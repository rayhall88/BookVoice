# -*- coding: utf-8 -*-
"""
Created on Fri Feb 20 06:29:20 2026

@author: ray
"""

import subprocess
import os
import tempfile
import sys

def merge_mp3_files(file_list, output_path):
    """
    Concatena archivos MP3 usando ffmpeg sin mostrar ventana de consola.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for mp3 in file_list:
            abs_path = os.path.abspath(mp3).replace('\\', '/')
            f.write(f"file '{abs_path}'\n")
        list_file = f.name

    try:
        cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_file, '-c', 'copy', output_path]
        
        # Configuración para ocultar ventana en Windows
        startupinfo = None
        creationflags = 0
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW  # solo disponible en Windows 10+
        
        result = subprocess.run(cmd, capture_output=True, text=True,
                                startupinfo=startupinfo, creationflags=creationflags)
        if result.returncode != 0:
            raise RuntimeError(f"Error de ffmpeg: {result.stderr}")
    finally:
        os.unlink(list_file)
        
def cleanup_temp_files(file_list):
    for f in file_list:
        if os.path.exists(f):
            os.remove(f)