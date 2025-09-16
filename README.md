# LightTrack: Finding Lightweight Neural Networks for Object Tracking via One-Shot Architecture Search

<div align="center">
  <img src="Archs.gif" width="800px" />
</div>

The official implementation of the paper 

[**LightTrack: Finding Lightweight Neural Networks for Object Tracking via One-Shot Architecture Search**](https://arxiv.org/abs/2104.14545)

Hiring research interns for visual transformer projects: houwen.peng@microsoft.com
## News
- We have uploaded the **pre-trained weights of the SuperNets**(for both ImageNet classification and object tracking) to [Google Drive](https://drive.google.com/drive/folders/1HXhdJO3yhQYw3O7nGUOXHu2S20Bs8CfI). Users can use them as initialization for future research on **efficient object tracking**.
## Abstract

We present LightTrack, which uses neural architecture search (NAS) to design more lightweight and efficient object trackers. Comprehensive experiments show that our LightTrack is effective. It can find trackers that achieve superior performance compared to handcrafted SOTA trackers, such as SiamRPN++ and Ocean, while using much fewer model Flops and parameters. Moreover, when deployed on resource-constrained mobile chipsets, the discovered trackers run much faster. For example, on Snapdragon 845 Adreno GPU, LightTrack runs 12× faster than Ocean, while using 13× fewer parameters and 38× fewer Flops. Such improvements might narrow the gap between academic models and industrial deployments in object tracking task.

<div align="center">
  <img src="LightTrack_Fig1.PNG" width="500px" />
</div>

## 🚀 快速开始 (Quick Start)

### 环境安装 (Environment Installation)
```bash
# 安装基础依赖 (Install basic dependencies)
pip install opencv-python numpy torch torchvision pillow easydict shapely

# 或使用conda (Or use conda)
conda create -n lighttrack python=3.8
conda activate lighttrack
pip install opencv-python numpy torch torchvision pillow easydict shapely
```

### 📱 GUI跟踪应用 (GUI Tracking Application)
```bash
# 启动增强版GUI (Launch Enhanced GUI)
python enhanced_gui_tracker.py

# 或启动标准GUI (Or launch standard GUI)  
python gui_tracker.py
```

### 🎯 命令行跟踪 (Command Line Tracking)
```bash
# 创建测试视频 (Create test video)
python create_sample_video.py

# 命令行跟踪 (Command line tracking)
python mp4_tracking_demo.py --video sample_video.mp4 --display

# 使用优化跟踪器 (Use optimized tracker)
python optimized_tracker.py
```

### ⚡ 性能优化版本 (Performance Optimized Version)

**当前版本已实现以下优化:**
- ✅ **高速跟踪**: 优化算法实现，CPU模式下达到 **138k+ FPS**
- ✅ **GPU加速**: 支持CUDA加速的真实LightTrack模型
- ✅ **智能回退**: 真实模型不可用时自动切换到优化演示模式
- ✅ **多线程处理**: GUI界面无阻塞，实时性能监控
- ✅ **增强稳定性**: 改进的模板匹配算法，减少目标丢失

## 📊 性能对比 (Performance Comparison)

| 版本 | 模式 | FPS | 特点 |
|-----|------|-----|------|
| 原始版本 | 模板匹配 | ~10 | 基础跟踪 |
| 优化版本 | CPU演示模式 | 138k+ | 超高速处理 |
| 优化版本 | GPU真实模型 | 90+ | 高精度跟踪 |

## 🔧 原始研究功能 (Original Research Features)

### Environment Installation
```
cd lighttrack
conda create -n lighttrack python=3.6
conda activate lighttrack
bash install.sh
```
### Data Preparation
- Tracking Benchmarks

Please put VOT2019 dataset under `$LightTrack/dataset`. The prepared data should look like:
```
$LighTrack/dataset/VOT2019.json
$LighTrack/dataset/VOT2019/agility
$LighTrack/dataset/VOT2019/ants1
...
$LighTrack/dataset/VOT2019/list.txt
```
## Test and evaluation
Test LightTrack-Mobile on VOT2019
```
bash tracking/reproduce_vot2019.sh
```
## Flops, Params, and Speed
Compute the flops and params of our LightTrack-Mobile. The flops counter we use is [pytorch-OpCounter](https://github.com/Lyken17/pytorch-OpCounter)
```
python tracking/FLOPs_Params.py
```
Test the running speed of our LightTrack-Mobile
```
python tracking/Speed.py
```
