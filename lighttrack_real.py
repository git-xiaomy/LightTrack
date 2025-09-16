#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实的LightTrack模型集成示例
当有预训练模型时，可以使用此脚本进行真实的跟踪
"""

import os
import sys
import cv2
import torch
import argparse
import numpy as np
from pathlib import Path

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
    print(f"LightTrack模块导入失败: {e}")
    LIGHTTRACK_AVAILABLE = False

def parse_args():
    parser = argparse.ArgumentParser(description='LightTrack真实模型跟踪')
    parser.add_argument('--video', type=str, required=True, help='输入视频文件')
    parser.add_argument('--model', type=str, default='snapshot/LightTrack_M.pth', help='预训练模型路径')
    parser.add_argument('--arch', type=str, default='LightTrackM_Subnet', help='网络架构')
    parser.add_argument('--bbox', type=str, help='初始边界框 (x,y,w,h)')
    parser.add_argument('--output', type=str, help='输出视频路径')
    parser.add_argument('--display', action='store_true', help='实时显示')
    return parser.parse_args()

def select_bbox_interactive(video_path):
    """交互式选择边界框"""
    print("正在打开视频进行目标选择...")
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise ValueError("无法读取视频第一帧")
    
    print("请在窗口中拖拽鼠标选择跟踪目标，按ENTER确认，按ESC取消")
    
    bbox = None
    selecting = False
    start_point = None
    
    def mouse_callback(event, x, y, flags, param):
        nonlocal bbox, selecting, start_point, frame
        
        if event == cv2.EVENT_LBUTTONDOWN:
            selecting = True
            start_point = (x, y)
            
        elif event == cv2.EVENT_MOUSEMOVE and selecting:
            temp_frame = frame.copy()
            cv2.rectangle(temp_frame, start_point, (x, y), (0, 255, 0), 2)
            cv2.imshow('LightTrack - 选择目标', temp_frame)
            
        elif event == cv2.EVENT_LBUTTONUP and selecting:
            selecting = False
            x1, y1 = start_point
            x2, y2 = x, y
            
            x1, x2 = min(x1, x2), max(x1, x2)
            y1, y2 = min(y1, y2), max(y1, y2)
            
            if x2 - x1 > 10 and y2 - y1 > 10:
                bbox = [x1, y1, x2 - x1, y2 - y1]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.imshow('LightTrack - 选择目标', frame)
    
    cv2.namedWindow('LightTrack - 选择目标')
    cv2.setMouseCallback('LightTrack - 选择目标', mouse_callback)
    cv2.imshow('LightTrack - 选择目标', frame)
    
    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == 13:  # Enter
            break
        elif key == 27:  # ESC
            bbox = None
            break
    
    cv2.destroyAllWindows()
    return bbox

def track_with_lighttrack(video_path, model_path, arch, init_bbox, output_path=None, display=False):
    """使用真实的LightTrack模型进行跟踪"""
    
    if not LIGHTTRACK_AVAILABLE:
        raise ImportError("LightTrack模块不可用")
    
    # 检查模型文件
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"模型文件不存在: {model_path}")
    
    print(f"正在加载LightTrack模型: {model_path}")
    
    # 配置参数
    info = edict()
    info.arch = arch
    info.dataset = 'VOT2019'  # 或其他数据集
    info.stride = 16
    
    # 初始化跟踪器
    tracker = Lighttrack(info)
    
    # 加载模型
    if torch.cuda.is_available():
        device = torch.device('cuda')
        print("使用GPU加速")
    else:
        device = torch.device('cpu')
        print("使用CPU")
    
    # 创建网络模型
    model = models.__dict__[arch](stride=info.stride)
    model = load_pretrain(model, model_path)
    model.eval()
    model = model.to(device)
    
    print("模型加载完成")
    
    # 打开视频
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"视频信息: {width}x{height}, {fps:.1f}fps, {total_frames}帧")
    
    # 准备输出
    if output_path is None:
        video_name = Path(video_path).stem
        output_path = f"{video_name}_lighttrack.mp4"
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # 初始化跟踪
    ret, first_frame = cap.read()
    if not ret:
        raise ValueError("无法读取视频第一帧")
    
    # 转换为RGB
    rgb_frame = cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB)
    
    # 初始化目标
    cx = init_bbox[0] + init_bbox[2] / 2
    cy = init_bbox[1] + init_bbox[3] / 2
    target_pos = np.array([cx, cy])
    target_sz = np.array([init_bbox[2], init_bbox[3]])
    
    # 初始化跟踪器
    state = tracker.init(rgb_frame, target_pos, target_sz, model)
    
    # 绘制初始框
    x, y, w, h = [int(v) for v in init_bbox]
    cv2.rectangle(first_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.putText(first_frame, 'Frame: 1', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(first_frame, 'LightTrack', (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    
    out.write(first_frame)
    
    if display:
        cv2.imshow('LightTrack跟踪', first_frame)
        cv2.waitKey(1)
    
    frame_count = 1
    
    # 跟踪循环
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 转换为RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 更新跟踪器
        state = tracker.track(state, rgb_frame)
        
        # 获取跟踪结果
        target_pos = state['target_pos']
        target_sz = state['target_sz']
        
        # 转换为边界框
        bbox = cxy_wh_2_rect(target_pos, target_sz)
        x, y, w, h = [int(v) for v in bbox]
        
        # 绘制跟踪框
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # 添加信息
        cv2.putText(frame, f'Frame: {frame_count + 1}/{total_frames}', 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, 'LightTrack', 
                   (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # 写入输出视频
        out.write(frame)
        
        # 显示结果
        if display:
            cv2.imshow('LightTrack跟踪', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        frame_count += 1
        
        # 显示进度
        if frame_count % 30 == 0:
            progress = (frame_count / total_frames) * 100
            print(f"跟踪进度: {progress:.1f}% ({frame_count}/{total_frames})")
    
    # 清理资源
    cap.release()
    out.release()
    if display:
        cv2.destroyAllWindows()
    
    print(f"LightTrack跟踪完成! 结果保存至: {output_path}")
    return output_path

def main():
    """主函数"""
    args = parse_args()
    
    # 检查视频文件
    if not os.path.exists(args.video):
        print(f"错误: 视频文件不存在: {args.video}")
        return
    
    # 检查LightTrack可用性
    if not LIGHTTRACK_AVAILABLE:
        print("错误: LightTrack模块不可用")
        print("请检查是否正确安装了所有依赖")
        return
    
    # 检查模型文件
    if not os.path.exists(args.model):
        print(f"错误: 模型文件不存在: {args.model}")
        print("请从以下链接下载预训练模型:")
        print("https://drive.google.com/drive/folders/1HXhdJO3yhQYw3O7nGUOXHu2S20Bs8CfI")
        return
    
    # 获取初始边界框
    if args.bbox:
        try:
            init_bbox = [float(x) for x in args.bbox.split(',')]
            if len(init_bbox) != 4:
                raise ValueError
        except ValueError:
            print("错误: 边界框格式错误，应为: x,y,w,h")
            return
    else:
        print("未指定边界框，将进入交互式选择模式")
        try:
            init_bbox = select_bbox_interactive(args.video)
            if init_bbox is None:
                print("未选择目标，退出程序")
                return
        except Exception as e:
            print(f"目标选择失败: {e}")
            return
    
    # 开始跟踪
    try:
        result_path = track_with_lighttrack(
            args.video,
            args.model,
            args.arch,
            init_bbox,
            args.output,
            args.display
        )
        
        print("=" * 60)
        print("LightTrack跟踪完成!")
        print(f"输入视频: {args.video}")
        print(f"输出视频: {result_path}")
        print(f"模型架构: {args.arch}")
        print(f"初始边界框: {init_bbox}")
        print("=" * 60)
        
    except Exception as e:
        print(f"跟踪过程出错: {e}")

if __name__ == "__main__":
    main()