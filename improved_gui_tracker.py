#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的LightTrack GUI - 解决所有性能和稳定性问题
Improved LightTrack GUI - Fixes all performance and stability issues

主要改进：
1. 支持跳帧处理 - 不需要每一帧都处理，大幅提升速度
2. 提高跟踪稳定性 - 减少目标丢失，提高成功率
3. 移除演示模式 - 使用真实跟踪算法
4. 实时性能监控 - 显示FPS、成功率等关键指标
5. 用户友好界面 - 清晰的操作流程和状态反馈
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
from datetime import datetime

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from improved_tracker import ImprovedTracker


class ImprovedLightTrackGUI:
    """改进的LightTrack GUI界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("LightTrack 改进版 - 高性能目标跟踪系统")
        self.root.geometry("1200x800")
        
        # 跟踪器和状态
        self.tracker = None
        self.video_path = None
        self.tracking_thread = None
        self.is_tracking = False
        self.bbox = None
        self.pause_tracking = False
        
        # 性能参数
        self.frame_skip = tk.IntVar(value=1)      # 跳帧间隔
        self.target_fps = tk.DoubleVar(value=30.0) # 目标FPS
        
        # 统计信息
        self.stats = {
            'total_frames': 0,
            'processed_frames': 0,
            'successful_tracks': 0,
            'current_fps': 0.0,
            'success_rate': 0.0,
            'start_time': None
        }
        
        # 创建界面
        self._create_widgets()
        
        # 定期更新状态
        self.root.after(500, self._update_status_display)
    
    def _create_widgets(self):
        """创建GUI组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 1. 控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding="10")
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 文件选择
        ttk.Button(control_frame, text="选择视频文件", 
                  command=self._select_video, width=15).grid(row=0, column=0, padx=(0, 10))
        
        self.video_label = ttk.Label(control_frame, text="未选择视频文件")
        self.video_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # 跟踪控制
        ttk.Button(control_frame, text="开始跟踪", 
                  command=self._start_tracking, width=12).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(control_frame, text="暂停/继续", 
                  command=self._toggle_pause, width=12).grid(row=0, column=3, padx=(0, 5))
        ttk.Button(control_frame, text="停止", 
                  command=self._stop_tracking, width=12).grid(row=0, column=4)
        
        # 2. 性能设置面板
        settings_frame = ttk.LabelFrame(main_frame, text="性能设置", padding="10")
        settings_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 跳帧设置
        ttk.Label(settings_frame, text="跳帧间隔:").grid(row=0, column=0, padx=(0, 5))
        frame_skip_scale = ttk.Scale(settings_frame, from_=1, to=5, 
                                   variable=self.frame_skip, orient=tk.HORIZONTAL)
        frame_skip_scale.grid(row=0, column=1, padx=(0, 10), sticky=(tk.W, tk.E))
        
        self.frame_skip_label = ttk.Label(settings_frame, text="1")
        self.frame_skip_label.grid(row=0, column=2, padx=(0, 20))
        frame_skip_scale.configure(command=self._update_frame_skip_label)
        
        # FPS设置  
        ttk.Label(settings_frame, text="目标FPS:").grid(row=0, column=3, padx=(0, 5))
        fps_scale = ttk.Scale(settings_frame, from_=10.0, to=90.0,
                             variable=self.target_fps, orient=tk.HORIZONTAL)
        fps_scale.grid(row=0, column=4, padx=(0, 10), sticky=(tk.W, tk.E))
        
        self.fps_label = ttk.Label(settings_frame, text="30.0")
        self.fps_label.grid(row=0, column=5, padx=(0, 10))
        fps_scale.configure(command=self._update_fps_label)
        
        # 应用设置按钮
        ttk.Button(settings_frame, text="应用设置", 
                  command=self._apply_settings).grid(row=0, column=6)
        
        # 配置权重
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(4, weight=1)
        
        # 3. 主要内容区域
        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        content_frame.columnconfigure(0, weight=3)
        content_frame.columnconfigure(1, weight=1)
        
        # 3.1 状态信息面板
        status_frame = ttk.LabelFrame(content_frame, text="实时状态", padding="10")
        status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # 状态文本
        self.status_text = tk.Text(status_frame, height=35, width=80, 
                                  font=("Consolas", 9), wrap=tk.WORD)
        
        status_scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, 
                                       command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=status_scrollbar.set)
        
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        status_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        
        # 3.2 性能监控面板
        monitor_frame = ttk.LabelFrame(content_frame, text="性能监控", padding="10")
        monitor_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 性能指标显示
        self._create_performance_display(monitor_frame)
        
        # 4. 底部状态栏
        status_bar = ttk.Frame(main_frame)
        status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_bar_label = ttk.Label(status_bar, text="就绪 - 请选择视频文件开始跟踪")
        self.status_bar_label.grid(row=0, column=0, sticky=tk.W)
        
        # 初始化日志
        self._log("🚀 LightTrack 改进版启动完成")
        self._log("📋 主要改进: 支持跳帧处理、提升跟踪稳定性、实时性能监控")
        self._log("🎯 使用说明: 选择视频→设置参数→开始跟踪")
    
    def _create_performance_display(self, parent):
        """创建性能监控显示"""
        # FPS显示
        fps_frame = ttk.Frame(parent)
        fps_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(fps_frame, text="实时FPS:").pack(anchor=tk.W)
        self.fps_display = ttk.Label(fps_frame, text="0.0", 
                                    font=("Arial", 16, "bold"), foreground="blue")
        self.fps_display.pack(anchor=tk.W)
        
        # 成功率显示
        success_frame = ttk.Frame(parent)
        success_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(success_frame, text="跟踪成功率:").pack(anchor=tk.W)
        self.success_display = ttk.Label(success_frame, text="0%", 
                                        font=("Arial", 16, "bold"), foreground="green")
        self.success_display.pack(anchor=tk.W)
        
        # 帧统计显示
        frames_frame = ttk.Frame(parent)
        frames_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(frames_frame, text="帧统计:").pack(anchor=tk.W)
        self.frames_display = ttk.Label(frames_frame, text="总帧数: 0\n处理帧数: 0\n跳过帧数: 0")
        self.frames_display.pack(anchor=tk.W)
        
        # 跟踪状态显示
        track_frame = ttk.Frame(parent)
        track_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(track_frame, text="跟踪状态:").pack(anchor=tk.W)
        self.track_status = ttk.Label(track_frame, text="未开始", 
                                     font=("Arial", 12, "bold"), foreground="gray")
        self.track_status.pack(anchor=tk.W)
        
        # 性能建议
        advice_frame = ttk.LabelFrame(parent, text="性能建议", padding="5")
        advice_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.advice_text = tk.Text(advice_frame, height=8, width=30, 
                                  font=("Arial", 8), wrap=tk.WORD)
        self.advice_text.pack(fill=tk.BOTH, expand=True)
        
        # 初始建议
        self._update_performance_advice()
    
    def _update_frame_skip_label(self, value):
        """更新跳帧标签"""
        self.frame_skip_label.config(text=str(int(float(value))))
    
    def _update_fps_label(self, value):
        """更新FPS标签"""
        self.fps_label.config(text=f"{float(value):.1f}")
    
    def _apply_settings(self):
        """应用性能设置"""
        skip = int(self.frame_skip.get())
        fps = float(self.target_fps.get())
        
        self._log(f"⚙️  应用设置: 跳帧间隔={skip}, 目标FPS={fps:.1f}")
        
        # 如果跟踪器已经存在，更新参数
        if self.tracker is not None:
            self.tracker.frame_skip = skip
            self.tracker.target_fps = fps
            self.tracker.frame_interval = 1.0 / fps if fps > 0 else 0
        
        self._update_performance_advice()
    
    def _select_video(self):
        """选择视频文件"""
        filetypes = [
            ('视频文件', '*.mp4 *.avi *.mov *.mkv *.wmv'),
            ('所有文件', '*.*')
        ]
        
        filename = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=filetypes
        )
        
        if filename:
            self.video_path = filename
            video_name = os.path.basename(filename)
            self.video_label.config(text=f"已选择: {video_name}")
            self.status_bar_label.config(text=f"已选择视频: {video_name}")
            self._log(f"📁 选择视频文件: {filename}")
            
            # 获取视频信息
            self._analyze_video()
    
    def _analyze_video(self):
        """分析视频文件"""
        if not self.video_path:
            return
        
        try:
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self._log("❌ 无法打开视频文件")
                return
            
            # 获取视频信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = total_frames / fps if fps > 0 else 0
            
            cap.release()
            
            self._log(f"📊 视频信息:")
            self._log(f"   分辨率: {width}x{height}")
            self._log(f"   总帧数: {total_frames}")
            self._log(f"   帧率: {fps:.2f} FPS")
            self._log(f"   时长: {duration:.1f}秒")
            
            # 根据视频信息给出建议
            self._give_performance_suggestions(total_frames, fps, duration)
            
        except Exception as e:
            self._log(f"❌ 视频分析失败: {e}")
    
    def _give_performance_suggestions(self, total_frames, original_fps, duration):
        """根据视频信息给出性能建议"""
        suggestions = []
        
        if duration > 30:
            suggestions.append("长视频建议跳帧间隔设为2-3")
        
        if original_fps > 30:
            suggestions.append("高帧率视频可适当增加跳帧")
        
        if total_frames > 1000:
            suggestions.append("大量帧数建议设置较高跳帧间隔")
        
        if suggestions:
            self._log("💡 性能建议:")
            for suggestion in suggestions:
                self._log(f"   • {suggestion}")
    
    def _start_tracking(self):
        """开始跟踪"""
        if not self.video_path:
            messagebox.showerror("错误", "请先选择视频文件")
            return
        
        if self.is_tracking:
            messagebox.showwarning("警告", "跟踪正在进行中")
            return
        
        # 交互式选择目标
        try:
            bbox = self._select_target_interactive()
            if bbox is None:
                return
            
            self.bbox = bbox
            self._log(f"🎯 选择目标区域: [{bbox[0]:.1f}, {bbox[1]:.1f}, {bbox[2]:.1f}, {bbox[3]:.1f}]")
            
            # 创建跟踪器
            skip = int(self.frame_skip.get())
            fps = float(self.target_fps.get())
            
            self.tracker = ImprovedTracker(frame_skip=skip, target_fps=fps)
            
            # 开始跟踪线程
            self.is_tracking = True
            self.pause_tracking = False
            self.stats['start_time'] = time.time()
            
            self.tracking_thread = threading.Thread(target=self._tracking_worker)
            self.tracking_thread.daemon = True
            self.tracking_thread.start()
            
            self.status_bar_label.config(text="跟踪进行中...")
            self._log("🚀 开始跟踪处理")
            
        except Exception as e:
            self._log(f"❌ 启动跟踪失败: {e}")
    
    def _select_target_interactive(self):
        """交互式选择跟踪目标"""
        self._log("👆 请在弹出窗口中框选跟踪目标...")
        
        cap = cv2.VideoCapture(self.video_path)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise ValueError("无法读取视频第一帧")
        
        # 显示选择界面
        bbox = cv2.selectROI("选择跟踪目标 - 框选后按ENTER确认", frame, False)
        cv2.destroyWindow("选择跟踪目标 - 框选后按ENTER确认")
        
        if bbox[2] > 0 and bbox[3] > 0:  # 有效选择
            return list(bbox)
        else:
            return None
    
    def _tracking_worker(self):
        """跟踪工作线程"""
        try:
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self._log("❌ 无法打开视频文件")
                return
            
            # 获取视频信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            original_fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # 准备输出视频
            output_path = os.path.splitext(self.video_path)[0] + "_tracked_improved.mp4"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, original_fps, (width, height))
            
            # 读取第一帧并初始化
            ret, frame = cap.read()
            if not ret:
                self._log("❌ 无法读取第一帧")
                return
            
            # 初始化跟踪器
            if not self.tracker.initialize(frame, self.bbox):
                self._log("❌ 跟踪器初始化失败")
                return
            
            self._log("✅ 跟踪器初始化成功，开始处理视频")
            
            frame_count = 0
            start_time = time.time()
            
            # 处理视频帧
            while ret and self.is_tracking:
                # 检查暂停
                while self.pause_tracking and self.is_tracking:
                    time.sleep(0.1)
                
                if not self.is_tracking:
                    break
                
                # 跟踪当前帧
                success, bbox, confidence, info = self.tracker.track(frame)
                
                # 更新统计
                self.stats['total_frames'] = frame_count + 1
                tracker_stats = self.tracker.get_stats()
                self.stats.update(tracker_stats)
                
                # 绘制跟踪结果
                if success and bbox is not None:
                    x, y, w, h = [int(v) for v in bbox]
                    
                    # 绘制边界框
                    color = (0, 255, 0) if confidence > 0.6 else (0, 255, 255)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    
                    # 添加信息文本
                    cv2.putText(frame, f'Frame: {frame_count + 1}/{total_frames}', 
                              (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.putText(frame, f'Confidence: {confidence:.2f}', 
                              (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                    # 跳帧信息
                    if info.get('skipped', False):
                        cv2.putText(frame, 'SKIPPED (Interpolated)', 
                                  (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                    
                    # FPS信息
                    current_fps = tracker_stats.get('avg_fps', 0)
                    cv2.putText(frame, f'FPS: {current_fps:.1f}', 
                              (10, height - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    
                    # 跟踪模式
                    mode = "LightTrack" if self.tracker.model is not None else "Template"
                    cv2.putText(frame, f'Mode: {mode}', 
                              (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                else:
                    # 跟踪失败
                    cv2.putText(frame, 'Tracking Lost', (10, 30), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # 写入输出视频
                out.write(frame)
                
                # 读取下一帧
                ret, frame = cap.read()
                frame_count += 1
                
                # 定期更新界面（每30帧）
                if frame_count % 30 == 0:
                    progress = (frame_count / total_frames) * 100
                    elapsed_time = time.time() - start_time
                    
                    self.root.after_idle(lambda p=progress, t=elapsed_time: 
                                        self._update_tracking_progress(p, t))
            
            # 清理资源
            cap.release()
            out.release()
            
            # 完成处理
            total_time = time.time() - start_time
            final_stats = self.tracker.get_stats()
            
            self.root.after_idle(lambda: self._tracking_complete(output_path, total_time, final_stats))
            
        except Exception as e:
            self.root.after_idle(lambda: self._log(f"❌ 跟踪过程出错: {e}"))
        finally:
            self.is_tracking = False
    
    def _update_tracking_progress(self, progress, elapsed_time):
        """更新跟踪进度"""
        self._log(f"📊 处理进度: {progress:.1f}% (用时: {elapsed_time:.1f}秒)")
        self.status_bar_label.config(text=f"跟踪进度: {progress:.1f}%")
    
    def _tracking_complete(self, output_path, total_time, final_stats):
        """跟踪完成处理"""
        self.is_tracking = False
        
        self._log("🎉 跟踪处理完成!")
        self._log(f"📁 输出文件: {output_path}")
        self._log(f"⏱️  总用时: {total_time:.2f}秒")
        self._log(f"📊 最终统计:")
        self._log(f"   总帧数: {final_stats.get('total_frames', 0)}")
        self._log(f"   处理帧数: {final_stats.get('processed_frames', 0)}")
        self._log(f"   跳过帧数: {final_stats.get('skipped_frames', 0)}")
        self._log(f"   成功率: {final_stats.get('success_rate', 0):.1f}%")
        self._log(f"   平均FPS: {final_stats.get('avg_fps', 0):.1f}")
        
        self.status_bar_label.config(text="跟踪完成!")
        
        # 询问是否打开输出文件夹
        if messagebox.askyesno("完成", f"跟踪完成!\n输出文件: {os.path.basename(output_path)}\n\n是否打开文件所在文件夹?"):
            os.startfile(os.path.dirname(output_path))
    
    def _toggle_pause(self):
        """切换暂停状态"""
        if not self.is_tracking:
            return
        
        self.pause_tracking = not self.pause_tracking
        status = "暂停" if self.pause_tracking else "继续"
        self._log(f"⏸️  跟踪{status}")
        self.status_bar_label.config(text=f"跟踪{status}中...")
    
    def _stop_tracking(self):
        """停止跟踪"""
        if not self.is_tracking:
            return
        
        self.is_tracking = False
        self.pause_tracking = False
        self._log("🛑 停止跟踪")
        self.status_bar_label.config(text="跟踪已停止")
    
    def _update_status_display(self):
        """更新状态显示"""
        try:
            if self.tracker is not None:
                stats = self.tracker.get_stats()
                
                # 更新FPS显示
                fps = stats.get('avg_fps', 0)
                self.fps_display.config(text=f"{fps:.1f}")
                
                # 更新成功率显示  
                success_rate = stats.get('success_rate', 0)
                self.success_display.config(text=f"{success_rate:.1f}%")
                
                # 更新帧统计
                total = stats.get('total_frames', 0)
                processed = stats.get('processed_frames', 0)
                skipped = stats.get('skipped_frames', 0)
                self.frames_display.config(text=f"总帧数: {total}\n处理帧数: {processed}\n跳过帧数: {skipped}")
                
                # 更新跟踪状态
                if self.is_tracking:
                    if self.pause_tracking:
                        status_text = "暂停中"
                        status_color = "orange"
                    else:
                        status_text = "跟踪中"
                        status_color = "green"
                else:
                    status_text = "就绪"
                    status_color = "blue"
                
                self.track_status.config(text=status_text, foreground=status_color)
            
        except Exception:
            pass  # 忽略更新错误
        
        # 继续定期更新
        self.root.after(500, self._update_status_display)
    
    def _update_performance_advice(self):
        """更新性能建议"""
        skip = int(self.frame_skip.get())
        fps = float(self.target_fps.get())
        
        advice = []
        
        if skip == 1:
            advice.append("跳帧间隔=1: 最高质量，但速度较慢")
        elif skip == 2:
            advice.append("跳帧间隔=2: 平衡质量与速度")
        elif skip >= 3:
            advice.append("跳帧间隔≥3: 高速处理，质量稍降")
        
        if fps <= 15:
            advice.append("低FPS: 省资源，适合慢速跟踪")
        elif fps <= 30:
            advice.append("中FPS: 适合一般跟踪应用")
        else:
            advice.append("高FPS: 高性能需求，适合快速目标")
        
        advice.append(f"\n预估加速比: {skip}x")
        advice.append(f"理论处理速度: {fps * skip:.1f} fps")
        
        self.advice_text.delete(1.0, tk.END)
        self.advice_text.insert(1.0, "\n".join(advice))
    
    def _log(self, message):
        """添加日志消息"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_message = f"[{timestamp}] {message}\n"
            
            # 线程安全的UI更新
            self.root.after_idle(self._append_log, log_message)
            
        except Exception:
            # Fallback to print if GUI is not available
            print(f"[{timestamp}] {message}")
    
    def _append_log(self, message):
        """追加日志到文本框"""
        try:
            self.status_text.insert(tk.END, message)
            self.status_text.see(tk.END)
            
            # 限制日志长度
            lines = self.status_text.get(1.0, tk.END).count('\n')
            if lines > 1000:
                self.status_text.delete(1.0, "100.0")
                
        except Exception:
            pass


def main():
    """主函数"""
    try:
        # 检查依赖
        import cv2
        import numpy as np
        print("✅ 依赖检查通过")
    except ImportError as e:
        print(f"❌ 依赖缺失: {e}")
        print("请安装: pip install opencv-python numpy torch torchvision pillow")
        return
    
    # 创建GUI应用
    root = tk.Tk()
    app = ImprovedLightTrackGUI(root)
    
    # 设置窗口关闭处理
    def on_closing():
        if app.is_tracking:
            if messagebox.askokcancel("退出", "跟踪正在进行中，确定要退出吗？"):
                app._stop_tracking()
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # 启动GUI
    print("🚀 启动改进版LightTrack GUI")
    root.mainloop()


if __name__ == "__main__":
    main()