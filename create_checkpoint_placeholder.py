#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建checkpoint占位文件的脚本
用于在没有真实权重文件时创建一个占位文件，方便用户理解路径结构
"""

import os
import sys

def create_checkpoint_placeholder():
    """创建checkpoint占位文件"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    checkpoint_path = os.path.join(current_dir, 'snapshot', 'checkpoint_e30.pth')
    
    # 创建目录（如果不存在）
    os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
    
    # 创建占位文件
    placeholder_content = """# This is a placeholder file
# Please replace this file with your actual LightTrack model checkpoint
# The real checkpoint file should be named 'checkpoint_e30.pth' and placed in the snapshot/ directory
# Download link: https://drive.google.com/drive/folders/1HXhdJO3yhQYw3O7nGUOXHu2S20Bs8CfI
"""
    
    with open(checkpoint_path, 'w') as f:
        f.write(placeholder_content)
    
    print(f"创建占位文件: {checkpoint_path}")
    print("请将真实的checkpoint_e30.pth文件替换此占位文件")

if __name__ == "__main__":
    create_checkpoint_placeholder()