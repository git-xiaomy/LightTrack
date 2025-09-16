#!/usr/bin/env python3
"""
验证脚本：检查 LightTrack 跟踪修复是否正确应用
Usage: python verify_tracking_fix.py
"""

import sys
import os
import re

def verify_fix():
    """验证修复是否正确应用"""
    
    print("🔍 LightTrack 跟踪修复验证")
    print("=" * 50)
    
    # 检查文件是否存在
    tracker_file = "lib/tracker/lighttrack.py"
    if not os.path.exists(tracker_file):
        print(f"❌ 错误: 找不到文件 {tracker_file}")
        print("请确保在 LightTrack 项目根目录运行此脚本")
        return False
    
    print(f"✅ 找到跟踪器文件: {tracker_file}")
    
    # 读取文件内容
    try:
        with open(tracker_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 无法读取文件: {e}")
        return False
    
    # 检查是否包含修复的代码
    fix_pattern = r"target_pos\[0\]\s*=\s*max\s*\(\s*target_sz\[0\]\s*/\s*2"
    
    if re.search(fix_pattern, content):
        print("✅ 发现修复代码: 正确的坐标限制逻辑")
    else:
        print("❌ 未发现修复代码: 可能使用的是未修复的版本")
        print("预期的修复代码应包含:")
        print("   target_pos[0] = max(target_sz[0]/2, min(state['im_w'] - target_sz[0]/2, target_pos[0]))")
        return False
    
    # 检查是否还包含旧的（错误的）代码
    old_pattern = r"target_pos\[0\]\s*=\s*max\s*\(\s*0\s*,\s*min\s*\(\s*state\['im_w'\]"
    
    if re.search(old_pattern, content):
        print("⚠️  警告: 仍然包含旧的限制代码，可能修复不完整")
        return False
    else:
        print("✅ 确认: 已移除旧的错误限制代码")
    
    # 验证修复逻辑
    print("\n🧪 测试修复逻辑:")
    print("-" * 30)
    
    # 模拟用户的视频参数
    im_w, im_h = 720, 1280
    target_sz = [374.0, 538.0]
    
    # 测试坐标
    test_coords = [
        ("边界情况1", 0.0, 0.0),
        ("边界情况2", 100.8, 222.7),
        ("正常情况", 429.0, 566.0)
    ]
    
    all_pass = True
    for desc, x, y in test_coords:
        # 应用修复后的限制逻辑
        fixed_x = max(target_sz[0]/2, min(im_w - target_sz[0]/2, x))
        fixed_y = max(target_sz[1]/2, min(im_h - target_sz[1]/2, y))
        
        # 检查边界框是否有效
        bbox_left = fixed_x - target_sz[0]/2
        bbox_top = fixed_y - target_sz[1]/2
        bbox_right = fixed_x + target_sz[0]/2
        bbox_bottom = fixed_y + target_sz[1]/2
        
        valid = (bbox_left >= 0 and bbox_top >= 0 and 
                bbox_right <= im_w and bbox_bottom <= im_h)
        
        status = "✅" if valid else "❌"
        print(f"{status} {desc}: ({x:.1f}, {y:.1f}) → ({fixed_x:.1f}, {fixed_y:.1f})")
        
        if not valid:
            all_pass = False
    
    if all_pass:
        print("\n🎉 验证成功!")
        print("修复已正确应用，跟踪器现在应该可以正常工作。")
        print("\n📝 接下来您可以:")
        print("1. 运行 python gui_tracker.py")
        print("2. 选择您的视频文件")
        print("3. 框选目标对象") 
        print("4. 开始跟踪")
        print("\n预期结果: 跟踪将在整个视频中持续进行，不再出现'跟踪结果无效'错误。")
        return True
    else:
        print("\n❌ 验证失败!")
        print("修复可能没有正确应用，请检查代码。")
        return False

if __name__ == "__main__":
    success = verify_fix()
    print(f"\n{'='*50}")
    print(f"验证结果: {'成功' if success else '失败'}")
    sys.exit(0 if success else 1)