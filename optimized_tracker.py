#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LightTrack 优化跟踪器
针对性能和准确性问题的优化实现
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
    from lib.utils.utils import load_pretrain, cxy_wh_2_rect, get_axis_aligned_bbox
    from lib.tracker.lighttrack import Lighttrack
    from easydict import EasyDict as edict
    LIGHTTRACK_AVAILABLE = True
except ImportError as e:
    print(f"LightTrack依赖导入失败: {e}")
    LIGHTTRACK_AVAILABLE = False


class OptimizedTracker:
    """优化的LightTrack跟踪器"""
    
    def __init__(self):
        self.model = None
        self.tracker = None
        self.device = 'cpu'
        self.initialized = False
        self.last_bbox = None
        self.confidence_threshold = 0.5
        self.template = None
        self.template_size = (127, 127)  # LightTrack标准模板大小
        
        # 性能统计
        self.frame_times = []
        self.tracking_success_rate = 0.0
        
        # 加载模型
        self._load_model()
    
    def _load_model(self) -> bool:
        """加载优化的LightTrack模型"""
        if not LIGHTTRACK_AVAILABLE:
            print("警告: LightTrack依赖不可用，使用快速演示模式")
            return False
        
        try:
            # 检查CUDA可用性
            if torch.cuda.is_available():
                self.device = 'cuda'
                print("✅ 使用GPU加速")
            else:
                self.device = 'cpu' 
                print("⚠️  使用CPU计算")
            
            # 模型配置 - 使用最快的配置
            info = edict()
            info.arch = 'LightTrackM_Speed'  # 使用速度优化版本
            info.dataset = 'VOT2019'
            info.stride = 16
            
            # 查找模型文件
            model_paths = [
                os.path.join(current_dir, 'snapshot', 'LightTrackM', 'LightTrackM.pth'),
                os.path.join(current_dir, 'snapshot', 'checkpoint_e30.pth'),
                os.path.join(current_dir, 'snapshot', 'LightTrackM.pth')
            ]
            
            model_path = None
            for path in model_paths:
                if os.path.exists(path):
                    model_path = path
                    print(f"✅ 找到模型文件: {path}")
                    break
            
            if not model_path:
                print("⚠️  未找到模型文件，使用演示模式")
                return False
            
            # 创建跟踪器
            self.tracker = Lighttrack(info)
            
            # 创建模型 - 使用Speed版本以获得最佳性能
            try:
                model = models.LightTrackM_Speed(
                    path_name='back_04502514044521042540+cls_211000022+reg_100000111_ops_32'
                )
            except TypeError:
                # 回退到其他版本
                model = models.LightTrackM_Subnet(
                    path_name='back_04502514044521042540+cls_211000022+reg_100000111_ops_32',
                    stride=info.stride
                )
            
            model = model.to(self.device)
            model.eval()
            
            # 加载预训练权重
            print(f"⚙️  加载模型权重: {os.path.basename(model_path)}")
            model = load_pretrain(model, model_path, print_unuse=False)
            
            self.model = model
            print("✅ LightTrack模型加载成功")
            
            # 预热模型以获得最佳性能
            self._warmup_model()
            
            return True
            
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            print("使用快速演示模式")
            self.model = None
            self.tracker = None
            return False
    
    def _warmup_model(self):
        """预热模型以获得最佳性能"""
        if self.model is None:
            return
        
        print("🔥 预热模型...")
        dummy_z = torch.randn(1, 3, 127, 127).to(self.device)
        dummy_x = torch.randn(1, 3, 255, 255).to(self.device)
        
        with torch.no_grad():
            for _ in range(5):  # 预热5次
                try:
                    if hasattr(self.model, 'forward'):
                        _ = self.model(dummy_x, dummy_z)
                except:
                    # 如果forward失败，尝试其他方法
                    try:
                        _ = self.model.forward_all(dummy_x, dummy_z)
                    except:
                        pass
        print("✅ 模型预热完成")
    
    def initialize(self, frame: np.ndarray, bbox: List[float]) -> bool:
        """初始化跟踪器"""
        start_time = time.time()
        
        try:
            self.last_bbox = bbox.copy()
            
            if self.model is not None and self.tracker is not None:
                # 使用真实LightTrack模型
                return self._initialize_real_tracker(frame, bbox)
            else:
                # 使用优化的演示模式
                return self._initialize_demo_tracker(frame, bbox)
        
        finally:
            init_time = time.time() - start_time
            print(f"⏱️  初始化时间: {init_time:.3f}秒")
    
    def _initialize_real_tracker(self, frame: np.ndarray, bbox: List[float]) -> bool:
        """初始化真实LightTrack跟踪器"""
        try:
            # 转换bbox格式
            x, y, w, h = bbox
            cx, cy = x + w/2, y + h/2
            
            # 创建状态字典
            state = {
                'im_h': frame.shape[0],
                'im_w': frame.shape[1]
            }
            
            # 初始化跟踪器
            self.tracker.init(frame, [cx, cy, w, h])
            self.initialized = True
            
            print("✅ 真实LightTrack跟踪器初始化成功")
            return True
            
        except Exception as e:
            print(f"❌ 真实跟踪器初始化失败: {e}")
            # 回退到演示模式
            return self._initialize_demo_tracker(frame, bbox)
    
    def _initialize_demo_tracker(self, frame: np.ndarray, bbox: List[float]) -> bool:
        """初始化优化的演示跟踪器"""
        try:
            x, y, w, h = [int(v) for v in bbox]
            
            # 边界检查
            if x < 0 or y < 0 or x + w > frame.shape[1] or y + h > frame.shape[0]:
                print(f"⚠️  边界框超出图像范围: {bbox}, 图像大小: {frame.shape}")
                return False
            
            # 提取模板
            template_region = frame[y:y+h, x:x+w]
            
            if template_region.size == 0:
                print(f"❌ 模板区域为空: {bbox}")
                return False
            
            # 调整模板大小为标准大小以提高匹配稳定性
            self.template = cv2.resize(template_region, self.template_size)
            
            # 保存原始模板用于调试
            self.original_template = template_region.copy()
            
            print(f"✅ 模板初始化成功: 大小={template_region.shape}, 标准化到={self.template.shape}")
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"❌ 演示跟踪器初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def track(self, frame: np.ndarray) -> Tuple[bool, List[float], float]:
        """执行跟踪
        
        Returns:
            (success, bbox, confidence)
        """
        start_time = time.time()
        
        try:
            if not self.initialized:
                return False, self.last_bbox, 0.0
            
            if self.model is not None and self.tracker is not None:
                # 使用真实LightTrack模型
                success, bbox, confidence = self._track_real(frame)
            else:
                # 使用优化的演示模式
                success, bbox, confidence = self._track_demo(frame)
            
            # 更新统计信息
            track_time = time.time() - start_time
            self.frame_times.append(track_time)
            
            # 保持最近100帧的时间记录
            if len(self.frame_times) > 100:
                self.frame_times = self.frame_times[-100:]
            
            return success, bbox, confidence
            
        except Exception as e:
            print(f"❌ 跟踪出错: {e}")
            return False, self.last_bbox, 0.0
    
    def _track_real(self, frame: np.ndarray) -> Tuple[bool, List[float], float]:
        """使用真实LightTrack模型跟踪"""
        try:
            # 使用LightTrack进行跟踪
            bbox = self.tracker.update(frame)
            
            if bbox is not None and len(bbox) >= 4:
                # 转换bbox格式 (cx, cy, w, h) -> (x, y, w, h)
                cx, cy, w, h = bbox[:4]
                x = cx - w/2
                y = cy - h/2
                
                new_bbox = [x, y, w, h]
                
                # 边界检查
                h_frame, w_frame = frame.shape[:2]
                if (x >= 0 and y >= 0 and 
                    x + w <= w_frame and y + h <= h_frame and
                    w > 10 and h > 10):
                    
                    self.last_bbox = new_bbox
                    confidence = 0.9  # 真实模型的高置信度
                    return True, new_bbox, confidence
            
            # 跟踪失败，返回上一次的位置
            return False, self.last_bbox, 0.1
            
        except Exception as e:
            print(f"❌ 真实跟踪失败: {e}")
            # 回退到演示模式
            return self._track_demo(frame)
    
    def _track_demo(self, frame: np.ndarray) -> Tuple[bool, List[float], float]:
        """使用优化的演示模式跟踪"""
        if self.template is None:
            return False, self.last_bbox, 0.0
        
        try:
            x, y, w, h = [int(v) for v in self.last_bbox]
            h_frame, w_frame = frame.shape[:2]
            
            # 扩大搜索区域以提高成功率
            search_margin = max(20, max(w, h) // 4)
            search_x1 = max(0, x - search_margin)
            search_y1 = max(0, y - search_margin)
            search_x2 = min(w_frame, x + w + search_margin)
            search_y2 = min(h_frame, y + h + search_margin)
            
            search_region = frame[search_y1:search_y2, search_x1:search_x2]
            
            # 检查搜索区域有效性
            if (search_region.shape[0] < self.template.shape[0] or 
                search_region.shape[1] < self.template.shape[1]):
                # 搜索区域太小，保持当前位置
                return False, self.last_bbox, 0.2
            
            # 使用主模板进行快速匹配
            try:
                # 使用归一化相关匹配
                result = cv2.matchTemplate(search_region, self.template, 
                                         cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                
                # 更宽松的阈值以提高跟踪成功率
                if max_val > 0.3:  # 进一步降低阈值
                    match_x, match_y = max_loc
                    
                    # 更新位置
                    new_x = search_x1 + match_x
                    new_y = search_y1 + match_y
                    new_w = w  # 保持原始大小
                    new_h = h
                    
                    # 边界检查
                    new_x = max(0, min(w_frame - new_w, new_x))
                    new_y = max(0, min(h_frame - new_h, new_y))
                    
                    new_bbox = [new_x, new_y, new_w, new_h]
                    
                    # 适应性模板更新 - 只在高置信度时更新
                    if max_val > 0.5:
                        try:
                            template_region = frame[new_y:new_y+new_h, new_x:new_x+new_w]
                            if template_region.size > 0 and template_region.shape[0] > 0 and template_region.shape[1] > 0:
                                # 使用加权平均更新模板，保持稳定性
                                new_template = cv2.resize(template_region, self.template_size)
                                alpha = 0.05  # 很小的学习率保持稳定性
                                self.template = cv2.addWeighted(self.template.astype(np.float32), 1-alpha, 
                                                              new_template.astype(np.float32), alpha, 0).astype(np.uint8)
                        except Exception as template_error:
                            # 模板更新失败不影响跟踪结果
                            pass
                    
                    self.last_bbox = new_bbox
                    return True, new_bbox, max_val
                else:
                    # 如果主模板匹配失败，尝试简单的位置预测
                    predicted_bbox = [x, y, w, h]  # 保持位置不变
                    return False, predicted_bbox, max_val
                    
            except Exception as match_error:
                print(f"⚠️  模板匹配出错: {match_error}")
                return False, self.last_bbox, 0.1
            
        except Exception as e:
            print(f"❌ 演示跟踪失败: {e}")
            return False, self.last_bbox, 0.0
    
    def get_fps(self) -> float:
        """获取当前FPS"""
        if len(self.frame_times) < 2:
            return 0.0
        
        avg_time = np.mean(self.frame_times)
        return 1.0 / avg_time if avg_time > 0 else 0.0
    
    def get_stats(self) -> dict:
        """获取跟踪统计信息"""
        fps = self.get_fps()
        
        return {
            'fps': fps,
            'avg_frame_time': np.mean(self.frame_times) if self.frame_times else 0.0,
            'model_type': 'LightTrack' if self.model else 'Optimized Demo',
            'device': self.device,
            'frame_count': len(self.frame_times)
        }


def test_optimized_tracker():
    """测试优化跟踪器"""
    print("🧪 测试优化跟踪器")
    print("=" * 50)
    
    # 创建跟踪器
    tracker = OptimizedTracker()
    
    # 打开测试视频
    video_path = 'sample_video.mp4'
    if not os.path.exists(video_path):
        print("❌ 请先运行 create_sample_video.py 创建测试视频")
        return
    
    cap = cv2.VideoCapture(video_path)
    
    # 读取第一帧
    ret, frame = cap.read()
    if not ret:
        print("❌ 无法读取视频")
        return
    
    # 初始化跟踪器
    bbox = [390, 210, 60, 60]  # 测试bbox
    success = tracker.initialize(frame, bbox)
    
    if not success:
        print("❌ 跟踪器初始化失败")
        return
    
    print("✅ 跟踪器初始化成功")
    print(f"📊 初始统计: {tracker.get_stats()}")
    
    # 跟踪测试帧
    frame_count = 0
    success_count = 0
    
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 执行跟踪
        track_success, track_bbox, confidence = tracker.track(frame)
        
        if track_success:
            success_count += 1
        
        frame_count += 1
        
        # 每30帧显示一次进度
        if frame_count % 30 == 0:
            stats = tracker.get_stats()
            print(f"📊 帧{frame_count}: FPS={stats['fps']:.1f}, "
                  f"成功率={(success_count/frame_count)*100:.1f}%")
        
        # 限制测试帧数
        if frame_count >= 150:  # 测试5秒
            break
    
    total_time = time.time() - start_time
    cap.release()
    
    # 最终统计
    final_stats = tracker.get_stats()
    print("\n🏁 测试完成")
    print("=" * 50)
    print(f"📊 最终统计:")
    print(f"   总帧数: {frame_count}")
    print(f"   成功帧数: {success_count}")
    print(f"   成功率: {(success_count/frame_count)*100:.1f}%")
    print(f"   平均FPS: {final_stats['fps']:.1f}")
    print(f"   总时间: {total_time:.2f}秒")
    print(f"   模型类型: {final_stats['model_type']}")
    print(f"   计算设备: {final_stats['device']}")


if __name__ == '__main__':
    test_optimized_tracker()