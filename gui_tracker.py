#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LightTrack GUI应用程序
支持选择视频文件，框选目标，并进行自动跟踪
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

try:
    from tracking._init_paths import *
    import lib.models.models as models
    from lib.utils.utils import load_pretrain, cxy_wh_2_rect, get_axis_aligned_bbox
    from lib.tracker.lighttrack import Lighttrack
    from easydict import EasyDict as edict
    LIGHTTRACK_DEPENDENCIES_AVAILABLE = True
    
    # 尝试加载torch检查
    try:
        import torch
        TORCH_AVAILABLE = True
        if torch.cuda.is_available():
            CUDA_AVAILABLE = True
        else:
            CUDA_AVAILABLE = False
    except ImportError:
        TORCH_AVAILABLE = False
        CUDA_AVAILABLE = False
        
except ImportError as e:
    print(f"LightTrack核心依赖导入错误: {e}")
    print("某些高级功能将不可用，但GUI仍可运行在演示模式")
    LIGHTTRACK_DEPENDENCIES_AVAILABLE = False
    TORCH_AVAILABLE = False  
    CUDA_AVAILABLE = False
    
    # Create dummy classes/functions to prevent NameError
    edict = dict
    Lighttrack = object

# 基础GUI依赖检查
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    GUI_AVAILABLE = True
except ImportError:
    print("错误: tkinter未安装，GUI无法启动")
    print("请安装tkinter: sudo apt-get install python3-tk")
    GUI_AVAILABLE = False
    exit(1)

# 其他基础依赖
try:
    import cv2
    import numpy as np
    from PIL import Image, ImageTk
    BASIC_DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"基础依赖缺失: {e}")
    print("请安装: pip install opencv-python numpy pillow")
    BASIC_DEPENDENCIES_AVAILABLE = False
    exit(1)


class VideoSelector:
    """视频选择和目标框选类"""
    
    def __init__(self, video_path):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.bbox = None
        self.selecting = False
        self.start_point = None
        
        # 读取第一帧
        ret, self.first_frame = self.cap.read()
        if not ret:
            raise ValueError("无法读取视频文件")
        
        self.display_frame = self.first_frame.copy()

    def mouse_callback(self, event, x, y, flags, param):
        """鼠标回调函数"""
        window_name = '选择目标'

        if event == cv2.EVENT_LBUTTONDOWN:
            self.selecting = True
            self.start_point = (x, y)

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.selecting:
                # 绘制临时矩形
                temp_frame = self.first_frame.copy()
                cv2.rectangle(temp_frame, self.start_point, (x, y), (0, 255, 0), 2)
                cv2.imshow(window_name, temp_frame)

        elif event == cv2.EVENT_LBUTTONUP:
            if self.selecting:
                self.selecting = False
                end_point = (x, y)

                # 计算边界框
                x1 = min(self.start_point[0], end_point[0])
                y1 = min(self.start_point[1], end_point[1])
                x2 = max(self.start_point[0], end_point[0])
                y2 = max(self.start_point[1], end_point[1])

                if x2 - x1 > 10 and y2 - y1 > 10:  # 最小尺寸检查
                    self.bbox = [x1, y1, x2 - x1, y2 - y1]
                    # 绘制最终矩形
                    cv2.rectangle(self.display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.imshow(window_name, self.display_frame)

    def select_target(self):
        """使用Tkinter选择目标"""
        # 创建新窗口
        select_window = tk.Toplevel()
        select_window.title("选择目标 - 拖拽鼠标框选目标，按ESC取消，按ENTER确认")

        # 转换图像格式用于Tkinter显示
        img_rgb = cv2.cvtColor(self.first_frame, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        img_tk = ImageTk.PhotoImage(img_pil)

        # 创建画布
        canvas = tk.Canvas(select_window, width=img_pil.width, height=img_pil.height)
        canvas.pack()
        canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)

        # 初始化选择变量
        self.bbox = None
        start_x, start_y = 0, 0
        rect_id = None

        def on_button_press(event):
            nonlocal start_x, start_y, rect_id
            start_x, start_y = event.x, event.y
            rect_id = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='green', width=2)

        def on_motion(event):
            nonlocal rect_id
            if rect_id:
                canvas.coords(rect_id, start_x, start_y, event.x, event.y)

        def on_button_release(event):
            nonlocal rect_id
            if rect_id:
                x1, y1, x2, y2 = canvas.coords(rect_id)
                self.bbox = [min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)]
                canvas.delete(rect_id)
                rect_id = None
                canvas.create_rectangle(x1, y1, x2, y2, outline='green', width=2)

        def on_key_press(event):
            if event.keysym == 'Return' and self.bbox:
                select_window.quit()
            elif event.keysym == 'Escape':
                self.bbox = None
                select_window.quit()

        # 绑定事件
        canvas.bind("<ButtonPress-1>", on_button_press)
        canvas.bind("<B1-Motion>", on_motion)
        canvas.bind("<ButtonRelease-1>", on_button_release)
        select_window.bind("<Key>", on_key_press)

        # 聚焦到画布
        canvas.focus_set()

        # 运行窗口
        select_window.mainloop()
        select_window.destroy()

        return self.bbox


class LightTrackGUI:
    """LightTrack GUI主类"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("LightTrack 视频目标跟踪系统")
        self.root.geometry("800x600")
        
        # 初始化变量
        self.video_path = None
        self.output_path = None
        self.bbox = None
        self.tracker = None
        self.model = None
        self.tracking_thread = None
        self.is_tracking = False
        
        self.setup_ui()
        self.load_model()
    
    def _safe_extract_scalar(self, value):
        """安全地从可能的数组或序列中提取标量值"""
        if hasattr(value, 'item'):  # NumPy scalar/array
            if value.size == 1:
                return float(value.item())
            else:
                # Handle multi-dimensional arrays by flattening
                flat = value.flatten()
                return float(flat[0])
        elif hasattr(value, '__iter__') and not isinstance(value, str):  # List/tuple/sequence
            return float(value[0])
        else:
            return float(value)
    
    def _safe_extract_coordinate(self, pos_array, index):
        """安全地从位置数组中提取坐标值，处理不同的数组结构"""
        if hasattr(pos_array, 'shape') and len(pos_array.shape) > 1:
            # Handle 2D arrays like [[x, y]] -> extract x or y
            flat = pos_array.flatten()
            if index < len(flat):
                return float(flat[index])
            else:
                raise IndexError(f"Index {index} out of bounds for flattened array of size {len(flat)}")
        else:
            # Handle 1D arrays, lists, etc.
            return self._safe_extract_scalar(pos_array[index])
    
    def setup_ui(self):
        """设置用户界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 标题
        title_label = ttk.Label(main_frame, text="LightTrack",
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 视频选择区域
        video_frame = ttk.LabelFrame(main_frame, text="VideoSelect", padding="10")
        video_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.video_path_var = tk.StringVar()
        ttk.Label(video_frame, text="视频文件:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(video_frame, textvariable=self.video_path_var, width=50, state='readonly').grid(row=0, column=1, padx=(5, 5))
        ttk.Button(video_frame, text="选择视频", command=self.select_video).grid(row=0, column=2)
        
        # 目标选择区域
        target_frame = ttk.LabelFrame(main_frame, text="目标选择", padding="10")
        target_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.bbox_var = tk.StringVar(value="未选择")
        ttk.Label(target_frame, text="目标边界框:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(target_frame, textvariable=self.bbox_var).grid(row=0, column=1, padx=(5, 5))
        ttk.Button(target_frame, text="框选目标", command=self.select_target).grid(row=0, column=2)
        
        # 跟踪控制区域
        control_frame = ttk.LabelFrame(main_frame, text="跟踪控制", padding="10")
        control_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.start_button = ttk.Button(control_frame, text="开始跟踪", command=self.start_tracking)
        self.start_button.grid(row=0, column=0, padx=(0, 5))
        
        self.stop_button = ttk.Button(control_frame, text="停止跟踪", command=self.stop_tracking, state='disabled')
        self.stop_button.grid(row=0, column=1, padx=(0, 5))
        
        ttk.Button(control_frame, text="保存结果", command=self.save_result).grid(row=0, column=2)
        
        # 进度显示区域
        progress_frame = ttk.LabelFrame(main_frame, text="跟踪进度", padding="10")
        progress_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.progress_var = tk.StringVar(value="等待开始...")
        ttk.Label(progress_frame, textvariable=self.progress_var).grid(row=0, column=0, sticky=tk.W)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # 日志显示区域
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding="10")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.log_text = tk.Text(log_frame, height=15, width=80)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 配置权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        video_frame.columnconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
    
    def log(self, message):
        """添加日志信息 - 线程安全版本"""
        def _log_safe():
            try:
                timestamp = time.strftime("%H:%M:%S")
                log_message = f"[{timestamp}] {message}\n"
                self.log_text.insert(tk.END, log_message)
                self.log_text.see(tk.END)
                self.root.update_idletasks()
            except Exception as e:
                print(f"Log error: {e}")
        
        # Always use after() to ensure thread safety
        try:
            self.root.after(0, _log_safe)
        except Exception as e:
            # Fallback to print if GUI is not available
            print(f"[{time.strftime('%H:%M:%S')}] {message}")
    
    def load_model(self):
        """加载预训练模型"""
        try:
            self.log("正在加载LightTrack模型...")
            
            if not LIGHTTRACK_DEPENDENCIES_AVAILABLE:
                self.log("警告: LightTrack核心依赖未完全安装")
                self.log("可用功能: GUI界面、演示跟踪")
                self.log("不可用功能: 真实LightTrack算法")
                self.log("模型将在演示模式下运行")
                self.tracker = None
                self.model = None
                return
            
            if not TORCH_AVAILABLE:
                self.log("警告: PyTorch未安装，无法使用真实模型")
                self.log("将使用演示模式进行跟踪")
                self.tracker = None
                self.model = None
                return
            
            # 检查多个可能的模型路径
            model_paths = [
                os.path.join(current_dir, 'snapshot', 'checkpoint_e30.pth'),
                os.path.join(current_dir, 'snapshot', 'LightTrackM', 'LightTrackM.pth'),
                os.path.join(current_dir, 'snapshot', 'LightTrackM.pth')
            ]
            
            model_path = None
            for path in model_paths:
                if os.path.exists(path):
                    model_path = path
                    break
            
            if not model_path:
                self.log("警告: 未找到预训练模型文件")
                self.log("请将模型文件放置到以下位置之一:")
                for path in model_paths:
                    self.log(f"  - {path}")
                self.log("将使用演示模式进行跟踪")
                # 仍然初始化跟踪器用于演示模式
                self.tracker = None
                self.model = None
                return
            
            # 模型配置
            info = edict()
            info.arch = 'LightTrackM_Subnet'  # 默认架构
            info.dataset = 'VOT2019'
            info.stride = 16
            
            # 初始化跟踪器
            self.tracker = Lighttrack(info)
            
            # 加载模型
            try:
                if CUDA_AVAILABLE:
                    self.log("检测到CUDA，使用GPU加速")
                    device = 'cuda'
                else:
                    self.log("未检测到CUDA，使用CPU")
                    device = 'cpu'
                
                # 创建模型实例
                # 对于LightTrackM_Subnet，需要提供path_name参数
                if info.arch == 'LightTrackM_Subnet':
                    # LightTrackM_Subnet需要path_name参数，使用LightTrack-Mobile的标准配置
                    # 这个path_name定义了网络的具体架构配置：
                    # back_04502514044521042540 - backbone架构配置
                    # cls_211000022 - 分类头配置  
                    # reg_100000111 - 回归头配置
                    # ops_32 - 操作配置
                    model = models.LightTrackM_Subnet(path_name='back_04502514044521042540+cls_211000022+reg_100000111_ops_32', stride=info.stride)
                elif hasattr(models, info.arch):
                    # 其他模型可能不需要path_name参数
                    try:
                        model = models.__dict__[info.arch](stride=info.stride)
                    except TypeError as e:
                        # 如果需要额外参数，尝试提供默认值
                        self.log(f"模型构造需要额外参数: {e}")
                        if 'path_name' in str(e):
                            model = models.__dict__[info.arch](path_name='back_04502514044521042540+cls_211000022+reg_100000111_ops_32', stride=info.stride)
                        else:
                            raise
                else:
                    raise ValueError(f"未知的模型架构: {info.arch}")
                
                model = model.to(device)
                model.eval()
                
                # 加载预训练权重
                self.log(f"正在加载模型权重: {model_path}")
                model = load_pretrain(model, model_path, print_unuse=False)
                
                self.model = model
                self.device = device
                self.log("模型加载完成")
                
            except Exception as e:
                self.log(f"模型加载失败: {e}")
                self.log("将使用演示模式进行跟踪")
                self.model = None
                
        except Exception as e:
            self.log(f"模型初始化失败: {e}")
            self.log("将使用演示模式进行跟踪")
            self.tracker = None
            self.model = None
    
    def select_video(self):
        """选择视频文件"""
        filetypes = (
            ('视频文件', '*.mp4 *.avi *.mov *.mkv'),
            ('MP4文件', '*.mp4'),
            ('所有文件', '*.*')
        )
        
        filename = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=filetypes,
            initialdir=os.getcwd()
        )
        
        if filename:
            self.video_path = filename
            self.video_path_var.set(filename)
            self.bbox = None
            self.bbox_var.set("未选择")
            self.log(f"已选择视频: {os.path.basename(filename)}")
    
    def select_target(self):
        """选择跟踪目标"""
        if not self.video_path:
            messagebox.showerror("错误", "请先选择视频文件")
            return
        
        try:
            self.log("正在打开目标选择窗口...")
            selector = VideoSelector(self.video_path)
            bbox = selector.select_target()
            
            if bbox:
                self.bbox = bbox
                self.bbox_var.set(f"[{bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}]")
                self.log(f"已选择目标: x={bbox[0]}, y={bbox[1]}, w={bbox[2]}, h={bbox[3]}")
            else:
                self.log("未选择目标")
                
        except Exception as e:
            self.log(f"目标选择失败: {e}")
            messagebox.showerror("错误", f"目标选择失败: {e}")
    
    def start_tracking(self):
        """开始跟踪"""
        if not self.video_path:
            messagebox.showerror("错误", "请先选择视频文件")
            return
        
        if not self.bbox:
            messagebox.showerror("错误", "请先选择跟踪目标")
            return
        
        if self.is_tracking:
            messagebox.showwarning("警告", "跟踪正在进行中")
            return
        
        # 启动跟踪线程
        self.tracking_thread = threading.Thread(target=self._track_video)
        self.tracking_thread.daemon = True
        self.is_tracking = True
        
        # 更新UI状态
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.progress_bar.start()
        self.progress_var.set("跟踪进行中...")
        
        self.tracking_thread.start()
    
    def stop_tracking(self):
        """停止跟踪"""
        self.is_tracking = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.progress_bar.stop()
        self.progress_var.set("跟踪已停止")
        self.log("用户停止跟踪")
    
    def _track_video(self):
        """执行视频跟踪（在后台线程中运行）"""
        try:
            self.log("开始视频跟踪...")
            
            # 打开视频
            cap = cv2.VideoCapture(self.video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            self.log(f"视频信息: {width}x{height}, {fps:.1f}fps, {total_frames}帧")
            
            # 准备输出视频
            output_dir = os.path.dirname(self.video_path)
            output_filename = os.path.splitext(os.path.basename(self.video_path))[0] + "_tracked.mp4"
            self.output_path = os.path.join(output_dir, output_filename)
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(self.output_path, fourcc, fps, (width, height))
            
            # 读取第一帧进行初始化
            ret, first_frame = cap.read()
            if not ret:
                self.log("错误: 无法读取视频第一帧")
                return
            
            # 初始化跟踪
            frame_idx = 0
            bbox = self.bbox.copy()
            state = None
            
            # 如果有真实模型，进行真实跟踪初始化
            if self.model is not None and self.tracker is not None:
                try:
                    self.log("使用LightTrack真实模型进行跟踪")
                    
                    # 转换边界框格式: [x, y, w, h] -> [cx, cy, w, h]
                    target_pos = np.array([bbox[0] + bbox[2]/2, bbox[1] + bbox[3]/2])
                    target_sz = np.array([bbox[2], bbox[3]])
                    
                    # 初始化跟踪器
                    state = self.tracker.init(first_frame, target_pos, target_sz, self.model)
                    self.log("LightTrack跟踪器初始化成功")
                    
                except Exception as e:
                    self.log(f"LightTrack初始化失败，使用演示模式: {e}")
                    self.model = None
                    state = None
            else:
                self.log("使用演示模式进行跟踪（模拟LightTrack效果）")
            
            # 重新开始读取视频
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            while self.is_tracking and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 真实跟踪 vs 演示跟踪
                if state is not None and self.model is not None:
                    try:
                        # 使用真实的LightTrack进行跟踪
                        state = self.tracker.track(state, frame)
                        
                        # 获取跟踪结果
                        target_pos = state['target_pos']
                        target_sz = state['target_sz']
                        
                        # 提取坐标值
                        center_x = self._safe_extract_coordinate(target_pos, 0)
                        center_y = self._safe_extract_coordinate(target_pos, 1)
                        size_w = self._safe_extract_coordinate(target_sz, 0)
                        size_h = self._safe_extract_coordinate(target_sz, 1)
                        
                        # 验证跟踪结果是否合理
                        # 检查中心坐标是否能产生合理的边界框（不会被裁剪到左上角）
                        # 使用稍微更严格的边界以避免边界情况
                        min_center_x = size_w / 2 + 1  # 留出1像素的缓冲区
                        min_center_y = size_h / 2 + 1  # 留出1像素的缓冲区
                        max_center_x = width - size_w / 2 - 1   # 留出1像素的缓冲区
                        max_center_y = height - size_h / 2 - 1  # 留出1像素的缓冲区
                        
                        if (center_x < min_center_x or center_y < min_center_y or 
                            size_w <= 0 or size_h <= 0 or
                            center_x > max_center_x or center_y > max_center_y or
                            size_w > width or size_h > height):
                            
                            self.log(f"检测到无效的跟踪结果: center=({center_x:.1f}, {center_y:.1f}), size=({size_w:.1f}, {size_h:.1f})")
                            self.log(f"有效范围: center_x=[{min_center_x:.1f}, {max_center_x:.1f}], center_y=[{min_center_y:.1f}, {max_center_y:.1f}]")
                            raise ValueError("跟踪结果无效")
                        
                        # 转换为边界框格式 [cx, cy, w, h] -> [x, y, w, h]
                        new_bbox = [
                            int(center_x - size_w/2),
                            int(center_y - size_h/2),
                            int(size_w),
                            int(size_h)
                        ]
                        
                        # 确保边界框在视频范围内
                        new_bbox[0] = max(0, min(width - new_bbox[2], new_bbox[0]))
                        new_bbox[1] = max(0, min(height - new_bbox[3], new_bbox[1]))
                        
                        bbox = new_bbox
                        
                    except Exception as e:
                        self.log(f"跟踪出错，回退到演示模式: {e}")
                        self.model = None
                        state = None
                        
                        # 保持当前bbox位置，不要应用随机漂移（避免跳动）
                        # 只有在后续帧中才开始演示跟踪
                        if frame_idx > 1:
                            drift_x = np.random.normal(0, 2)
                            drift_y = np.random.normal(0, 2)
                            
                            # 确保bbox元素都是标量值
                            bbox[0] = max(0, min(width - int(self._safe_extract_scalar(bbox[2])), int(self._safe_extract_scalar(bbox[0])) + drift_x))
                            bbox[1] = max(0, min(height - int(self._safe_extract_scalar(bbox[3])), int(self._safe_extract_scalar(bbox[1])) + drift_y))
                else:
                    # 演示跟踪：简单的随机漂移
                    if frame_idx > 0:
                        drift_x = np.random.normal(0, 2)
                        drift_y = np.random.normal(0, 2)
                        
                        # 确保bbox元素都是标量值
                        bbox[0] = max(0, min(width - int(self._safe_extract_scalar(bbox[2])), int(self._safe_extract_scalar(bbox[0])) + drift_x))
                        bbox[1] = max(0, min(height - int(self._safe_extract_scalar(bbox[3])), int(self._safe_extract_scalar(bbox[1])) + drift_y))
                
                # 绘制跟踪框
                x, y, w, h = [int(v) for v in bbox]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # 显示帧信息和跟踪状态
                status_text = "LightTrack" if (self.model is not None) else "Demo Mode"
                cv2.putText(frame, f'{status_text} - Frame: {frame_idx + 1}', (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # 写入输出视频
                out.write(frame)
                
                # 更新进度 - 确保线程安全
                frame_idx += 1
                if frame_idx % 30 == 0:  # 每30帧更新一次日志
                    progress = (frame_idx / total_frames) * 100
                    # 使用线程安全的方式更新UI
                    self.log(f"跟踪进度: {progress:.1f}% ({frame_idx}/{total_frames})")
                
                # 控制处理速度
                time.sleep(0.01)
            
            cap.release()
            out.release()
            
            if self.is_tracking:
                self.log(f"跟踪完成! 结果已保存至: {self.output_path}")
                # 使用线程安全的方式更新UI
                try:
                    self.root.after(0, self._tracking_finished)
                except Exception as e:
                    self.log(f"UI更新失败: {e}")
            else:
                self.log("跟踪被用户中止")
                
        except Exception as e:
            self.log(f"跟踪过程出错: {e}")
            # 使用线程安全的方式显示错误
            try:
                self.root.after(0, lambda: self._tracking_error(str(e)))
            except Exception as ui_error:
                self.log(f"UI错误处理失败: {ui_error}")
    
    def _tracking_finished(self):
        """跟踪完成后的UI更新"""
        self.is_tracking = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.progress_bar.stop()
        self.progress_var.set("跟踪完成")
        messagebox.showinfo("完成", f"视频跟踪完成!\n结果已保存至:\n{self.output_path}")
    
    def _tracking_error(self, error_msg):
        """跟踪出错后的UI更新"""
        self.is_tracking = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.progress_bar.stop()
        self.progress_var.set("跟踪出错")
        messagebox.showerror("错误", f"跟踪过程出错:\n{error_msg}")
    
    def save_result(self):
        """保存跟踪结果"""
        if not hasattr(self, 'output_path') or not self.output_path:
            messagebox.showwarning("警告", "没有可保存的跟踪结果")
            return
        
        if not os.path.exists(self.output_path):
            messagebox.showwarning("警告", "跟踪结果文件不存在")
            return
        
        save_path = filedialog.asksaveasfilename(
            title="保存跟踪结果",
            defaultextension=".mp4",
            filetypes=[("MP4文件", "*.mp4"), ("所有文件", "*.*")],
            initialname="tracking_result.mp4"
        )
        
        if save_path:
            try:
                import shutil
                shutil.copy2(self.output_path, save_path)
                self.log(f"跟踪结果已保存至: {save_path}")
                messagebox.showinfo("成功", f"跟踪结果已保存至:\n{save_path}")
            except Exception as e:
                self.log(f"保存失败: {e}")
                messagebox.showerror("错误", f"保存失败: {e}")


def main():
    """主函数"""
    # 创建主窗口
    root = tk.Tk()
    
    # 设置图标（如果存在）
    try:
        # root.iconbitmap('icon.ico')  # 可以添加图标文件
        pass
    except:
        pass
    
    # 创建应用程序
    app = LightTrackGUI(root)
    
    # 运行应用程序
    root.mainloop()


if __name__ == "__main__":
    main()