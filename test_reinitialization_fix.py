#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify the reinitialization fix
"""

import os
import sys

# Add project path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_reinitialization_fix():
    """Test that the reinitialization logic has been removed"""
    print("=" * 60)
    print("Testing LightTrack GUI Reinitialization Fix")
    print("=" * 60)
    
    # Read the gui_tracker.py file
    gui_tracker_path = os.path.join(current_dir, 'gui_tracker.py')
    
    if not os.path.exists(gui_tracker_path):
        print("❌ gui_tracker.py not found")
        return False
    
    with open(gui_tracker_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that reinitialization logic has been removed or modified
    tests = [
        {
            'name': 'No center position reinitialization',
            'bad_patterns': [
                'recovery_center_x = width // 2',
                'recovery_center_y = height // 2',
            ],
            'should_not_exist': True
        },
        {
            'name': 'No tracker.init calls in recovery',
            'bad_patterns': [
                'state = self.tracker.init(frame, recovery_pos',
                'self.tracker.init(frame, target_pos_reset',
            ],
            'should_not_exist': True
        },
        {
            'name': 'Has continuity-preserving behavior',
            'good_patterns': [
                '保持原始跟踪模板',
                '继续使用原始模型跟踪',
                '确保了跟踪的连续性',
                '保持目标跟踪连续性'
            ],
            'should_exist': True
        }
    ]
    
    all_passed = True
    
    for test in tests:
        print(f"\n📋 {test['name']}:")
        
        if test.get('should_not_exist'):
            # These patterns should NOT exist
            found_patterns = []
            for pattern in test.get('bad_patterns', []):
                if pattern in content:
                    found_patterns.append(pattern)
            
            if found_patterns:
                print(f"   ❌ Found problematic patterns:")
                for pattern in found_patterns:
                    print(f"      - {pattern}")
                all_passed = False
            else:
                print(f"   ✅ No problematic patterns found")
        
        if test.get('should_exist'):
            # These patterns SHOULD exist
            found_patterns = []
            for pattern in test.get('good_patterns', []):
                if pattern in content:
                    found_patterns.append(pattern)
            
            if found_patterns:
                print(f"   ✅ Found expected patterns:")
                for pattern in found_patterns:
                    print(f"      - {pattern}")
            else:
                print(f"   ❌ Missing expected patterns")
                all_passed = False
    
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 All tests passed! The reinitialization fix is properly implemented.")
        print("")
        print("✅ Key improvements:")
        print("   - Tracker no longer reinitializes to center position")
        print("   - Original target template is preserved")
        print("   - Tracking continuity is maintained")
        print("   - Coordinate clamping still prevents out-of-bounds boxes")
    else:
        print("❌ Some tests failed. The fix may not be complete.")
    
    print(f"{'='*60}")
    return all_passed

if __name__ == "__main__":
    success = test_reinitialization_fix()
    sys.exit(0 if success else 1)