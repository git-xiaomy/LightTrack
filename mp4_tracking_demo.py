#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LightTrack MP4视频跟踪示例脚本
使用方法: python mp4_tracking_demo.py --video your_video.mp4 --bbox x,y,w,h
"""

import os
import sys
import cv2
import argparse
import numpy as np
from pathlib import Path

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def parse_args():
    parser = argparse.ArgumentParser(description='LightTrack MP4视频跟踪演示')
    parser.add_argument('--video', type=str, required=True, help='输入MP4视频文件路径')
    parser.add_argument('--bbox', type=str, help='初始边界框 (x,y,w,h)')
    parser.add_argument('--output', type=str, help='输出视频文件路径')
    parser.add_argument('--display', action='store_true', help='实时显示跟踪结果')
    return parser.parse_args()

def parse_bbox(bbox_str):
    """解析边界框字符串"""
    try:
        bbox = [float(x) for x in bbox_str.split(',')]
        if len(bbox) != 4:
            raise ValueError
        return bbox
    except:
        raise ValueError("边界框格式错误，应为: x,y,w,h")

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
            cv2.imshow('选择目标', temp_frame)
            
        elif event == cv2.EVENT_LBUTTONUP and selecting:
            selecting = False
            x1, y1 = start_point
            x2, y2 = x, y
            
            x1, x2 = min(x1, x2), max(x1, x2)
            y1, y2 = min(y1, y2), max(y1, y2)
            
            if x2 - x1 > 10 and y2 - y1 > 10:
                bbox = [x1, y1, x2 - x1, y2 - y1]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.imshow('选择目标', frame)
    
    cv2.namedWindow('选择目标')
    cv2.setMouseCallback('选择目标', mouse_callback)
    cv2.imshow('选择目标', frame)
    
    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == 13:  # Enter
            break
        elif key == 27:  # ESC
            bbox = None
            break
    
    cv2.destroyAllWindows()
    return bbox

def track_video_simple(video_path, init_bbox, output_path=None, display=False):
    """
    简单的视频跟踪实现（模拟LightTrack的效果）
    由于缺少实际的预训练模型，这里使用OpenCV的跟踪器作为演示
    """
    print(f"开始跟踪视频: {video_path}")
    print(f"初始边界框: {init_bbox}")
    
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
        output_path = f"{video_name}_tracked.mp4"
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # 初始化简单跟踪器（作为LightTrack的替代演示）
    # 由于OpenCV版本兼容性问题，使用简单的跟踪算法
    print("使用简化的跟踪算法作为LightTrack演示")
    
    # 读取第一帧
    ret, frame = cap.read()
    if not ret:
        print("错误: 无法读取视频")
        return
    
    # 使用简单的模板匹配作为跟踪演示
    x, y, w, h = [int(v) for v in init_bbox]
    template = frame[y:y+h, x:x+w]
    
    frame_count = 0
    current_bbox = init_bbox.copy()
    
    # 重新定位到视频开始
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 简单的模板匹配跟踪
        x, y, w, h = [int(v) for v in current_bbox]
        
        # 定义搜索区域（比当前边界框稍大）
        search_margin = 50
        search_x1 = max(0, x - search_margin)
        search_y1 = max(0, y - search_margin)
        search_x2 = min(width, x + w + search_margin)
        search_y2 = min(height, y + h + search_margin)
        
        search_region = frame[search_y1:search_y2, search_x1:search_x2]
        
        if search_region.shape[0] > template.shape[0] and search_region.shape[1] > template.shape[1]:
            # 模板匹配
            result = cv2.matchTemplate(search_region, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # 更新边界框位置
            if max_val > 0.6:  # 匹配阈值
                match_x, match_y = max_loc
                current_bbox[0] = search_x1 + match_x
                current_bbox[1] = search_y1 + match_y
                ok = True
            else:
                ok = False
        else:
            ok = False
        
        if ok:
            # 跟踪成功，绘制边界框
            (x, y, w, h) = [int(v) for v in current_bbox]
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # 添加跟踪信息
            cv2.putText(frame, f'Frame: {frame_count + 1}/{total_frames}', 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, 'LightTrack Demo (Template Matching)', 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.putText(frame, 'LightTrack', 
                       (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        else:
            # 跟踪失败
            cv2.putText(frame, 'Tracking Failed', (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # 写入输出视频
        out.write(frame)
        
        # 显示结果（可选）
        if display:
            cv2.imshow('LightTrack Demo', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        frame_count += 1
        
        # 显示进度
        if frame_count % 30 == 0:
            progress = (frame_count / total_frames) * 100
            print(f"处理进度: {progress:.1f}% ({frame_count}/{total_frames})")
    
    # 清理资源
    cap.release()
    out.release()
    if display:
        cv2.destroyAllWindows()
    
    print(f"跟踪完成! 结果已保存至: {output_path}")
    return output_path

def main():
    """主函数"""
    args = parse_args()
    
    # 检查视频文件
    if not os.path.exists(args.video):
        print(f"错误: 视频文件不存在: {args.video}")
        return
    
    # 获取初始边界框
    if args.bbox:
        try:
            init_bbox = parse_bbox(args.bbox)
        except ValueError as e:
            print(f"错误: {e}")
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
        result_path = track_video_simple(
            args.video, 
            init_bbox, 
            args.output, 
            args.display
        )
        
        print("=" * 50)
        print("跟踪完成!")
        print(f"输入视频: {args.video}")
        print(f"输出视频: {result_path}")
        print(f"初始边界框: {init_bbox}")
        print("=" * 50)
        
    except Exception as e:
        print(f"跟踪过程出错: {e}")

if __name__ == "__main__":
    main()