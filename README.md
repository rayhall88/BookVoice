# BookVoice Reader 🎧📖

![BookVoice Reader Logo](src/bookvoicer.ico) 

**BookVoice Reader** es una aplicación de escritorio construida con Python y Tkinter que transforma la lectura de libros electrónicos (EPUB) en una experiencia multimedia. Lee, escucha y sumérgete en tus historias favoritas con funciones de texto-a-voz, gestión de capítulos y exportación de audio.

### ✨ Características Principales

*   **Carga y Lectura de EPUBs:** Abre archivos EPUB y navega por su contenido con un índice interactivo.
*   **Narración con Voces Naturales:**
    *   **Online:** Utiliza las voces neuronales de Microsoft Edge (edge-tts) para una calidad excepcional.
    *   **Offline:** Si no hay conexión, cambia automáticamente al motor TTS de tu sistema operativo (SAPI5 en Windows, `say` en macOS, `espeak` en Linux).
*   **Reproducción Inteligente:**
    *   **Narración Progresiva:** Comienza a reproducir en cuanto el primer fragmento de audio está listo.
    *   **Pausa y Reanudación Robusta:** Detén y continúa la narración en el punto exacto donde la dejaste.
    *   **Paso Automático de Capítulos:** Al terminar un capítulo, si lo deseas, pasa automáticamente al siguiente.
*   **Exportación a MP3:**
    *   **Capítulo Individual:** Guarda el capítulo actual como un archivo MP3, con el nombre del capítulo sugerido.
    *   **Libro Completo:** Exporta cada capítulo del libro como un archivo MP3 independiente, organizado en una carpeta con el nombre del libro (ej. `001_Capitulo_1.mp3`, `002_Capitulo_2.mp3`...).
*   **Visualización de Imágenes:** Si un capítulo tiene ilustraciones, aparecerá un botón para abrir un visor y navegar por ellas.
*   **Totalmente Offline (para lectura y narración básica):** Una vez cargado el libro, puedes leerlo o usar el TTS del sistema sin necesidad de internet. La exportación a MP3 requiere `ffmpeg`.

### 🛠️ Tecnologías Utilizadas

*   **Lenguaje:** Python 3
*   **Interfaz Gráfica:** Tkinter
*   **Reproducción de Audio:** Pygame
*   **Procesamiento de Audio:** Pydub, ffmpeg
*   **Extracción de EPUB:** EbookLib, BeautifulSoup4
*   **Síntesis de Voz Online:** Edge-TTS
*   **Síntesis de Voz Offline:** Pyttsx3
*   **Gestión de Imágenes:** Pillow

### 📦 Instalación

* Para los usuarios de Windows ya existe una compilación que se puede descargar desde el siguiente link:
  https://drive.google.com/file/d/16MgyF-CVsNwunGYyvLQoBQDk_4kfYJ0C/view?usp=drive_link
* No necesita instalación solo ejecutar el archivo .exe descargado.
* Para utilizar las opciones de exportar a MP3 las narraciones de capitulos o del documento/libro entero es necesario tener instalado ffmpeg (https://www.ffmpeg.org) en el sistema o el fichero ffmpeg.exe en la misma carpeta de BookVoice.
