# LightTrack: 轻量级目标跟踪神经网络

<div align="center">
  <img src="Archs.gif" width="800px" />
</div>

## 项目简介

LightTrack是一个基于神经架构搜索(NAS)的轻量级目标跟踪系统。该项目通过自动化的架构搜索技术，设计出更加轻量且高效的目标跟踪器。

### 主要特点

- 🚀 **高效轻量**：相比传统SOTA跟踪器（如SiamRPN++和Ocean），使用更少的模型参数和计算量
- 📱 **移动端优化**：在Snapdragon 845 Adreno GPU上运行速度比Ocean快12倍
- 🎯 **精准跟踪**：在保持轻量化的同时实现优秀的跟踪性能
- 🔧 **易于部署**：缩小学术模型与工业部署之间的差距

<div align="center">
  <img src="LightTrack_Fig1.PNG" width="500px" />
</div>

## 技术架构

### 核心组件

1. **超网络设计** - 使用神经架构搜索构建的高效网络架构
2. **轻量级跟踪器** - 基于Siamese网络的目标跟踪算法
3. **多尺度搜索** - 支持不同尺度的目标检测和跟踪
4. **实时处理** - 优化的推理速度，适合实时应用

### 网络结构

- **骨干网络**: EfficientNet-based超网络
- **特征提取**: 轻量级卷积特征提取器
- **相似度计算**: Siamese网络架构
- **边界框回归**: 精确的目标定位

## 环境配置

### 系统要求

- Python 3.6+
- CUDA 10.0+
- PyTorch 1.1.0+
- OpenCV 4.0+

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/git-xiaomy/LightTrack.git
cd LightTrack
```

2. **创建虚拟环境**
```bash
conda create -n lighttrack python=3.6
conda activate lighttrack
```

3. **安装依赖**
```bash
bash install.sh
```

### 手动安装依赖

如果自动安装脚本失败，可以手动安装以下依赖：

```bash
# 基础依赖
pip install torch==1.1.0 torchvision==0.3.0
pip install opencv-python
pip install numpy pandas scipy
pip install pillow scikit-image
pip install easydict pyyaml

# 专用依赖
pip install lmdb jpeg4py
pip install cython==0.29.21
pip install shapely numba
pip install yacs timm==0.1.20
pip install tensorboardX colorama

# 计算FLOPs工具
pip install --upgrade git+https://github.com/Lyken17/pytorch-OpCounter.git
```

## 数据准备

### 跟踪数据集

支持的数据集格式：
- VOT2019
- OTB2015
- LaSOT
- GOT-10K

### 数据目录结构

```
LightTrack/
├── dataset/
│   ├── VOT2019.json
│   ├── VOT2019/
│   │   ├── agility/
│   │   ├── ants1/
│   │   └── ...
│   └── list.txt
├── snapshot/          # 预训练模型
├── experiments/       # 配置文件
└── tracking/         # 跟踪脚本
```

## 模型使用

### 预训练模型

项目提供预训练的超网络权重：
- ImageNet分类预训练模型
- 目标跟踪预训练模型

下载链接：[Google Drive](https://drive.google.com/drive/folders/1HXhdJO3yhQYw3O7nGUOXHu2S20Bs8CfI)

### 基本使用方法

#### 1. 测试单个视频

```bash
cd tracking
python test_lighttrack.py \
    --arch LightTrackM_Subnet \
    --resume ../snapshot/LightTrack_M.pth \
    --video your_video_name
```

#### 2. 批量测试

```bash
bash reproduce_vot2019.sh
```

#### 3. 性能评估

```bash
# 计算FLOPs和参数量
python FLOPs_Params.py

# 测试运行速度
python Speed.py
```

## MP4视频跟踪教程

### 准备工作

1. **准备MP4视频文件**
2. **转换视频格式**（如果需要）
3. **提取视频帧**

### 详细步骤

#### 步骤1：视频预处理

```python
import cv2
import os

def extract_frames(video_path, output_dir):
    """从MP4视频提取帧"""
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_path = os.path.join(output_dir, f"{frame_count:06d}.jpg")
        cv2.imwrite(frame_path, frame)
        frame_count += 1
    
    cap.release()
    return frame_count

# 使用示例
video_path = "your_video.mp4"
output_dir = "video_frames"
total_frames = extract_frames(video_path, output_dir)
```

#### 步骤2：初始化跟踪器

```python
import sys
sys.path.append('.')
from tracking.test_lighttrack import *

# 配置参数
args = type('Args', (), {
    'arch': 'LightTrackM_Subnet',
    'resume': 'snapshot/LightTrack_M.pth',
    'dataset': 'VOT2019',
    'stride': 16
})()

# 初始化跟踪器
info = edict()
info.arch = args.arch
info.dataset = args.dataset
info.stride = args.stride

tracker = Lighttrack(info)
```

#### 步骤3：目标初始化和跟踪

```python
def track_video(tracker, model, frames_dir, init_bbox):
    """
    跟踪视频中的目标
    
    Args:
        tracker: LightTrack跟踪器
        model: 加载的模型
        frames_dir: 视频帧目录
        init_bbox: 初始边界框 [x, y, w, h]
    """
    frame_files = sorted(os.listdir(frames_dir))
    results = []
    
    for i, frame_file in enumerate(frame_files):
        frame_path = os.path.join(frames_dir, frame_file)
        frame = cv2.imread(frame_path)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        if i == 0:  # 初始化
            cx = init_bbox[0] + init_bbox[2] / 2
            cy = init_bbox[1] + init_bbox[3] / 2
            target_pos = np.array([cx, cy])
            target_sz = np.array([init_bbox[2], init_bbox[3]])
            
            state = tracker.init(rgb_frame, target_pos, target_sz, model)
            results.append(init_bbox)
        else:  # 跟踪
            state = tracker.track(state, rgb_frame)
            
            # 转换结果格式
            cx, cy = state['target_pos']
            w, h = state['target_sz']
            bbox = [cx - w/2, cy - h/2, w, h]
            results.append(bbox)
    
    return results
```

### 可视化结果

```python
def visualize_tracking(frames_dir, results, output_video):
    """可视化跟踪结果"""
    frame_files = sorted(os.listdir(frames_dir))
    
    # 获取视频参数
    first_frame = cv2.imread(os.path.join(frames_dir, frame_files[0]))
    height, width = first_frame.shape[:2]
    
    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video, fourcc, 30.0, (width, height))
    
    for i, (frame_file, bbox) in enumerate(zip(frame_files, results)):
        frame_path = os.path.join(frames_dir, frame_file)
        frame = cv2.imread(frame_path)
        
        # 绘制边界框
        x, y, w, h = [int(v) for v in bbox]
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        # 添加帧号
        cv2.putText(frame, f'Frame: {i+1}', (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        out.write(frame)
    
    out.release()
    print(f"跟踪结果已保存到: {output_video}")
```

## GUI界面应用

项目提供了一个图形用户界面，方便用户选择视频文件并进行目标跟踪。

### 功能特点

- 📁 **文件选择**：支持选择MP4、AVI等常见视频格式
- 🎯 **目标框选**：在第一帧中手动框选要跟踪的目标
- ▶️ **实时跟踪**：显示跟踪过程和结果
- 💾 **结果保存**：保存跟踪结果视频

### 使用方法

```bash
python gui_tracker.py
```

界面操作步骤：
1. 点击"选择视频"按钮选择MP4文件
2. 在弹出的第一帧图像中拖拽鼠标框选目标
3. 点击"开始跟踪"按钮开始自动跟踪
4. 跟踪完成后可选择保存结果

## 性能指标

### 模型对比

| 模型 | 参数量 | FLOPs | VOT2019 EAO | 速度(fps) |
|------|--------|-------|-------------|-----------|
| SiamRPN++ | 53.8M | 15.3G | 0.285 | 35 |
| Ocean | 32.7M | 17.6G | 0.289 | 25 |
| **LightTrack-Mobile** | **2.5M** | **0.46G** | **0.324** | **300** |

### 移动端性能

在Snapdragon 845 Adreno GPU上的测试结果：
- **速度提升**: 比Ocean快12倍
- **参数减少**: 比Ocean少13倍参数
- **计算量减少**: 比Ocean少38倍FLOPs

## 常见问题解答

### Q1: 如何处理不同分辨率的视频？

A1: LightTrack会自动适配不同分辨率。对于高分辨率视频，建议先缩放到合适尺寸以提高处理速度。

### Q2: 跟踪效果不理想怎么办？

A2: 可以尝试以下方法：
- 调整初始边界框的精度
- 选择更清晰的初始帧
- 调整跟踪参数（在配置文件中）

### Q3: 如何在CPU上运行？

A3: 修改代码中的`.cuda()`调用，改为`.cpu()`即可在CPU上运行。

### Q4: 支持多目标跟踪吗？

A4: 当前版本主要支持单目标跟踪。多目标跟踪需要额外的实现。

## 项目结构详解

```
LightTrack/
├── lib/                    # 核心库
│   ├── models/            # 模型定义
│   ├── tracker/           # 跟踪算法
│   ├── utils/             # 工具函数
│   └── eval_toolkit/      # 评估工具
├── tracking/              # 跟踪脚本
│   ├── test_lighttrack.py # 测试脚本
│   ├── Speed.py           # 速度测试
│   └── FLOPs_Params.py    # 性能测试
├── experiments/           # 实验配置
├── dataset/              # 数据集
├── snapshot/             # 模型权重
└── gui_tracker.py        # GUI应用（新增）
```

## 论文引用

如果您在研究中使用了LightTrack，请引用以下论文：

```bibtex
@article{yan2021lighttrack,
  title={LightTrack: Finding Lightweight Neural Networks for Object Tracking via One-Shot Architecture Search},
  author={Yan, Bin and Peng, Houwen and Wu, Kan and Wang, Dong and Fu, Jianlong and Lu, Huchuan},
  journal={arXiv preprint arXiv:2104.14545},
  year={2021}
}
```

## 许可证

本项目基于MIT许可证开源。详见 [LICENSE](LICENSE) 文件。

## 贡献指南

欢迎提交Issue和Pull Request来改进项目。在提交代码前请确保：

1. 代码符合项目风格
2. 添加必要的注释
3. 通过所有测试用例

## 联系方式

- 项目维护者：houwen.peng@microsoft.com
- 问题反馈：通过GitHub Issues

---

**注意**：本项目仅用于学术研究。商业使用请联系项目作者获得授权。