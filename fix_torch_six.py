#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
torch._six 兼容性修复
解决 "No module named 'torch._six'" 错误
"""

def fix_torch_six():
    """修复torch._six兼容性问题"""
    try:
        import torch
        print(f"PyTorch version: {torch.__version__}")
        
        # 检查torch._six是否存在
        try:
            import torch._six
            print("✅ torch._six 可用")
            return True
        except ImportError:
            print("⚠️  torch._six 不可用，尝试修复...")
            
            # 创建torch._six模块兼容性
            import sys
            if 'torch._six' not in sys.modules:
                try:
                    # 创建一个简单的六兼容模块
                    import types
                    six_module = types.ModuleType('torch._six')
                    
                    # 添加常用的six函数
                    import six
                    for attr in ['PY2', 'PY3', 'string_types', 'integer_types', 'class_types', 'text_type', 'binary_type']:
                        if hasattr(six, attr):
                            setattr(six_module, attr, getattr(six, attr))
                    
                    sys.modules['torch._six'] = six_module
                    print("✅ torch._six 兼容性模块已创建")
                    return True
                    
                except ImportError:
                    print("❌ 无法创建torch._six兼容模块，six包不可用")
                    print("请运行: pip install six")
                    return False
            else:
                print("✅ torch._six 已存在")
                return True
                
    except ImportError:
        print("❌ PyTorch 未安装")
        print("请运行: pip install torch torchvision")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("torch._six 兼容性检查和修复")
    print("=" * 50)
    
    if fix_torch_six():
        print("\n🎉 torch._six 问题已解决!")
        print("现在可以尝试运行: python gui_tracker.py")
    else:
        print("\n❌ 无法解决torch._six问题")
        print("建议:")
        print("1. 更新PyTorch: pip install --upgrade torch torchvision")
        print("2. 安装six: pip install six")
        print("3. 重新安装PyTorch: pip uninstall torch && pip install torch")
    
    print("=" * 50)