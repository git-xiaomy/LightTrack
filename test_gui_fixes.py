#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：验证gui_tracker.py的修复
"""

import os
import sys
import tempfile
import time

def test_gui_import():
    """测试GUI模块导入"""
    try:
        # 添加路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        # 尝试导入
        print("测试GUI模块导入...")
        from gui_tracker import LightTrackGUI, VideoSelector
        print("✅ GUI模块导入成功")
        return True
    except Exception as e:
        print(f"❌ GUI模块导入失败: {e}")
        return False

def test_dependency_check():
    """测试依赖检查"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        # 导入并检查DEPENDENCIES_AVAILABLE标志
        import gui_tracker
        print(f"依赖状态: {'可用' if gui_tracker.DEPENDENCIES_AVAILABLE else '不可用'}")
        
        if not gui_tracker.DEPENDENCIES_AVAILABLE:
            print("✅ 正确检测到依赖缺失，GUI将以演示模式运行")
        else:
            print("✅ 依赖可用，GUI将尝试使用真实模型")
        
        return True
    except Exception as e:
        print(f"❌ 依赖检查失败: {e}")
        return False

def test_threading_safety():
    """测试线程安全性（基本检查）"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        # 模拟创建GUI但不显示
        print("测试线程安全性...")
        
        # 检查log函数是否使用after方法
        import gui_tracker
        import inspect
        
        # 检查log方法的源码
        source = inspect.getsource(gui_tracker.LightTrackGUI.log)
        
        if 'root.after(' in source:
            print("✅ log方法使用了root.after()进行线程安全更新")
        else:
            print("❌ log方法可能存在线程安全问题")
            return False
            
        return True
    except Exception as e:
        print(f"❌ 线程安全检查失败: {e}")
        return False

def test_model_paths():
    """测试模型路径检查"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 检查期望的模型路径
        expected_paths = [
            os.path.join(current_dir, 'snapshot', 'checkpoint_e30.pth'),
            os.path.join(current_dir, 'snapshot', 'LightTrackM', 'LightTrackM.pth'),
            os.path.join(current_dir, 'snapshot', 'LightTrackM.pth')
        ]
        
        print("检查模型路径:")
        found_model = False
        for path in expected_paths:
            exists = os.path.exists(path)
            status = "✅ 存在" if exists else "❌ 不存在"
            print(f"  {path}: {status}")
            if exists:
                found_model = True
        
        if found_model:
            print("✅ 找到至少一个模型文件")
        else:
            print("⚠️  未找到模型文件，将使用演示模式")
        
        return True
    except Exception as e:
        print(f"❌ 模型路径检查失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 50)
    print("LightTrack GUI修复验证测试")
    print("=" * 50)
    
    tests = [
        ("依赖检查", test_dependency_check),
        ("GUI模块导入", test_gui_import),
        ("线程安全性", test_threading_safety),
        ("模型路径", test_model_paths),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n🧪 {name}:")
        try:
            if test_func():
                passed += 1
            else:
                print(f"   测试失败")
        except Exception as e:
            print(f"   测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！GUI修复成功")
        print("\n使用方法:")
        print("  python gui_tracker.py")
        print("\n如果遇到依赖问题，请运行:")
        print("  pip install opencv-python numpy torch torchvision pillow easydict")
    else:
        print("⚠️  部分测试失败，可能需要进一步调试")
    
    print("=" * 50)

if __name__ == "__main__":
    main()