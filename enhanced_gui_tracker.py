#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的LightTrack GUI - 集成优化跟踪器
解决跟踪性能和准确性问题
"""

import os
import sys
import cv2
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
from PIL import Image, ImageTk
import threading
import time

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from optimized_tracker import OptimizedTracker


class EnhancedLightTrackGUI:
    """增强的LightTrack GUI"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("LightTrack - 增强版目标跟踪系统")
        self.root.geometry("1000x700")
        
        # 初始化变量
        self.video_path = None
        self.tracker = None
        self.tracking_thread = None
        self.is_tracking = False
        self.bbox = None
        
        # 性能监控
        self.performance_stats = {
            'fps': 0.0,
            'success_rate': 0.0,
            'processed_frames': 0,
            'successful_frames': 0
        }
        
        # 创建界面
        self._create_widgets()
        
        # 初始化跟踪器
        self._initialize_tracker()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标题
        title_label = ttk.Label(main_frame, text="LightTrack 增强版目标跟踪系统", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # 控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 文件选择
        file_frame = ttk.Frame(control_frame)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(file_frame, text="选择视频文件", 
                  command=self._select_video).pack(side=tk.LEFT, padx=(0, 10))
        
        self.file_label = ttk.Label(file_frame, text="未选择文件", foreground="gray")
        self.file_label.pack(side=tk.LEFT)
        
        # 跟踪控制
        track_frame = ttk.Frame(control_frame)
        track_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_button = ttk.Button(track_frame, text="开始跟踪", 
                                      command=self._start_tracking, state=tk.DISABLED)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(track_frame, text="停止跟踪", 
                                     command=self._stop_tracking, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 性能监控面板
        perf_frame = ttk.LabelFrame(main_frame, text="性能监控", padding=10)
        perf_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 性能指标
        perf_info_frame = ttk.Frame(perf_frame)
        perf_info_frame.pack(fill=tk.X)
        
        # FPS显示
        fps_frame = ttk.Frame(perf_info_frame)
        fps_frame.pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(fps_frame, text="FPS:").pack(side=tk.LEFT)
        self.fps_var = tk.StringVar(value="0.0")
        ttk.Label(fps_frame, textvariable=self.fps_var, font=('Arial', 12, 'bold'), 
                 foreground="blue").pack(side=tk.LEFT, padx=(5, 0))
        
        # 成功率显示
        success_frame = ttk.Frame(perf_info_frame)
        success_frame.pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(success_frame, text="成功率:").pack(side=tk.LEFT)
        self.success_var = tk.StringVar(value="0.0%")
        ttk.Label(success_frame, textvariable=self.success_var, font=('Arial', 12, 'bold'), 
                 foreground="green").pack(side=tk.LEFT, padx=(5, 0))
        
        # 处理帧数显示
        frames_frame = ttk.Frame(perf_info_frame)
        frames_frame.pack(side=tk.LEFT)
        ttk.Label(frames_frame, text="处理帧数:").pack(side=tk.LEFT)
        self.frames_var = tk.StringVar(value="0")
        ttk.Label(frames_frame, textvariable=self.frames_var, font=('Arial', 12, 'bold'), 
                 foreground="purple").pack(side=tk.LEFT, padx=(5, 0))
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(perf_frame, variable=self.progress_var, 
                                           maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(10, 0))
        
        # 日志面板
        log_frame = ttk.LabelFrame(main_frame, text="系统日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建带滚动条的文本框
        log_text_frame = ttk.Frame(log_frame)
        log_text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_text_frame, wrap=tk.WORD, height=15, 
                               font=('Courier', 10))
        log_scrollbar = ttk.Scrollbar(log_text_frame, orient=tk.VERTICAL, 
                                     command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 底部状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var, 
                 relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X)
    
    def _initialize_tracker(self):
        """初始化跟踪器"""
        self.log("🚀 初始化增强跟踪系统...")
        
        try:
            self.tracker = OptimizedTracker()
            self.log("✅ 跟踪器初始化完成")
            
            # 显示跟踪器信息
            stats = self.tracker.get_stats()
            self.log(f"📊 跟踪器类型: {stats['model_type']}")
            self.log(f"🖥️  计算设备: {stats['device']}")
            
            if stats['model_type'] == 'LightTrack':
                self.log("🎯 使用真实LightTrack模型 - 预期高性能跟踪")
            else:
                self.log("🎭 使用优化演示模式 - 快速跟踪算法")
            
        except Exception as e:
            self.log(f"❌ 跟踪器初始化失败: {e}")
            messagebox.showerror("错误", f"跟踪器初始化失败:\n{e}")
    
    def log(self, message):
        """添加日志信息"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        # 线程安全的UI更新
        def update_log():
            self.log_text.insert(tk.END, log_message)
            self.log_text.see(tk.END)
        
        self.root.after(0, update_log)
    
    def _select_video(self):
        """选择视频文件"""
        file_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[
                ("视频文件", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv"),
                ("MP4文件", "*.mp4"),
                ("AVI文件", "*.avi"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            self.video_path = file_path
            filename = os.path.basename(file_path)
            self.file_label.config(text=filename, foreground="black")
            self.start_button.config(state=tk.NORMAL)
            self.log(f"📁 选择视频文件: {filename}")
            
            # 获取视频信息
            self._get_video_info(file_path)
    
    def _get_video_info(self, video_path):
        """获取视频信息"""
        try:
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
                
                self.log(f"📺 视频信息: {width}x{height}, {fps:.1f}fps, "
                        f"{frame_count}帧, {duration:.1f}秒")
                cap.release()
        except Exception as e:
            self.log(f"⚠️  获取视频信息失败: {e}")
    
    def _start_tracking(self):
        """开始跟踪"""
        if not self.video_path or not os.path.exists(self.video_path):
            messagebox.showerror("错误", "请先选择有效的视频文件")
            return
        
        if self.is_tracking:
            messagebox.showwarning("警告", "跟踪已在进行中")
            return
        
        # 目标选择
        self._select_target()
    
    def _select_target(self):
        """选择跟踪目标"""
        try:
            cap = cv2.VideoCapture(self.video_path)
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                messagebox.showerror("错误", "无法读取视频第一帧")
                return
            
            self.log("🎯 请在弹出的窗口中选择跟踪目标...")
            
            # 创建目标选择窗口
            bbox = self._interactive_bbox_selection(frame)
            
            if bbox:
                self.bbox = bbox
                self.log(f"✅ 目标选择完成: {bbox}")
                self._start_tracking_thread()
            else:
                self.log("❌ 目标选择取消")
        
        except Exception as e:
            self.log(f"❌ 目标选择失败: {e}")
            messagebox.showerror("错误", f"目标选择失败:\n{e}")
    
    def _interactive_bbox_selection(self, frame):
        """交互式边界框选择"""
        bbox = None
        selecting = False
        start_point = None
        
        def mouse_callback(event, x, y, flags, param):
            nonlocal bbox, selecting, start_point
            
            if event == cv2.EVENT_LBUTTONDOWN:
                selecting = True
                start_point = (x, y)
                
            elif event == cv2.EVENT_MOUSEMOVE and selecting:
                temp_frame = frame.copy()
                cv2.rectangle(temp_frame, start_point, (x, y), (0, 255, 0), 2)
                cv2.imshow('选择目标 - 拖拽选择，Enter确认，ESC取消', temp_frame)
                
            elif event == cv2.EVENT_LBUTTONUP and selecting:
                selecting = False
                x1, y1 = start_point
                x2, y2 = x, y
                
                x1, x2 = min(x1, x2), max(x1, x2)
                y1, y2 = min(y1, y2), max(y1, y2)
                
                if x2 - x1 > 10 and y2 - y1 > 10:
                    bbox = [x1, y1, x2 - x1, y2 - y1]
                    temp_frame = frame.copy()
                    cv2.rectangle(temp_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(temp_frame, f'Target: {bbox}', (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.imshow('选择目标 - 拖拽选择，Enter确认，ESC取消', temp_frame)
        
        cv2.namedWindow('选择目标 - 拖拽选择，Enter确认，ESC取消')
        cv2.setMouseCallback('选择目标 - 拖拽选择，Enter确认，ESC取消', mouse_callback)
        cv2.imshow('选择目标 - 拖拽选择，Enter确认，ESC取消', frame)
        
        while True:
            key = cv2.waitKey(1) & 0xFF
            if key == 13 and bbox is not None:  # Enter
                break
            elif key == 27:  # ESC
                bbox = None
                break
        
        cv2.destroyAllWindows()
        return bbox
    
    def _start_tracking_thread(self):
        """启动跟踪线程"""
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.log("⚠️  跟踪线程已在运行")
            return
        
        self.is_tracking = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # 重置性能统计
        self.performance_stats = {
            'fps': 0.0,
            'success_rate': 0.0,
            'processed_frames': 0,
            'successful_frames': 0
        }
        
        self.tracking_thread = threading.Thread(target=self._track_video, daemon=True)
        self.tracking_thread.start()
        
        self.log("🚀 开始跟踪...")
    
    def _track_video(self):
        """执行视频跟踪（在后台线程中运行）"""
        try:
            cap = cv2.VideoCapture(self.video_path)
            
            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # 创建输出视频
            output_path = os.path.splitext(self.video_path)[0] + '_tracked_enhanced.mp4'
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            # 读取第一帧并初始化跟踪器
            ret, frame = cap.read()
            if not ret:
                self.log("❌ 无法读取视频第一帧")
                return
            
            # 初始化跟踪器
            if not self.tracker.initialize(frame, self.bbox):
                self.log("❌ 跟踪器初始化失败")
                return
            
            self.log("✅ 跟踪器初始化成功，开始处理视频...")
            
            frame_count = 0
            start_time = time.time()
            
            # 重置视频到开始
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            while self.is_tracking:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 执行跟踪
                success, bbox, confidence = self.tracker.track(frame)
                
                # 更新统计信息
                frame_count += 1
                self.performance_stats['processed_frames'] = frame_count
                if success:
                    self.performance_stats['successful_frames'] += 1
                
                # 计算成功率和FPS
                if frame_count > 0:
                    self.performance_stats['success_rate'] = \
                        (self.performance_stats['successful_frames'] / frame_count) * 100
                
                # 绘制跟踪结果
                display_frame = frame.copy()
                x, y, w, h = [int(v) for v in bbox]
                
                if success:
                    # 成功跟踪 - 绿色框
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(display_frame, f'TRACKING conf={confidence:.2f}', 
                               (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    # 跟踪失败 - 红色框
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                    cv2.putText(display_frame, f'LOST conf={confidence:.2f}', 
                               (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # 添加信息文本
                tracker_stats = self.tracker.get_stats()
                cv2.putText(display_frame, f'Frame: {frame_count}/{total_frames}', 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(display_frame, f'FPS: {tracker_stats["fps"]:.1f}', 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(display_frame, f'Success: {self.performance_stats["success_rate"]:.1f}%', 
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(display_frame, f'LightTrack Enhanced', 
                           (10, height-20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                
                # 写入输出视频
                out.write(display_frame)
                
                # 更新UI（每10帧更新一次）
                if frame_count % 10 == 0:
                    progress = (frame_count / total_frames) * 100
                    self._update_ui_stats(tracker_stats, progress)
                
                # 输出进度日志（每30帧一次）
                if frame_count % 30 == 0:
                    self.log(f"📊 帧{frame_count}/{total_frames}: "
                           f"FPS={tracker_stats['fps']:.1f}, "
                           f"成功率={self.performance_stats['success_rate']:.1f}%")
            
            # 完成处理
            total_time = time.time() - start_time
            actual_fps = frame_count / total_time if total_time > 0 else 0
            
            cap.release()
            out.release()
            
            if self.is_tracking:  # 正常完成，而非被停止
                self.log(f"🎉 跟踪完成!")
                self.log(f"📊 最终统计:")
                self.log(f"   处理帧数: {frame_count}")
                self.log(f"   成功帧数: {self.performance_stats['successful_frames']}")
                self.log(f"   成功率: {self.performance_stats['success_rate']:.1f}%")
                self.log(f"   平均FPS: {actual_fps:.1f}")
                self.log(f"   总时间: {total_time:.2f}秒")
                self.log(f"📹 输出文件: {os.path.basename(output_path)}")
                
                # 显示完成对话框
                self.root.after(0, lambda: messagebox.showinfo(
                    "跟踪完成", 
                    f"视频跟踪已完成！\n\n"
                    f"处理帧数: {frame_count}\n"
                    f"成功率: {self.performance_stats['success_rate']:.1f}%\n"
                    f"平均FPS: {actual_fps:.1f}\n"
                    f"输出文件: {os.path.basename(output_path)}"
                ))
            else:
                self.log("⏹️  跟踪被用户停止")
        
        except Exception as e:
            self.log(f"❌ 跟踪过程出错: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.is_tracking = False
            self.root.after(0, self._reset_ui)
    
    def _update_ui_stats(self, tracker_stats, progress):
        """更新UI统计信息"""
        def update():
            self.fps_var.set(f"{tracker_stats['fps']:.1f}")
            self.success_var.set(f"{self.performance_stats['success_rate']:.1f}%")
            self.frames_var.set(str(self.performance_stats['processed_frames']))
            self.progress_var.set(progress)
            self.status_var.set(f"跟踪中... {progress:.1f}%")
        
        self.root.after(0, update)
    
    def _reset_ui(self):
        """重置UI状态"""
        self.start_button.config(state=tk.NORMAL if self.video_path else tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("就绪")
    
    def _stop_tracking(self):
        """停止跟踪"""
        if self.is_tracking:
            self.is_tracking = False
            self.log("⏹️  停止跟踪...")
            self.status_var.set("正在停止...")


def main():
    """主函数"""
    root = tk.Tk()
    app = EnhancedLightTrackGUI(root)
    
    # 设置窗口图标和其他属性
    try:
        # 如果有图标文件，可以设置
        # root.iconbitmap("icon.ico")
        pass
    except:
        pass
    
    # 处理窗口关闭事件
    def on_closing():
        if app.is_tracking:
            if messagebox.askokcancel("退出", "跟踪正在进行中，确定要退出吗？"):
                app.is_tracking = False
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # 启动GUI
    root.mainloop()


if __name__ == '__main__':
    main()