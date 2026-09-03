# src/entry.py
import sys
import os

# 確保專案根目錄在 sys.path 中
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app
