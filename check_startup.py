#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LightTrack GUI 启动检查器
帮助用户诊断和解决运行问题
"""

import os
import sys

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 6:
        print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python版本过低: {version.major}.{version.minor}.{version.micro}")
        print("   需要Python 3.6或更高版本")
        return False

def check_dependencies():
    """检查必要依赖"""
    dependencies = {
        'cv2': 'opencv-python',
        'numpy': 'numpy', 
        'torch': 'torch',
        'torchvision': 'torchvision',
        'PIL': 'pillow',
        'tkinter': 'tkinter (系统包)',
        'easydict': 'easydict'
    }
    
    missing = []
    available = []
    
    for module, package in dependencies.items():
        try:
            if module == 'tkinter':
                import tkinter
            elif module == 'cv2':
                import cv2
            elif module == 'PIL':
                from PIL import Image
            else:
                __import__(module)
            
            available.append((module, package))
            print(f"✅ {module} - 已安装")
        except ImportError:
            missing.append((module, package))
            print(f"❌ {module} - 未安装")
    
    return available, missing

def check_torch_six():
    """检查torch._six问题"""
    try:
        import torch
        try:
            import torch._six
            print("✅ torch._six - 可用")
            return True
        except ImportError:
            print("⚠️  torch._six - 不可用（可能的兼容性问题）")
            return False
    except ImportError:
        print("❌ torch - 未安装")
        return False

def check_model_files():
    """检查模型文件"""
    model_paths = [
        "snapshot/checkpoint_e30.pth",
        "snapshot/LightTrackM/LightTrackM.pth", 
        "snapshot/LightTrackM.pth"
    ]
    
    found = []
    missing = []
    
    for path in model_paths:
        if os.path.exists(path):
            size = os.path.getsize(path) / (1024*1024)  # MB
            found.append((path, f"{size:.1f}MB"))
            print(f"✅ {path} ({size:.1f}MB)")
        else:
            missing.append(path)
            print(f"❌ {path} - 不存在")
    
    return found, missing

def check_gui_file():
    """检查GUI文件"""
    if os.path.exists("gui_tracker.py"):
        print("✅ gui_tracker.py - 存在")
        return True
    else:
        print("❌ gui_tracker.py - 不存在")
        return False

def provide_solutions(missing_deps, missing_models, torch_six_ok, gui_exists):
    """提供解决方案"""
    print("\n" + "=" * 50)
    print("💡 解决方案:")
    print("=" * 50)
    
    if missing_deps:
        print("\n📦 安装缺失依赖:")
        pip_packages = []
        system_packages = []
        
        for module, package in missing_deps:
            if 'tkinter' in package:
                system_packages.append("python3-tk")
            else:
                pip_packages.append(package)
        
        if pip_packages:
            print(f"   pip install {' '.join(pip_packages)}")
        
        if system_packages:
            print(f"   sudo apt-get install {' '.join(system_packages)}  # Ubuntu/Debian")
            print(f"   yum install {' '.join(system_packages)}  # CentOS/RHEL")
    
    if not torch_six_ok:
        print("\n🔧 修复torch._six问题:")
        print("   1. 尝试更新PyTorch:")
        print("      pip install --upgrade torch torchvision")
        print("   2. 或者安装six包:")
        print("      pip install six")
        print("   3. 或者运行修复脚本:")
        print("      python fix_torch_six.py")
    
    if missing_models:
        print("\n📁 获取模型文件:")
        print("   将预训练模型放置到以下位置之一:")
        for path in missing_models:
            print(f"   - {path}")
        print("   \n   模型下载地址:")
        print("   https://drive.google.com/drive/folders/1HXhdJO3yhQYw3O7nGUOXHu2S20Bs8CfI")
    
    if not gui_exists:
        print("\n📄 GUI文件缺失:")
        print("   请确保gui_tracker.py文件在当前目录")

def main():
    """主检查函数"""
    print("=" * 60)
    print("🔍 LightTrack GUI 启动检查器")
    print("=" * 60)
    
    print("\n1️⃣  检查Python版本...")
    python_ok = check_python_version()
    
    print("\n2️⃣  检查依赖包...")
    available_deps, missing_deps = check_dependencies()
    
    print("\n3️⃣  检查torch._six兼容性...")
    torch_six_ok = check_torch_six()
    
    print("\n4️⃣  检查模型文件...")
    found_models, missing_models = check_model_files()
    
    print("\n5️⃣  检查GUI文件...")
    gui_exists = check_gui_file()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 检查结果:")
    print("=" * 60)
    
    total_score = 0
    max_score = 5
    
    if python_ok:
        total_score += 1
    if not missing_deps:
        total_score += 1 
    if torch_six_ok:
        total_score += 1
    if found_models:
        total_score += 1
    if gui_exists:
        total_score += 1
    
    print(f"综合评分: {total_score}/{max_score}")
    
    if total_score >= 4:
        print("🎉 恭喜！大部分检查通过，GUI应该可以正常运行")
        if missing_models:
            print("   注意：没有模型文件时将使用演示模式")
        print("\n🚀 启动命令:")
        print("   python gui_tracker.py")
    elif total_score >= 2:
        print("⚠️  存在一些问题，需要解决后才能正常运行")
        provide_solutions(missing_deps, missing_models, torch_six_ok, gui_exists)
    else:
        print("❌ 存在严重问题，需要先解决基础依赖")
        provide_solutions(missing_deps, missing_models, torch_six_ok, gui_exists)
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()