import pyttsx3
import tempfile
import os
import subprocess
import sys


def _check_ffmpeg():
    """Devuelve True si ffmpeg está disponible en el sistema."""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def system_text_to_mp3(text, voice_id, output_file):
    """
    Genera audio con TTS del sistema.
    - Si output_file termina en .mp3 y ffmpeg está disponible, se genera MP3.
    - Si no, se genera WAV y se devuelve la ruta con extensión .wav.
    La función retorna la ruta real del archivo generado (puede ser .wav).
    """
    # Generar WAV temporal
    temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    temp_wav.close()
    
    try:
        # Usar pyttsx3 para generar WAV
        engine = pyttsx3.init()
        engine.setProperty('voice', voice_id)
        engine.save_to_file(text, temp_wav.name)
        engine.runAndWait()
        engine.stop()

        # Determinar si debemos convertir a MP3
        if output_file.lower().endswith('.mp3') and _check_ffmpeg():
            # Convertir WAV a MP3 con ffmpeg (ventana oculta)
            cmd = ['ffmpeg', '-y', '-i', temp_wav.name,
                   '-codec:a', 'libmp3lame', '-qscale:a', '2', output_file]
            
            startupinfo = None
            creationflags = 0
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
                creationflags = subprocess.CREATE_NO_WINDOW
            
            subprocess.run(cmd, capture_output=True, check=True,
                           startupinfo=startupinfo, creationflags=creationflags)
            os.unlink(temp_wav.name)
            return output_file
        else:
            # No hay ffmpeg o se pidió WAV: devolver el WAV
            if output_file.lower().endswith('.mp3'):
                # Cambiar extensión a .wav
                wav_output = output_file[:-4] + '.wav'
                os.rename(temp_wav.name, wav_output)
                return wav_output
            else:
                # Ya es WAV
                os.rename(temp_wav.name, output_file)
                return output_file
    except Exception as e:
        if os.path.exists(temp_wav.name):
            os.unlink(temp_wav.name)
        raise e





def get_system_voices():
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    result = []
    for v in voices:
        # En Windows, v.id es algo como "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_ES-ES_ELVIRA_11.0"
        # Extraemos un nombre legible
        name = v.name or v.id.split('\\')[-1]
        result.append((name, v.id))
    engine.stop()
    return result

