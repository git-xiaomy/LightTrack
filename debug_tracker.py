#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化跟踪测试 - 调试跟踪算法
"""

import os
import sys
import cv2
import numpy as np
import time
from optimized_tracker import OptimizedTracker

def visual_test_tracker():
    """可视化测试跟踪器"""
    print("🎥 可视化跟踪测试")
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
    
    # 显示第一帧让用户选择目标
    print("📋 请在第一帧中选择跟踪目标...")
    
    # 简单的目标选择器
    bbox = None
    selecting = False
    start_point = None
    current_frame = frame.copy()
    
    def mouse_callback(event, x, y, flags, param):
        nonlocal bbox, selecting, start_point, current_frame
        
        if event == cv2.EVENT_LBUTTONDOWN:
            selecting = True
            start_point = (x, y)
            
        elif event == cv2.EVENT_MOUSEMOVE and selecting:
            temp_frame = frame.copy()
            cv2.rectangle(temp_frame, start_point, (x, y), (0, 255, 0), 2)
            cv2.imshow('Select Target', temp_frame)
            
        elif event == cv2.EVENT_LBUTTONUP and selecting:
            selecting = False
            x1, y1 = start_point
            x2, y2 = x, y
            
            x1, x2 = min(x1, x2), max(x1, x2)
            y1, y2 = min(y1, y2), max(y1, y2)
            
            if x2 - x1 > 10 and y2 - y1 > 10:
                bbox = [x1, y1, x2 - x1, y2 - y1]
                cv2.rectangle(current_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(current_frame, f'Target: {bbox}', (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow('Select Target', current_frame)
                print(f"✅ 选择的目标边界框: {bbox}")
    
    cv2.namedWindow('Select Target')
    cv2.setMouseCallback('Select Target', mouse_callback)
    cv2.imshow('Select Target', frame)
    
    print("🖱️  使用鼠标拖拽选择目标，按Enter确认，按ESC退出")
    
    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == 13 and bbox is not None:  # Enter
            break
        elif key == 27:  # ESC
            cv2.destroyAllWindows()
            cap.release()
            return
    
    cv2.destroyAllWindows()
    
    # 初始化跟踪器
    print(f"🎯 初始化跟踪器，目标: {bbox}")
    success = tracker.initialize(frame, bbox)
    
    if not success:
        print("❌ 跟踪器初始化失败")
        cap.release()
        return
    
    print("✅ 跟踪器初始化成功，开始跟踪...")
    
    # 创建输出视频
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter('debug_tracking.mp4', fourcc, fps, (width, height))
    
    frame_count = 0
    success_count = 0
    
    # 重置视频到开始
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 执行跟踪
        track_success, track_bbox, confidence = tracker.track(frame)
        
        # 绘制结果
        display_frame = frame.copy()
        
        if track_success:
            success_count += 1
            x, y, w, h = [int(v) for v in track_bbox]
            
            # 绘制成功的跟踪框（绿色）
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(display_frame, f'SUCCESS conf={confidence:.2f}', (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            x, y, w, h = [int(v) for v in track_bbox]
            
            # 绘制失败的跟踪框（红色）
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(display_frame, f'FAILED conf={confidence:.2f}', (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # 显示统计信息
        stats = tracker.get_stats()
        cv2.putText(display_frame, f'Frame: {frame_count+1}', (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(display_frame, f'FPS: {stats["fps"]:.1f}', (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(display_frame, f'Success Rate: {(success_count/(frame_count+1))*100:.1f}%', 
                   (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(display_frame, f'Model: {stats["model_type"]}', (10, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 写入输出视频
        out.write(display_frame)
        
        # 显示实时结果
        cv2.imshow('Tracking Debug', display_frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        
        frame_count += 1
        
        # 输出进度
        if frame_count % 30 == 0:
            print(f"📊 帧{frame_count}: FPS={stats['fps']:.1f}, "
                  f"成功率={(success_count/frame_count)*100:.1f}%")
    
    total_time = time.time() - start_time
    
    # 清理
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    
    # 最终统计
    final_stats = tracker.get_stats()
    print("\n🏁 跟踪完成")
    print("=" * 50)
    print(f"📊 最终统计:")
    print(f"   总帧数: {frame_count}")
    print(f"   成功帧数: {success_count}")
    print(f"   成功率: {(success_count/frame_count)*100:.1f}%")
    print(f"   平均FPS: {final_stats['fps']:.1f}")
    print(f"   总时间: {total_time:.2f}秒")
    print(f"   模型类型: {final_stats['model_type']}")
    print(f"   计算设备: {final_stats['device']}")
    print(f"📹 调试视频已保存: debug_tracking.mp4")


if __name__ == '__main__':
    visual_test_tracker()