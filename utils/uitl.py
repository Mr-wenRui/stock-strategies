import os
from pathlib import Path



def get_root_path():
    current_file_path = Path(__file__).resolve()
    root_path = current_file_path.parents[1]  # 获取当前目录的上两级
    return root_path

