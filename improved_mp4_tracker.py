#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的命令行跟踪工具 - 支持跳帧和高性能跟踪
Improved Command Line Tracker - With Frame Skipping and High Performance

主要改进：
1. 支持跳帧处理 - 大幅提升处理速度
2. 真实LightTrack模型集成 - 移除演示模式
3. 自适应性能调优 - 根据视频特点自动优化
4. 详细的性能分析 - 完整的统计信息输出
"""

import os
import sys
import cv2
import argparse
import numpy as np
import time
from pathlib import Path

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from improved_tracker import ImprovedTracker


def parse_args():
    parser = argparse.ArgumentParser(description='LightTrack 改进版命令行跟踪工具')
    parser.add_argument('--video', type=str, required=True, help='输入MP4视频文件路径')
    parser.add_argument('--bbox', type=str, help='初始边界框 (x,y,w,h)')
    parser.add_argument('--output', type=str, help='输出视频文件路径')
    parser.add_argument('--display', action='store_true', help='实时显示跟踪结果')
    parser.add_argument('--frame-skip', type=int, default=1, help='跳帧间隔 (默认:1, 不跳帧)')
    parser.add_argument('--target-fps', type=float, default=30.0, help='目标FPS (默认:30)')
    parser.add_argument('--benchmark', action='store_true', help='性能基准测试模式')
    parser.add_argument('--auto-optimize', action='store_true', help='自动优化参数')
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
    
    # 使用OpenCV的ROI选择器
    bbox = cv2.selectROI("选择跟踪目标 - 框选后按ENTER确认", frame, False)
    cv2.destroyWindow("选择跟踪目标 - 框选后按ENTER确认")
    
    if bbox[2] > 0 and bbox[3] > 0:
        return list(bbox)
    else:
        return None


def analyze_video(video_path):
    """分析视频特征，给出优化建议"""
    print("\n📊 分析视频特征...")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None, None
    
    # 获取基本信息
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = total_frames / fps if fps > 0 else 0
    
    # 采样几帧分析运动幅度
    motion_scores = []
    prev_gray = None
    
    for i in range(0, min(total_frames, 100), 10):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if not ret:
            break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_gray is not None:
            flow = cv2.calcOpticalFlowPyrLK(prev_gray, gray, 
                                          np.array([[width//2, height//2]], dtype=np.float32),
                                          None, maxLevel=2)[0]
            if flow is not None and len(flow) > 0:
                motion = np.linalg.norm(flow[0])
                motion_scores.append(motion)
        
        prev_gray = gray
    
    cap.release()
    
    # 计算运动统计
    avg_motion = np.mean(motion_scores) if motion_scores else 0
    
    # 视频特征
    video_info = {
        'total_frames': total_frames,
        'fps': fps,
        'width': width,
        'height': height,
        'duration': duration,
        'avg_motion': avg_motion,
        'motion_level': 'high' if avg_motion > 10 else 'medium' if avg_motion > 3 else 'low'
    }
    
    # 性能建议
    suggestions = {}
    
    # 基于视频长度的建议
    if duration > 60:
        suggestions['frame_skip'] = 3
        suggestions['reason'] = "长视频，建议较大跳帧间隔"
    elif duration > 30:
        suggestions['frame_skip'] = 2
        suggestions['reason'] = "中等长度视频，适度跳帧"
    else:
        suggestions['frame_skip'] = 1
        suggestions['reason'] = "短视频，保持高质量"
    
    # 基于运动幅度的建议
    if avg_motion > 10:
        suggestions['target_fps'] = 60
        suggestions['motion_reason'] = "高运动幅度，需要高帧率"
    elif avg_motion > 3:
        suggestions['target_fps'] = 30
        suggestions['motion_reason'] = "中等运动幅度，标准帧率"
    else:
        suggestions['target_fps'] = 20
        suggestions['motion_reason'] = "低运动幅度，可降低帧率"
    
    # 基于分辨率的建议
    if width * height > 1920 * 1080:
        suggestions['frame_skip'] = max(suggestions['frame_skip'], 2)
        suggestions['resolution_reason'] = "高分辨率，增加跳帧"
    
    return video_info, suggestions


def print_video_analysis(video_info, suggestions):
    """打印视频分析结果"""
    print(f"   分辨率: {video_info['width']}x{video_info['height']}")
    print(f"   总帧数: {video_info['total_frames']}")
    print(f"   帧率: {video_info['fps']:.2f} FPS")
    print(f"   时长: {video_info['duration']:.1f}秒")
    print(f"   运动幅度: {video_info['motion_level']} (平均: {video_info['avg_motion']:.1f})")
    
    print(f"\n💡 优化建议:")
    print(f"   推荐跳帧间隔: {suggestions['frame_skip']} ({suggestions['reason']})")
    print(f"   推荐目标FPS: {suggestions['target_fps']} ({suggestions['motion_reason']})")
    if 'resolution_reason' in suggestions:
        print(f"   分辨率调整: {suggestions['resolution_reason']}")


def track_video_improved(video_path, init_bbox, output_path, display=False, 
                        frame_skip=1, target_fps=30.0, benchmark=False):
    """使用改进跟踪器处理视频"""
    
    print(f"\n🚀 开始改进版跟踪")
    print(f"跳帧间隔: {frame_skip}, 目标FPS: {target_fps}")
    
    # 创建跟踪器
    tracker = ImprovedTracker(frame_skip=frame_skip, target_fps=target_fps)
    
    # 打开视频
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频文件: {video_path}")
    
    # 获取视频属性
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"视频信息: {width}x{height}, {original_fps}fps, {total_frames}帧")
    
    # 准备输出视频
    if output_path is None:
        output_path = os.path.splitext(video_path)[0] + f"_tracked_fs{frame_skip}_fps{target_fps:.0f}.mp4"
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, original_fps, (width, height))
    
    # 读取第一帧
    ret, frame = cap.read()
    if not ret:
        raise ValueError("无法读取视频第一帧")
    
    # 初始化跟踪器
    print(f"初始化跟踪器，目标区域: {init_bbox}")
    
    start_time = time.time()
    if not tracker.initialize(frame, init_bbox):
        raise ValueError("跟踪器初始化失败")
    
    init_time = time.time() - start_time
    print(f"✅ 跟踪器初始化成功 (耗时: {init_time:.3f}秒)")
    
    # 跟踪统计
    stats = {
        'start_time': time.time(),
        'frame_times': [],
        'total_frames': 0,
        'successful_frames': 0,
        'processing_times': []
    }
    
    # 基准测试数据
    if benchmark:
        benchmark_data = {
            'frame_processing_times': [],
            'confidence_scores': [],
            'bbox_stability': [],
            'skip_ratios': []
        }
    
    frame_count = 0
    
    # 处理视频帧
    print("📹 开始处理视频帧...")
    
    while ret:
        frame_start = time.time()
        
        # 跟踪当前帧
        success, bbox, confidence, info = tracker.track(frame)
        
        processing_time = time.time() - frame_start
        stats['processing_times'].append(processing_time)
        
        # 绘制跟踪结果
        if success and bbox is not None:
            x, y, w, h = [int(v) for v in bbox]
            
            # 选择颜色
            if confidence > 0.7:
                color = (0, 255, 0)  # 绿色 - 高置信度
            elif confidence > 0.4:
                color = (0, 255, 255)  # 黄色 - 中置信度  
            else:
                color = (0, 165, 255)  # 橙色 - 低置信度
            
            # 绘制边界框
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # 添加信息文本
            cv2.putText(frame, f'Frame: {frame_count + 1}/{total_frames}', 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f'Confidence: {confidence:.3f}', 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # 跟踪模式信息
            mode = "LightTrack" if tracker.model is not None else "Template"
            cv2.putText(frame, f'Mode: {mode}', 
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # 跳帧信息
            if info.get('skipped', False):
                cv2.putText(frame, 'SKIPPED (Interpolated)', 
                          (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            
            # 性能信息
            tracker_stats = tracker.get_stats()
            current_fps = tracker_stats.get('avg_fps', 0)
            cv2.putText(frame, f'Processing FPS: {current_fps:.1f}', 
                       (10, height - 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            # 成功率
            success_rate = tracker_stats.get('success_rate', 0)
            cv2.putText(frame, f'Success Rate: {success_rate:.1f}%', 
                       (10, height - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # 系统标识
            cv2.putText(frame, 'LightTrack Improved', 
                       (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            stats['successful_frames'] += 1
            
        else:
            # 跟踪失败
            cv2.putText(frame, 'Tracking Lost', (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, f'Frame: {frame_count + 1}/{total_frames}', 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # 基准测试数据收集
        if benchmark:
            benchmark_data['frame_processing_times'].append(processing_time)
            benchmark_data['confidence_scores'].append(confidence)
            if len(tracker.bbox_history) >= 2:
                # 计算bbox稳定性
                prev_bbox = tracker.bbox_history[-2]
                curr_bbox = tracker.bbox_history[-1]
                stability = np.linalg.norm(np.array(curr_bbox[:2]) - np.array(prev_bbox[:2]))
                benchmark_data['bbox_stability'].append(stability)
        
        # 写入输出视频
        out.write(frame)
        
        # 显示结果（可选）
        if display:
            cv2.imshow('LightTrack Improved', frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("用户中断跟踪")
                break
            elif key == ord(' '):  # 空格键暂停
                cv2.waitKey(0)
        
        # 读取下一帧
        ret, frame = cap.read()
        frame_count += 1
        stats['total_frames'] = frame_count
        
        # 显示进度
        if frame_count % 60 == 0:
            progress = (frame_count / total_frames) * 100
            elapsed = time.time() - stats['start_time']
            current_fps = frame_count / elapsed if elapsed > 0 else 0
            print(f"处理进度: {progress:.1f}% ({frame_count}/{total_frames}) - "
                  f"处理FPS: {current_fps:.1f}")
    
    # 清理资源
    cap.release()
    out.release()
    if display:
        cv2.destroyAllWindows()
    
    # 计算最终统计
    total_time = time.time() - stats['start_time']
    final_stats = tracker.get_stats()
    
    # 打印结果
    print_tracking_results(video_path, output_path, init_bbox, total_time, 
                          final_stats, stats, benchmark_data if benchmark else None)
    
    return output_path, final_stats


def print_tracking_results(input_path, output_path, init_bbox, total_time, 
                         tracker_stats, process_stats, benchmark_data=None):
    """打印跟踪结果"""
    
    print("\n" + "="*60)
    print("🎉 跟踪完成!")
    print("="*60)
    print(f"📁 输入视频: {os.path.basename(input_path)}")
    print(f"📁 输出视频: {os.path.basename(output_path)}")
    print(f"🎯 初始目标: [{init_bbox[0]:.1f}, {init_bbox[1]:.1f}, {init_bbox[2]:.1f}, {init_bbox[3]:.1f}]")
    
    print(f"\n📊 处理统计:")
    print(f"   总处理时间: {total_time:.2f}秒")
    print(f"   总帧数: {tracker_stats.get('total_frames', 0)}")
    print(f"   处理帧数: {tracker_stats.get('processed_frames', 0)}")
    print(f"   跳过帧数: {tracker_stats.get('skipped_frames', 0)}")
    print(f"   成功跟踪: {tracker_stats.get('successful_tracks', 0)}")
    
    print(f"\n🚀 性能指标:")
    print(f"   平均处理FPS: {tracker_stats.get('avg_fps', 0):.1f}")
    print(f"   跟踪成功率: {tracker_stats.get('success_rate', 0):.1f}%")
    
    if process_stats['processing_times']:
        avg_process_time = np.mean(process_stats['processing_times']) * 1000  # 毫秒
        print(f"   平均帧处理时间: {avg_process_time:.1f}ms")
    
    # 跳帧效率分析
    total_frames = tracker_stats.get('total_frames', 0)
    processed_frames = tracker_stats.get('processed_frames', 0)
    if total_frames > 0:
        skip_efficiency = (total_frames - processed_frames) / total_frames * 100
        print(f"   跳帧效率: {skip_efficiency:.1f}%")
    
    # 基准测试结果
    if benchmark_data:
        print(f"\n🧪 基准测试:")
        if benchmark_data['frame_processing_times']:
            avg_frame_time = np.mean(benchmark_data['frame_processing_times']) * 1000
            std_frame_time = np.std(benchmark_data['frame_processing_times']) * 1000
            print(f"   帧处理时间: {avg_frame_time:.1f}±{std_frame_time:.1f}ms")
        
        if benchmark_data['confidence_scores']:
            avg_confidence = np.mean(benchmark_data['confidence_scores'])
            print(f"   平均置信度: {avg_confidence:.3f}")
        
        if benchmark_data['bbox_stability']:
            avg_stability = np.mean(benchmark_data['bbox_stability'])
            print(f"   跟踪稳定性: {avg_stability:.1f}像素偏移")
    
    # 性能等级评估
    fps = tracker_stats.get('avg_fps', 0)
    success_rate = tracker_stats.get('success_rate', 0)
    
    if fps >= 60 and success_rate >= 90:
        grade = "🏆 优秀"
    elif fps >= 30 and success_rate >= 80:
        grade = "✅ 良好"
    elif fps >= 15 and success_rate >= 60:
        grade = "⚠️  一般"
    else:
        grade = "❌ 需要优化"
    
    print(f"\n🎖️  性能评级: {grade}")


def run_benchmark_suite(video_path, init_bbox):
    """运行性能基准测试套件"""
    print("\n🧪 运行性能基准测试套件...")
    
    test_configs = [
        {'frame_skip': 1, 'target_fps': 30, 'name': '标准配置'},
        {'frame_skip': 2, 'target_fps': 30, 'name': '2倍跳帧'},
        {'frame_skip': 3, 'target_fps': 30, 'name': '3倍跳帧'},
        {'frame_skip': 1, 'target_fps': 60, 'name': '高FPS'},
        {'frame_skip': 2, 'target_fps': 60, 'name': '高FPS+跳帧'},
    ]
    
    results = []
    
    for config in test_configs:
        print(f"\n测试配置: {config['name']}")
        try:
            output_path = f"benchmark_{config['name'].replace(' ', '_')}.mp4"
            _, stats = track_video_improved(
                video_path, init_bbox, output_path, 
                display=False, 
                frame_skip=config['frame_skip'],
                target_fps=config['target_fps'],
                benchmark=True
            )
            
            results.append({
                'config': config,
                'stats': stats,
                'output': output_path
            })
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
    
    # 打印基准测试总结
    print("\n" + "="*80)
    print("🏆 基准测试总结")
    print("="*80)
    print(f"{'配置':<15} {'FPS':<10} {'成功率':<10} {'处理帧':<10} {'跳帧效率':<10}")
    print("-" * 80)
    
    for result in results:
        config = result['config']
        stats = result['stats']
        
        fps = stats.get('avg_fps', 0)
        success_rate = stats.get('success_rate', 0)
        processed = stats.get('processed_frames', 0)
        total = stats.get('total_frames', 1)
        skip_eff = (total - processed) / total * 100
        
        print(f"{config['name']:<15} {fps:<10.1f} {success_rate:<10.1f}% "
              f"{processed:<10} {skip_eff:<10.1f}%")
    
    # 清理基准测试文件
    for result in results:
        try:
            os.remove(result['output'])
        except:
            pass


def main():
    """主函数"""
    args = parse_args()
    
    # 检查视频文件
    if not os.path.exists(args.video):
        print(f"❌ 错误: 视频文件不存在: {args.video}")
        return 1
    
    print("🚀 LightTrack 改进版命令行跟踪工具")
    print("="*50)
    
    # 获取初始边界框
    if args.bbox:
        try:
            init_bbox = parse_bbox(args.bbox)
        except ValueError as e:
            print(f"❌ 错误: {e}")
            return 1
    else:
        print("未指定边界框，将进入交互式选择模式")
        try:
            init_bbox = select_bbox_interactive(args.video)
            if init_bbox is None:
                print("未选择目标，退出程序")
                return 1
        except Exception as e:
            print(f"❌ 目标选择失败: {e}")
            return 1
    
    # 分析视频并给出建议
    if args.auto_optimize:
        video_info, suggestions = analyze_video(args.video)
        if video_info and suggestions:
            print_video_analysis(video_info, suggestions)
            
            # 应用建议
            frame_skip = suggestions['frame_skip']
            target_fps = suggestions['target_fps']
            print(f"\n🔧 应用自动优化参数: 跳帧={frame_skip}, FPS={target_fps}")
        else:
            frame_skip = args.frame_skip
            target_fps = args.target_fps
    else:
        frame_skip = args.frame_skip
        target_fps = args.target_fps
    
    # 基准测试模式
    if args.benchmark:
        run_benchmark_suite(args.video, init_bbox)
        return 0
    
    # 开始跟踪
    try:
        output_path, final_stats = track_video_improved(
            args.video, 
            init_bbox, 
            args.output, 
            args.display,
            frame_skip,
            target_fps,
            benchmark=False
        )
        
        print(f"\n✅ 处理完成! 输出文件: {output_path}")
        return 0
        
    except Exception as e:
        print(f"❌ 跟踪失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())