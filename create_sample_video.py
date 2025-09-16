#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建一个简单的测试视频用于演示LightTrack跟踪功能
"""

import cv2
import numpy as np
import os

def create_sample_video(output_path="sample_video.mp4", duration=10, fps=30):
    """
    创建一个包含移动目标的示例视频
    
    Args:
        output_path: 输出视频路径
        duration: 视频时长（秒）
        fps: 帧率
    """
    
    # 视频参数
    width, height = 640, 480
    total_frames = duration * fps
    
    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # 目标参数
    target_size = 30
    target_color = (0, 255, 0)  # 绿色
    
    print(f"正在创建测试视频: {output_path}")
    print(f"分辨率: {width}x{height}, 时长: {duration}秒, 帧率: {fps}")
    
    for frame_idx in range(total_frames):
        # 创建黑色背景
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 添加一些背景噪声
        noise = np.random.randint(0, 50, (height, width, 3), dtype=np.uint8)
        frame = cv2.add(frame, noise)
        
        # 计算目标位置（圆形运动）
        t = frame_idx / total_frames * 4 * np.pi  # 2个完整圆周
        center_x = width // 2 + int(100 * np.cos(t))
        center_y = height // 2 + int(80 * np.sin(t))
        
        # 确保目标在画面内
        center_x = max(target_size, min(width - target_size, center_x))
        center_y = max(target_size, min(height - target_size, center_y))
        
        # 绘制移动目标（实心圆）
        cv2.circle(frame, (center_x, center_y), target_size, target_color, -1)
        
        # 添加一些干扰目标
        for i in range(3):
            distractor_x = int(np.random.uniform(50, width - 50))
            distractor_y = int(np.random.uniform(50, height - 50))
            distractor_color = (np.random.randint(50, 255), 
                              np.random.randint(50, 255), 
                              np.random.randint(50, 255))
            cv2.circle(frame, (distractor_x, distractor_y), 
                      np.random.randint(5, 15), distractor_color, -1)
        
        # 添加帧号信息
        cv2.putText(frame, f'Frame: {frame_idx + 1}', (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 添加目标位置信息
        cv2.putText(frame, f'Target: ({center_x}, {center_y})', (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 写入帧
        out.write(frame)
        
        # 显示进度
        if frame_idx % 30 == 0:
            progress = (frame_idx / total_frames) * 100
            print(f"进度: {progress:.1f}%")
    
    out.release()
    print(f"测试视频创建完成: {output_path}")
    
    # 返回第一帧的目标边界框
    first_target_x = width // 2 + int(100 * np.cos(0))
    first_target_y = height // 2 + int(80 * np.sin(0))
    bbox = [first_target_x - target_size, first_target_y - target_size, 
            target_size * 2, target_size * 2]
    
    print(f"建议的初始边界框: {bbox}")
    return bbox

def main():
    """主函数"""
    print("LightTrack 测试视频生成器")
    print("=" * 40)
    
    # 创建测试视频
    bbox = create_sample_video("sample_video.mp4", duration=10, fps=30)
    
    print("\n使用说明:")
    print("1. 使用GUI程序:")
    print("   python gui_tracker.py")
    print("   然后选择生成的 sample_video.mp4")
    print()
    print("2. 使用命令行程序:")
    print(f"   python mp4_tracking_demo.py --video sample_video.mp4 --bbox {bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]} --display")
    print()
    print("3. 交互式选择目标:")
    print("   python mp4_tracking_demo.py --video sample_video.mp4 --display")

if __name__ == "__main__":
    main()