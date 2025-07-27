#!/usr/bin/env python3
"""
简单的健康检查脚本
"""

import requests
import time
import sys

def check_health(max_retries=10, delay=2):
    """检查应用健康状态"""
    for i in range(max_retries):
        try:
            print(f"尝试 {i+1}/{max_retries}: 连接到 http://localhost:5000/health")
            response = requests.get('http://localhost:5000/health', timeout=5)
            
            if response.status_code == 200:
                print("✅ 健康检查通过!")
                print(f"响应: {response.json()}")
                return True
            else:
                print(f"❌ 健康检查失败: HTTP {response.status_code}")
                print(f"响应: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"⏳ 连接拒绝，等待 {delay} 秒后重试...")
            time.sleep(delay)
        except Exception as e:
            print(f"❌ 错误: {e}")
            time.sleep(delay)
    
    print("❌ 健康检查失败：无法连接到应用")
    return False

if __name__ == '__main__':
    success = check_health()
    sys.exit(0 if success else 1)