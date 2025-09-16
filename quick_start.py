#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LightTrack 使用说明和快速开始脚本
"""

import os
import sys

def print_banner():
    """打印欢迎横幅"""
    print("=" * 60)
    print("    LightTrack: 轻量级目标跟踪神经网络")
    print("    Finding Lightweight Neural Networks for Object Tracking")
    print("=" * 60)
    print()

def check_dependencies():
    """检查依赖是否安装"""
    print("🔍 检查依赖...")
    
    required_packages = ['cv2', 'numpy', 'torch', 'torchvision', 'PIL', 'tkinter']
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'cv2':
                import cv2
            elif package == 'tkinter':
                import tkinter
            else:
                __import__(package)
            print(f"  ✅ {package} - 已安装")
        except ImportError:
            print(f"  ❌ {package} - 未安装")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  缺少以下依赖: {', '.join(missing_packages)}")
        print("请运行以下命令安装:")
        if 'tkinter' in missing_packages:
            print("  sudo apt-get install python3-tk")
        print("  pip install opencv-python numpy torch torchvision pillow easydict pyyaml")
        return False
    else:
        print("  ✅ 所有依赖已安装")
        return True

def show_usage():
    """显示使用说明"""
    print("\n📚 使用说明:")
    print()
    
    print("1️⃣  创建测试视频 (可选):")
    print("   python create_sample_video.py")
    print("   # 这将创建一个包含移动目标的示例视频")
    print()
    
    print("2️⃣  使用GUI界面 (推荐):")
    print("   python gui_tracker.py")
    print("   # 图形界面，支持选择视频、框选目标、自动跟踪")
    print()
    
    print("3️⃣  使用命令行:")
    print("   # 交互式选择目标")
    print("   python mp4_tracking_demo.py --video your_video.mp4 --display")
    print()
    print("   # 指定边界框")
    print("   python mp4_tracking_demo.py --video your_video.mp4 --bbox x,y,w,h --display")
    print()
    
    print("4️⃣  项目文档:")
    print("   README.md - 英文文档")
    print("   README_CN.md - 中文详细文档")
    print()

def show_project_structure():
    """显示项目结构"""
    print("📁 项目结构:")
    print()
    print("LightTrack/")
    print("├── README.md              # 英文文档")
    print("├── README_CN.md           # 中文详细文档")
    print("├── gui_tracker.py         # GUI跟踪应用 [新增]")
    print("├── mp4_tracking_demo.py   # 命令行跟踪演示 [新增]")
    print("├── create_sample_video.py # 测试视频生成器 [新增]")
    print("├── quick_start.py         # 快速开始脚本 [新增]")
    print("├── lib/                   # 核心库")
    print("│   ├── models/           # 模型定义")
    print("│   ├── tracker/          # 跟踪算法")
    print("│   └── utils/            # 工具函数")
    print("├── tracking/             # 跟踪脚本")
    print("├── experiments/          # 实验配置")
    print("├── dataset/              # 数据集")
    print("└── snapshot/             # 模型权重")
    print()

def show_features():
    """显示新增功能"""
    print("🎯 新增功能:")
    print()
    print("✨ GUI图形界面:")
    print("   • 选择MP4视频文件")
    print("   • 在第一帧中拖拽框选目标")
    print("   • 实时显示跟踪进度")
    print("   • 自动保存跟踪结果")
    print()
    
    print("✨ 命令行工具:")
    print("   • 支持MP4等常见视频格式")
    print("   • 交互式目标选择")
    print("   • 实时跟踪显示")
    print("   • 自定义输出路径")
    print()
    
    print("✨ 完整中文文档:")
    print("   • 详细的安装说明")
    print("   • 使用教程和示例")
    print("   • 性能对比和优化建议")
    print("   • 常见问题解答")
    print()

def main():
    """主函数"""
    print_banner()
    
    # 检查依赖
    deps_ok = check_dependencies()
    print()
    
    # 显示功能特点
    show_features()
    
    # 显示项目结构
    show_project_structure()
    
    # 显示使用说明
    show_usage()
    
    # 提供快速开始选项
    if deps_ok:
        print("🚀 快速开始:")
        print()
        choice = input("选择操作 (1:创建测试视频, 2:启动GUI, 3:查看帮助, q:退出): ").strip().lower()
        
        if choice == '1':
            print("\n正在创建测试视频...")
            try:
                os.system("python create_sample_video.py")
            except:
                print("创建失败，请手动运行: python create_sample_video.py")
        
        elif choice == '2':
            print("\n正在启动GUI应用...")
            try:
                os.system("python gui_tracker.py")
            except:
                print("启动失败，请手动运行: python gui_tracker.py")
        
        elif choice == '3':
            print("\n请查看 README_CN.md 获取详细文档")
            
        elif choice == 'q':
            print("再见!")
        
        else:
            print("无效选择")
    
    else:
        print("❌ 请先安装缺少的依赖，然后重新运行此脚本")

if __name__ == "__main__":
    main()