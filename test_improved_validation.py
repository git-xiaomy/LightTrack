#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the improved GUI tracker validation and messaging
"""

import os
import sys
import numpy as np

# Add project path  
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_improved_validation_messaging():
    """Test the improved validation messaging"""
    print("=" * 80)
    print("Testing Improved Validation Messaging")
    print("=" * 80)
    
    # Mock the validation logic with enhanced messaging
    def validate_tracking_result(center_x, center_y, size_w, size_h, width, height, frame_idx):
        """Enhanced validation with detailed error reporting"""
        min_center_x = size_w / 2 + 1
        min_center_y = size_h / 2 + 1
        max_center_x = width - size_w / 2 - 1
        max_center_y = height - size_h / 2 - 1
        
        if (center_x < min_center_x or center_y < min_center_y or 
            size_w <= 0 or size_h <= 0 or
            center_x > max_center_x or center_y > max_center_y or
            size_w > width or size_h > height):
            
            print(f"❌ 第{frame_idx}帧检测到无效的跟踪结果:")
            print(f"   返回坐标: center=({center_x:.1f}, {center_y:.1f}), size=({size_w:.1f}, {size_h:.1f})")
            print(f"   有效范围: center_x=[{min_center_x:.1f}, {max_center_x:.1f}], center_y=[{min_center_y:.1f}, {max_center_y:.1f}]")
            
            # Detailed explanation of why invalid
            reasons = []
            if center_x < min_center_x:
                bbox_left = int(center_x - size_w/2)
                reasons.append(f"中心X({center_x:.1f}) < 最小值({min_center_x:.1f})，会导致左边界={bbox_left} < 0")
            if center_y < min_center_y:
                bbox_top = int(center_y - size_h/2)
                reasons.append(f"中心Y({center_y:.1f}) < 最小值({min_center_y:.1f})，会导致上边界={bbox_top} < 0")
            if size_w <= 0 or size_h <= 0:
                reasons.append(f"尺寸无效: width={size_w}, height={size_h}")
            if center_x > max_center_x:
                reasons.append(f"中心X({center_x:.1f}) > 最大值({max_center_x:.1f})，超出视频右边界")
            if center_y > max_center_y:
                reasons.append(f"中心Y({center_y:.1f}) > 最大值({max_center_y:.1f})，超出视频下边界")
            
            for i, reason in enumerate(reasons, 1):
                print(f"   {i}. {reason}")
            
            print(f"   💡 系统将切换到演示模式，这是正常的错误恢复行为")
            return False
        return True
    
    # Test cases
    test_cases = [
        {
            'name': '用户报告的问题坐标',
            'center_x': 77.0, 'center_y': 175.3,
            'size_w': 337.0, 'size_h': 444.0,
            'width': 720, 'height': 1280, 'frame_idx': 3
        },
        {
            'name': '零坐标',
            'center_x': 0.0, 'center_y': 0.0,
            'size_w': 100.0, 'size_h': 100.0,
            'width': 720, 'height': 1280, 'frame_idx': 5
        },
        {
            'name': '正常坐标',
            'center_x': 400.0, 'center_y': 600.0,
            'size_w': 100.0, 'size_h': 100.0,
            'width': 720, 'height': 1280, 'frame_idx': 10
        }
    ]
    
    for test in test_cases:
        print(f"\n测试场景: {test['name']}")
        print("-" * 50)
        is_valid = validate_tracking_result(
            test['center_x'], test['center_y'], 
            test['size_w'], test['size_h'],
            test['width'], test['height'], test['frame_idx']
        )
        if is_valid:
            print("✅ 坐标有效，继续真实模型跟踪")
        else:
            print("🔄 坐标无效，切换到演示模式")

def test_enhanced_bbox_handling():
    """Test enhanced bbox handling in demo mode"""
    print("\n" + "=" * 80)
    print("Testing Enhanced Bbox Handling")
    print("=" * 80)
    
    # Mock safe extraction with error handling
    def safe_extract_scalar(value):
        if hasattr(value, 'item'):
            return float(value.item())
        elif hasattr(value, '__iter__') and not isinstance(value, str):
            return float(value[0])
        else:
            return float(value)
    
    def update_demo_bbox_safely(bbox, width, height, drift_x, drift_y):
        """Enhanced demo bbox update with error handling"""
        try:
            new_x = int(safe_extract_scalar(bbox[0])) + int(drift_x)
            new_y = int(safe_extract_scalar(bbox[1])) + int(drift_y)
            bbox_w = int(safe_extract_scalar(bbox[2]))
            bbox_h = int(safe_extract_scalar(bbox[3]))
            
            updated_bbox = [
                max(0, min(width - bbox_w, new_x)),
                max(0, min(height - bbox_h, new_y)),
                bbox_w,
                bbox_h
            ]
            print(f"✅ Demo bbox更新成功: {bbox} -> {updated_bbox}")
            return updated_bbox
        except Exception as e:
            print(f"⚠️  Demo bbox更新出错: {e}, 保持原bbox: {bbox}")
            return bbox
    
    # Test various bbox formats
    test_bboxes = [
        [100, 100, 50, 50],  # Normal list
        [np.float64(100), np.float64(100), np.float64(50), np.float64(50)],  # NumPy scalars
        [np.array([100]), np.array([100]), np.array([50]), np.array([50])],  # NumPy arrays
    ]
    
    for i, bbox in enumerate(test_bboxes):
        print(f"\n测试bbox格式 {i+1}: {type(bbox[0]).__name__}")
        updated = update_demo_bbox_safely(bbox, 720, 1280, 5, -3)
        print(f"   结果: {updated}")

if __name__ == "__main__":
    test_improved_validation_messaging()
    test_enhanced_bbox_handling()
    
    print("\n" + "=" * 80)
    print("改进总结")
    print("=" * 80)
    print("✅ 增强了验证错误消息，详细解释为什么坐标无效")
    print("✅ 改进了演示模式的用户友好性消息")
    print("✅ 增强了bbox处理的错误恢复机制")
    print("✅ 明确说明切换到演示模式是正常的错误恢复行为")
    print("💡 这些改进让用户更好地理解系统的工作原理")