# LightTrack模型权重目录

请将预训练模型文件放置到此目录：

## 支持的模型文件：

1. **checkpoint_e30.pth** - 推荐使用
   - 从原始项目下载的标准模型文件
   - 请将下载的模型文件重命名为此名称

2. **LightTrackM/LightTrackM.pth** - 备用路径
   - 原始LightTrackM模型文件

3. **LightTrackM.pth** - 备用路径
   - 直接放置在snapshot目录的LightTrackM模型文件

## 模型下载：

如果您没有模型文件，可以从以下位置获取：
- 查看原始项目的README文件获取下载链接
- 或者在没有模型的情况下使用演示模式

## 使用说明：

1. 下载模型文件
2. 将其重命名为 `checkpoint_e30.pth` 
3. 放置到此目录
4. 运行 `python gui_tracker.py`

GUI会自动检测并加载可用的模型文件。