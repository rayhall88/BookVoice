# BookVoice Reader 🎧📖

![BookVoice Reader Logo](src/bookvoicer.ico) 

**BookVoice Reader** es una aplicación de escritorio construida con Python y Tkinter que transforma la lectura de libros electrónicos (EPUB) en una experiencia multimedia. Lee, escucha y sumérgete en tus historias favoritas con funciones de texto-a-voz, gestión de capítulos y exportación de audio.  
**BookVoice Reader** is a desktop application built with Python and Tkinter that transforms reading EPUB e-books into a multimedia experience. Read, listen, and immerse yourself in your favorite stories with text-to-speech, chapter management, and audio export features.

[Descargar BookVoice Reader para Windows / Download BookVoice Reader for Windows](https://drive.google.com/file/d/1YSmVOsTkLs2XZKGtUA4zmHDcauo30QsV/view?usp=drive_link)

---

## ✨ Características Principales / Key Features

### Español
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
*   **Totalmente Offline (para lectura y narración básica):** Una vez cargado el libro, puedes leerlo o usar el TTS del sistema sin necesidad de internet. La exportación a MP3 requiere [ffmpeg](https://www.ffmpeg.org).

### English
*   **Load and Read EPUBs:** Open EPUB files and navigate through their content with an interactive table of contents.
*   **Natural Voice Narration:**
    *   **Online:** Uses Microsoft Edge's neural voices (edge-tts) for exceptional quality.
    *   **Offline:** If there's no connection, it automatically switches to your operating system's TTS engine (SAPI5 on Windows, `say` on macOS, `espeak` on Linux).
*   **Smart Playback:**
    *   **Progressive Narration:** Starts playing as soon as the first audio fragment is ready.
    *   **Robust Pause/Resume:** Stop and resume narration exactly where you left off.
    *   **Automatic Chapter Advance:** When a chapter ends, you can choose to automatically move to the next one.
*   **MP3 Export:**
    *   **Single Chapter:** Save the current chapter as an MP3 file, with the chapter name suggested.
    *   **Full Book:** Export each chapter as an independent MP3 file, organized in a folder named after the book (e.g., `001_Chapter_1.mp3`, `002_Chapter_2.mp3`...).
*   **Image Viewer:** If a chapter contains illustrations, a button will appear to open a viewer and browse through them.
*   **Fully Offline (for reading and basic narration):** Once the book is loaded, you can read or use the system TTS without an internet connection. MP3 export requires [ffmpeg](https://www.ffmpeg.org).

---

## 🛠️ Tecnologías Utilizadas / Technologies Used

*   **Lenguaje / Language:** Python 3
*   **Interfaz Gráfica / GUI:** Tkinter
*   **Reproducción de Audio / Audio Playback:** Pygame
*   **Procesamiento de Audio / Audio Processing:** Pydub, ffmpeg
*   **Extracción de EPUB / EPUB Extraction:** EbookLib, BeautifulSoup4
*   **Síntesis de Voz Online / Online TTS:** Edge-TTS
*   **Síntesis de Voz Offline / Offline TTS:** Pyttsx3
*   **Gestión de Imágenes / Image Handling:** Pillow

---

## 📦 Instalación / Installation

### Español
*   Para los usuarios de Windows ya existe una compilación que se puede descargar desde el siguiente link: [BookVoice Reader para Windows](https://drive.google.com/file/d/1YSmVOsTkLs2XZKGtUA4zmHDcauo30QsV/view?usp=drive_link)
*   No necesita instalación, solo ejecutar el archivo `.exe` descargado.
*   Para utilizar las opciones de exportar a MP3 las narraciones de capítulos o del documento/libro entero es necesario tener instalado [ffmpeg](https://www.ffmpeg.org) en el sistema o colocar el fichero `ffmpeg.exe` en la misma carpeta de BookVoice.

### English
*   For Windows users, there is a pre-compiled version available for download at: [BookVoice Reader for Windows](https://drive.google.com/file/d/1YSmVOsTkLs2XZKGtUA4zmHDcauo30QsV/view?usp=drive_link)
*   No installation required; just run the downloaded `.exe` file.
*   To use the MP3 export options (chapters or full book), you need to have [ffmpeg](https://www.ffmpeg.org) installed on your system or place the `ffmpeg.exe` file in the same folder as BookVoice.

  ---
  ## ❤️ Donar/donate
  ### Apoya nuestro proyecto / Support our project
  ![bc1qgcxkczwcl8gpfl2t9v5mjmnszyckgz2kew95nt](src/donar.png) 
