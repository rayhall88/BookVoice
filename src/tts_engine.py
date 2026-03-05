# -*- coding: utf-8 -*-
"""
Created on Fri Feb 20 06:40:01 2026

@author: ray
"""

import asyncio
import edge_tts
import tempfile
import os
import platform
from system_tts import get_system_voices, system_text_to_mp3
import ctypes
from ctypes import wintypes

# Variable global para saber si edge-tts está disponible
_edge_available = None

# Constantes de idiomas primarios (definidas en winnt.h)
LANG_SPANISH = 0x0A
LANG_ENGLISH = 0x09

# Macro para obtener el idioma primario de un LANGID
def PRIMARYLANGID(langid):
    return langid & 0x3FF  # Los 10 bits bajos son el idioma primario

def get_os_language_code():
    """
    Devuelve el código de idioma del sistema operativo Windows:
    - "es" si el idioma del sistema es español.
    - "en" si el idioma del sistema es inglés.
    - "und" para cualquier otro idioma o si no se puede determinar.
    """
    try:
        # Obtener el identificador de idioma de la interfaz de usuario del usuario actual
        user_lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        
        # Extraer el idioma primario
        primary_lang = PRIMARYLANGID(user_lang_id)
        
        # Determinar el código de retorno
        if primary_lang == LANG_SPANISH:
            return "es"
        elif primary_lang == LANG_ENGLISH:
            return "en"
        else:
            return "und"
    except Exception:
        # En caso de error (poco probable), devolvemos "und"
        return "und"




def check_edge_tts():
    """Intenta conectar con edge-tts y devuelve True si funciona."""
    try:
        # Intentar listar voces (rápido)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(edge_tts.list_voices())
        loop.close()
        return True
    except Exception:
        return False

def get_voices(idioma="en"):
    """Devuelve lista de voces disponibles (edge-tts si funciona, sino sistema)."""
    global _edge_available
    if _edge_available is None:
        _edge_available = check_edge_tts()

    if _edge_available:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            voices = loop.run_until_complete(edge_tts.list_voices())
            loop.close()
            # Filtrar español o todas? Depende de tu preferencia
            if idioma ==  "es" or idioma== "en":
                primeros = [v for v in voices if f'{idioma}-' in v['ShortName']]
                segundos = [v for v in voices if not f'{idioma}-' in v['ShortName']]
                voces = primeros + segundos
                
            else:
                voces = voices
            return [('edge-tts', 'online', f"{v['ShortName']} - {v['Locale']} ({v['Gender']})", v['ShortName']) 
                    for v in voces]
        except Exception:
            _edge_available = False

    # Fallback a sistema
    sys_voices = get_system_voices()
    return [('sistema', 'offline', name, code) for name, code in sys_voices]

async def _generate_single_edge(text, voice, output_file):
    comm = edge_tts.Communicate(text, voice)
    await comm.save(output_file)

def text_to_mp3(text_chunks, voice_info, progress_callback=None):
    """
    Genera MP3 para cada fragmento.
    voice_info es una tupla (tipo, modo, nombre_mostrar, codigo)
    tipo: 'edge-tts' o 'sistema'
    modo: 'online' o 'offline' (para info)
    codigo: identificador de la voz
    """
    temp_files = []
    total = len(text_chunks)
    voice_type, _, _, voice_code = voice_info

    for i, chunk in enumerate(text_chunks):
        if not chunk.strip():
            continue
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp.close()

        if voice_type == 'edge-tts':
            asyncio.run(_generate_single_edge(chunk, voice_code, temp.name))
        else:  # sistema
            system_text_to_mp3(chunk, voice_code, temp.name)

        temp_files.append(temp.name)
        if progress_callback:
            progress_callback(i+1, total)
    return temp_files