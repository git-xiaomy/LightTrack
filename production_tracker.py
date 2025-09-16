#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平衡速度与准确性的最终跟踪器
Final Production Tracker - Balanced Speed and Accuracy
"""

import os
import sys
import cv2
import torch
import numpy as np
import time
from typing import Optional, Tuple, List

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from tracking._init_paths import *
    import lib.models.models as models
    from lib.utils.utils import load_pretrain
    from lib.tracker.lighttrack import Lighttrack
    from easydict import EasyDict as edict
    LIGHTTRACK_AVAILABLE = True
except ImportError as e:
    print(f"LightTrack依赖导入失败: {e}")
    LIGHTTRACK_AVAILABLE = False


class ProductionTracker:
    """生产级跟踪器 - 平衡速度与准确性"""
    
    def __init__(self, target_fps: float = 60.0):
        self.model = None
        self.tracker = None
        self.device = 'cpu'
        self.initialized = False
        self.last_bbox = None
        self.template = None
        self.target_fps = target_fps  # 目标FPS，平衡速度与准确性
        
        # 跟踪历史用于稳定性
        self.bbox_history = []
        self.confidence_history = []
        self.max_history = 5
        
        # 性能统计
        self.frame_times = []
        self.success_count = 0
        self.total_frames = 0
        
        # 加载模型
        self._load_model()
    
    def _load_model(self) -> bool:
        """加载LightTrack模型"""
        if not LIGHTTRACK_AVAILABLE:
            print("⚠️  使用高速演示模式")
            return False
        
        try:
            # 检查CUDA
            if torch.cuda.is_available():
                self.device = 'cuda'
                print("✅ 使用GPU加速")
            else:
                self.device = 'cpu'
                print("💻 使用CPU计算")
            
            # 模型配置
            info = edict()
            info.arch = 'LightTrackM_Speed'
            info.dataset = 'VOT2019'
            info.stride = 16
            
            # 查找模型文件
            model_paths = [
                os.path.join(current_dir, 'snapshot', 'LightTrackM', 'LightTrackM.pth'),
                os.path.join(current_dir, 'snapshot', 'checkpoint_e30.pth')
            ]
            
            model_path = None
            for path in model_paths:
                if os.path.exists(path):
                    model_path = path
                    break
            
            if not model_path:
                print("⚠️  未找到模型文件，使用演示模式")
                return False
            
            # 创建跟踪器
            self.tracker = Lighttrack(info)
            
            # 创建模型
            try:
                model = models.LightTrackM_Speed(
                    path_name='back_04502514044521042540+cls_211000022+reg_100000111_ops_32'
                )
            except TypeError:
                model = models.LightTrackM_Subnet(
                    path_name='back_04502514044521042540+cls_211000022+reg_100000111_ops_32',
                    stride=info.stride
                )
            
            model = model.to(self.device)
            model.eval()
            
            # 加载预训练权重
            print(f"📥 加载模型: {os.path.basename(model_path)}")
            model = load_pretrain(model, model_path, print_unuse=False)
            
            self.model = model
            print("✅ 真实LightTrack模型加载成功")
            return True
            
        except Exception as e:
            print(f"⚠️  模型加载失败，使用演示模式: {e}")
            self.model = None
            self.tracker = None
            return False
    
    def initialize(self, frame: np.ndarray, bbox: List[float]) -> bool:
        """初始化跟踪器"""
        self.last_bbox = bbox.copy()
        
        # 清空历史
        self.bbox_history = [bbox.copy()]
        self.confidence_history = [1.0]
        
        if self.model is not None and self.tracker is not None:
            return self._initialize_real_tracker(frame, bbox)
        else:
            return self._initialize_demo_tracker(frame, bbox)
    
    def _initialize_real_tracker(self, frame: np.ndarray, bbox: List[float]) -> bool:
        """初始化真实LightTrack跟踪器"""
        try:
            x, y, w, h = bbox
            cx, cy = x + w/2, y + h/2
            
            # 初始化跟踪器
            self.tracker.init(frame, [cx, cy, w, h])
            self.initialized = True
            
            print("✅ 真实LightTrack跟踪器初始化成功")
            return True
            
        except Exception as e:
            print(f"❌ 真实跟踪器初始化失败: {e}")
            return self._initialize_demo_tracker(frame, bbox)
    
    def _initialize_demo_tracker(self, frame: np.ndarray, bbox: List[float]) -> bool:
        """初始化演示跟踪器"""
        try:
            x, y, w, h = [int(v) for v in bbox]
            
            # 边界检查
            if (x < 0 or y < 0 or x + w > frame.shape[1] or 
                y + h > frame.shape[0] or w <= 0 or h <= 0):
                print(f"❌ 无效边界框: {bbox}")
                return False
            
            # 提取模板
            template_region = frame[y:y+h, x:x+w]
            if template_region.size == 0:
                return False
            
            # 使用合适的模板大小
            template_size = min(127, max(w, h))
            self.template = cv2.resize(template_region, (template_size, template_size))
            
            self.initialized = True
            print("✅ 演示跟踪器初始化成功")
            return True
            
        except Exception as e:
            print(f"❌ 演示跟踪器初始化失败: {e}")
            return False
    
    def track(self, frame: np.ndarray) -> Tuple[bool, List[float], float]:
        """执行跟踪"""
        start_time = time.time()
        
        if not self.initialized:
            return False, self.last_bbox, 0.0
        
        try:
            if self.model is not None and self.tracker is not None:
                # 使用真实LightTrack模型
                success, bbox, confidence = self._track_real(frame)
            else:
                # 使用高质量演示模式
                success, bbox, confidence = self._track_demo_balanced(frame)
            
            # 更新统计
            self.total_frames += 1
            if success:
                self.success_count += 1
            
            # 更新历史
            self._update_history(bbox, confidence)
            
            # 根据目标FPS调整处理速度
            elapsed = time.time() - start_time
            target_time = 1.0 / self.target_fps
            if elapsed < target_time:
                time.sleep(target_time - elapsed)
            
            self.frame_times.append(time.time() - start_time)
            if len(self.frame_times) > 100:
                self.frame_times = self.frame_times[-100:]
            
            return success, bbox, confidence
            
        except Exception as e:
            print(f"❌ 跟踪失败: {e}")
            return False, self.last_bbox, 0.0
    
    def _track_real(self, frame: np.ndarray) -> Tuple[bool, List[float], float]:
        """使用真实LightTrack模型跟踪"""
        try:
            bbox = self.tracker.update(frame)
            
            if bbox is not None and len(bbox) >= 4:
                cx, cy, w, h = bbox[:4]
                x = cx - w/2
                y = cy - h/2
                
                new_bbox = [x, y, w, h]
                
                # 边界检查
                h_frame, w_frame = frame.shape[:2]
                if (x >= 0 and y >= 0 and x + w <= w_frame and 
                    y + h <= h_frame and w > 10 and h > 10):
                    
                    self.last_bbox = new_bbox
                    return True, new_bbox, 0.9
            
            return False, self.last_bbox, 0.1
            
        except Exception as e:
            print(f"❌ 真实跟踪失败: {e}")
            return self._track_demo_balanced(frame)
    
    def _track_demo_balanced(self, frame: np.ndarray) -> Tuple[bool, List[float], float]:
        """平衡的演示模式跟踪"""
        if self.template is None:
            return False, self.last_bbox, 0.0
        
        try:
            x, y, w, h = [int(v) for v in self.last_bbox]
            h_frame, w_frame = frame.shape[:2]
            
            # 智能搜索区域大小
            movement_scale = max(0.5, min(2.0, self.target_fps / 30.0))
            search_margin = int(max(20, (w + h) * 0.25 * movement_scale))
            
            search_x1 = max(0, x - search_margin)
            search_y1 = max(0, y - search_margin)
            search_x2 = min(w_frame, x + w + search_margin)
            search_y2 = min(h_frame, y + h + search_margin)
            
            search_region = frame[search_y1:search_y2, search_x1:search_x2]
            
            # 检查搜索区域
            if (search_region.shape[0] < self.template.shape[0] or 
                search_region.shape[1] < self.template.shape[1]):
                return False, self.last_bbox, 0.1
            
            # 多尺度模板匹配以提高准确性
            best_val = 0
            best_loc = None
            best_scale = 1.0
            
            scales = [0.9, 1.0, 1.1] if self.target_fps > 30 else [1.0]
            
            for scale in scales:
                try:
                    if scale != 1.0:
                        scaled_template = cv2.resize(
                            self.template, 
                            (int(self.template.shape[1] * scale),
                             int(self.template.shape[0] * scale))
                        )
                    else:
                        scaled_template = self.template
                    
                    if (scaled_template.shape[0] <= search_region.shape[0] and 
                        scaled_template.shape[1] <= search_region.shape[1]):
                        
                        result = cv2.matchTemplate(search_region, scaled_template, 
                                                 cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, max_loc = cv2.minMaxLoc(result)
                        
                        if max_val > best_val:
                            best_val = max_val
                            best_loc = max_loc
                            best_scale = scale
                    
                except:
                    continue
            
            # 智能阈值调整
            confidence_threshold = max(0.4, 0.7 - (self.target_fps - 30) * 0.01)
            
            if best_val > confidence_threshold and best_loc is not None:
                match_x, match_y = best_loc
                
                new_x = search_x1 + match_x
                new_y = search_y1 + match_y
                new_w = int(w * best_scale)
                new_h = int(h * best_scale)
                
                # 边界检查
                new_x = max(0, min(w_frame - new_w, new_x))
                new_y = max(0, min(h_frame - new_h, new_y))
                
                new_bbox = [new_x, new_y, new_w, new_h]
                
                # 模板更新策略
                if best_val > 0.7 and len(self.confidence_history) > 0:
                    avg_confidence = np.mean(self.confidence_history[-3:])
                    if avg_confidence > 0.6:  # 只有持续高置信度才更新模板
                        self._update_template(frame, new_bbox, best_val)
                
                self.last_bbox = new_bbox
                return True, new_bbox, best_val
            else:
                # 使用历史信息预测位置
                predicted_bbox = self._predict_bbox()
                return False, predicted_bbox, best_val
                
        except Exception as e:
            print(f"❌ 演示跟踪失败: {e}")
            return False, self.last_bbox, 0.0
    
    def _update_template(self, frame: np.ndarray, bbox: List[float], confidence: float):
        """智能模板更新"""
        try:
            x, y, w, h = [int(v) for v in bbox]
            
            if (x >= 0 and y >= 0 and x + w <= frame.shape[1] and 
                y + h <= frame.shape[0] and w > 0 and h > 0):
                
                new_template_region = frame[y:y+h, x:x+w]
                if new_template_region.size > 0:
                    # 调整到相同大小
                    new_template = cv2.resize(new_template_region, 
                                            (self.template.shape[1], self.template.shape[0]))
                    
                    # 自适应学习率
                    learning_rate = min(0.1, confidence * 0.15)
                    
                    # 加权更新
                    self.template = cv2.addWeighted(
                        self.template.astype(np.float32), 1 - learning_rate,
                        new_template.astype(np.float32), learning_rate, 0
                    ).astype(np.uint8)
        except:
            pass  # 模板更新失败不影响跟踪
    
    def _update_history(self, bbox: List[float], confidence: float):
        """更新跟踪历史"""
        self.bbox_history.append(bbox.copy())
        self.confidence_history.append(confidence)
        
        if len(self.bbox_history) > self.max_history:
            self.bbox_history = self.bbox_history[-self.max_history:]
            self.confidence_history = self.confidence_history[-self.max_history:]
    
    def _predict_bbox(self) -> List[float]:
        """基于历史预测边界框"""
        if len(self.bbox_history) < 2:
            return self.last_bbox.copy()
        
        # 简单的运动预测
        try:
            last_bbox = self.bbox_history[-1]
            prev_bbox = self.bbox_history[-2]
            
            dx = last_bbox[0] - prev_bbox[0]
            dy = last_bbox[1] - prev_bbox[1]
            
            # 限制运动幅度
            dx = max(-20, min(20, dx))
            dy = max(-20, min(20, dy))
            
            predicted_x = last_bbox[0] + dx
            predicted_y = last_bbox[1] + dy
            
            return [predicted_x, predicted_y, last_bbox[2], last_bbox[3]]
        except:
            return self.last_bbox.copy()
    
    def get_stats(self) -> dict:
        """获取跟踪统计信息"""
        fps = 1.0 / np.mean(self.frame_times) if self.frame_times else 0.0
        success_rate = (self.success_count / self.total_frames * 100) if self.total_frames > 0 else 0.0
        
        return {
            'fps': fps,
            'success_rate': success_rate,
            'total_frames': self.total_frames,
            'successful_frames': self.success_count,
            'model_type': 'LightTrack' if self.model else 'Balanced Demo',
            'device': self.device,
            'target_fps': self.target_fps
        }


def test_production_tracker():
    """测试生产级跟踪器"""
    print("🏭 生产级跟踪器测试")
    print("=" * 50)
    
    # 测试不同FPS目标
    fps_targets = [30, 60, 90]
    
    for target_fps in fps_targets:
        print(f"\n🎯 测试目标FPS: {target_fps}")
        print("-" * 30)
        
        tracker = ProductionTracker(target_fps=target_fps)
        
        # 测试视频
        cap = cv2.VideoCapture('sample_video.mp4')
        ret, frame = cap.read()
        if not ret:
            print("❌ 无法读取视频")
            continue
        
        # 初始化
        bbox = [390, 210, 60, 60]
        success = tracker.initialize(frame, bbox)
        
        if not success:
            print("❌ 初始化失败")
            continue
        
        # 测试30帧
        test_frames = 30
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        start_time = time.time()
        
        for i in range(test_frames):
            ret, frame = cap.read()
            if not ret:
                break
            
            success, bbox, confidence = tracker.track(frame)
        
        total_time = time.time() - start_time
        cap.release()
        
        # 显示结果
        stats = tracker.get_stats()
        print(f"   实际FPS: {stats['fps']:.1f}")
        print(f"   成功率: {stats['success_rate']:.1f}%")
        print(f"   总时间: {total_time:.3f}秒")
        print(f"   跟踪器类型: {stats['model_type']}")


if __name__ == '__main__':
    test_production_tracker()