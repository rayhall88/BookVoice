import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
import pygame
import edge_tts
import asyncio
import re
from epub_reader import extract_epub_content
from tts_engine import get_voices, text_to_mp3, get_os_language_code
from audio_exporter import merge_mp3_files, cleanup_temp_files
from PIL import Image, ImageTk
from system_tts import _check_ffmpeg
import io


# Configuración para asyncio en Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
def resource_path(relative_path):
    """Obtiene la ruta absoluta a un recurso (funciona en desarrollo y en el .exe)"""
    try:
        # PyInstacker crea una carpeta temporal y guarda la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class BookVoiceReader:
    def __init__(self, root):
        self.root = root
        self.root.title("BookVoice Reader 3.1")
        self.root.iconbitmap(default=resource_path('bookvoicer.ico'))
        self.root.geometry("900x700")

        # Variables de estado
        self.current_book = None
        self.chapters = []                # lista de (titulo, contenido)
        self.current_chapter_index = 0
        self.voices_list = []              # [(nombre_mostrar, codigo_voz)]
        self.paused = False   # Indica si la narración está en pausa
        self.current_playback_file = None
        self.pause_position = 0
        self.fragment_indices = []   # lista de (start, end) para el capítulo actual
        self.current_fragment_index = -1
        self.auto_next = tk.BooleanVar(value=True)  # Activar por defecto
        self.chapter_images = []          # lista paralela a chapters con imágenes
        self.image_button = None           # botón para abrir visor de imágenes
        self.idioma = get_os_language_code()
        self.ffmpeg = _check_ffmpeg()
        # Control de reproducción y generación
        self.playing = False
        self.generation_cancelled = False
        self.generation_finished = False
        self.current_temp_files = []       # archivos temporales generados
        self.playback_queue = []            # cola de archivos listos para reproducir

        # Control de carga de libros (evitar conflictos)
        self.loading_lock = threading.Lock()
        self.cancel_loading = False
        self.current_loading_thread = None

        # Control de actualización del árbol (evitar recursión)
        self._updating_tree = False

        # Crear interfaz
        self.create_menu()
        self.create_widgets()

        

        # Cargar voces en segundo plano
        if not self.ffmpeg:
            txt1 = "ffmpeg no encontrado" if self.idioma == "es" else "ffmpeg not found"
            txt2 = "La exportación a MP3 no estará disponible.\n Descarga ffmpeg desde https://ffmpeg.org/" if self.idioma == "es" else "MP3 export will not be available.\n Download ffmpeg from https://ffmpeg.org/"
            messagebox.showwarning(txt1,txt2)        
        self.load_voices()

    # ---------- Menú ----------
    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo" if self.idioma == "es" else "File", menu=file_menu)
        file_menu.add_command(label="Abrir EPUB" if self.idioma == "es" else "Open EPUB", command=self.open_epub)
        file_menu.add_separator()
        file_menu.add_command(label="Salir" if self.idioma == "es" else "Exit", command=self.root.quit)

        export_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Exportar" if self.idioma == "es" else "Export", menu=export_menu)
        full=export_menu.add_command(label="Exportar libro completo a capítulos MP3"  if self.idioma == "es" else "Export the entire book to MP3 chapters", command=self.export_full)
        cap=export_menu.add_command(label="Exportar capítulo actual a MP3"  if self.idioma == "es" else "Export current chapter to MP3", command=self.export_chapter)
        if not self.ffmpeg:
             export_menu.entryconfig("Exportar libro completo a capítulos MP3", state=tk.DISABLED)
             export_menu.entryconfig("Exportar capítulo actual a MP3", state=tk.DISABLED)          
            
        
        # Menú Ayuda
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ayuda"  if self.idioma == "es" else "Help", menu=help_menu)
        help_menu.add_command(label="Cómo usar"  if self.idioma == "es" else "How to use", command=self.show_help)
        help_menu.add_separator()
        help_menu.add_command(label="Acerca de BookVoice"  if self.idioma == "es" else "About BookVoice", command=self.show_about)
        
        # --- NUEVO: Botón de donación directamente en la barra ---
        menubar.add_command(label="❤️ Donar", command=self.show_donation)

    # ---------- Interfaz gráfica ----------
    def create_widgets(self):
        # Panel izquierdo: índice
        left_frame = ttk.Frame(self.root, width=250)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        left_frame.pack_propagate(False)

        ttk.Label(left_frame, text="Índice" if self.idioma == "es" else "Index", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        self.toc_tree = ttk.Treeview(left_frame, show='tree')
        self.toc_tree.pack(fill=tk.BOTH, expand=True)
        self.toc_tree.bind('<<TreeviewSelect>>', self.on_toc_select)

        # Panel central: contenido + controles
        center_frame = ttk.Frame(self.root)
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Título del capítulo
        title_frame = ttk.Frame(center_frame)
        title_frame.pack(fill=tk.X, pady=5)
        
        self.chapter_title_var = tk.StringVar()
        ttk.Label(title_frame, textvariable=self.chapter_title_var, font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        
        self.image_button = ttk.Button(title_frame, text="📷 Ver ilustraciones" if self.idioma == "es" else "📷 See illustrations", command=self.show_images, state=tk.DISABLED)
        self.image_button.pack(side=tk.RIGHT, padx=5)

        # Área de texto con scroll
        text_frame = ttk.Frame(center_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.text_area = tk.Text(text_frame, wrap=tk.WORD, font=('Arial', 11), padx=20, pady=20)
        scroll_y = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_area.yview)
        self.text_area.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_area.tag_configure("highlight", background="yellow", foreground="black")
        self.text_area.configure(state='disabled')

        # Barra de navegación entre capítulos
        nav_frame = ttk.Frame(center_frame)
        nav_frame.pack(fill=tk.X, pady=5)

        self.prev_button = ttk.Button(nav_frame, text="◀ Anterior"  if self.idioma == "es" else "◀ Previous", command=self.prev_chapter)
        self.prev_button.pack(side=tk.LEFT, padx=2)
        self.next_button = ttk.Button(nav_frame, text="Siguiente ▶"  if self.idioma == "es" else "Next ▶", command=self.next_chapter)
        self.next_button.pack(side=tk.LEFT, padx=2)
        ttk.Label(nav_frame, text="Capítulo:"  if self.idioma == "es" else "Chapter:").pack(side=tk.LEFT, padx=(10,2))
        self.chapter_spinbox = ttk.Spinbox(nav_frame, from_=1, to=1, width=5, command=self.go_to_chapter)
        self.chapter_spinbox.pack(side=tk.LEFT)
        self.total_chapters_label = ttk.Label(nav_frame, text="de 1")
        self.total_chapters_label.pack(side=tk.LEFT)

        # Panel inferior: narración
        ttk.Label(center_frame, text="Narración (edge-tts)"  if self.idioma == "es" else "Narrative (edge-tts)", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(10,0))

        voice_frame = ttk.Frame(center_frame)
        voice_frame.pack(fill=tk.X)

        ttk.Label(voice_frame, text="Voz:" if self.idioma == "es" else "Voice:").pack(side=tk.LEFT)
        self.voice_combobox = ttk.Combobox(voice_frame, state='readonly', width=40)
        self.voice_combobox.pack(side=tk.LEFT, padx=5)

        # Botones de narración
        btn_frame = ttk.Frame(center_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        self.play_button = ttk.Button(btn_frame, text="▶ Narrar capítulo"  if self.idioma == "es" else "▶ Narrate chapter", command=self.narrate_chapter)
        self.play_button.pack(side=tk.LEFT, padx=2)
        self.pause_button = ttk.Button(btn_frame, text="⏸️ Pausa"  if self.idioma == "es" else "⏸️ Pause", command=self.toggle_pause, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=2)
        self.stop_button = ttk.Button(btn_frame, text="■ Detener"  if self.idioma == "es" else "■ Stop", command=self.stop_narration, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=2)
        auto_next_check = ttk.Checkbutton(
            center_frame, 
            text="Reproducir siguiente capítulo automáticamente"  if self.idioma == "es" else "Play next chapter automatically",
            variable=self.auto_next
        )
        auto_next_check.pack(anchor=tk.W, pady=2)        

        # Barra de progreso
        self.progress = ttk.Progressbar(center_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)

        self.status_label = ttk.Label(center_frame, text="Listo" if self.idioma == "es" else "Ready")
        self.status_label.pack(anchor=tk.W)

    # ---------- Carga de voces ----------
    def load_voices(self):
        def fetch():
            try:
                # get_voices devuelve lista de tuplas (tipo, modo, display, code)
                self.voices_list = get_voices(idioma=self.idioma)
            except Exception as e:
                print("Error cargando voces:", e)
                self.voices_list = [("Error al cargar voces", "")]
            finally:
                self.root.after(0, self.update_voice_list)
    
        threading.Thread(target=fetch, daemon=True).start()

    def update_voice_list(self):
        """Actualiza el combobox con las voces obtenidas y muestra el modo."""
        display_names = [v[2] for v in self.voices_list]  # índice 2 = nombre a mostrar
        self.voice_combobox['values'] = display_names
        if display_names:
            self.voice_combobox.current(0)
            modo = self.voices_list[0][1]  # índice 1 = 'online' o 'offline'
            if modo == 'offline':
                self.status_label.config(text="Modo sin conexión (TTS del sistema)"  if self.idioma == "es" else "Offline mode (system TTS)")
                # Notificar al usuario solo una vez
                if not hasattr(self, '_offline_notified'):
                    txt = "No se pudo conectar a edge-tts. Se usará el TTS del sistema (calidad inferior)."  if self.idioma == "es" else  "Could not connect to edge-tts. System TTS will be used (lower quality)."
                    messagebox.showinfo("Offline",txt)
                    self._offline_notified = True
            else:
                self.status_label.config(text="Modo online (edge-tts)"  if self.idioma == "es" else "Online mode (edge-tts)")
        else:
            txt = "No hay voces disponibles" if self.idioma == "es" else "No voices available"
            self.voice_combobox.set(txt)

    # ---------- Carga de EPUB ----------
    def open_epub(self):
        # Detener narración si está activa
        if self.playing:
            self.stop_narration()

        # Asegurar botones en estado inicial
        self.idioma = get_os_language_code()
        self.load_voices()
        self.play_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.status_label.config(text="Listo")

        # Cancelar carga anterior si existe
        if self.current_loading_thread and self.current_loading_thread.is_alive():
            self.cancel_loading = True
            self.current_loading_thread.join(timeout=1.0)

        file_path = filedialog.askopenfilename(filetypes=[("EPUB files", "*.epub")])
        if not file_path:
            return

        # Limpiar interfaz del libro anterior
        self.toc_tree.delete(*self.toc_tree.get_children())
        self.text_area.configure(state='normal')
        self.text_area.delete(1.0, tk.END)
        self.text_area.configure(state='disabled')
        self.chapter_title_var.set("")
        self.current_book = None
        self.chapters = []
        if self.image_button:
            self.image_button.config(state=tk.DISABLED)
        
        self.current_chapter_index = 0
        self.chapter_spinbox.config(from_=1, to=1, state='readonly')
        self.chapter_spinbox.delete(0, tk.END)
        self.chapter_spinbox.insert(0, "1")
        self.total_chapters_label.config(text="de 1")

        self.status_label.config(text="Cargando EPUB..." if self.idioma == "es" else "Loading EPUB...")
        self.root.update()

        self.cancel_loading = False

        def load():
            with self.loading_lock:
                if self.cancel_loading:
                    return
                try:
                    book_data = extract_epub_content(file_path)
                    if self.cancel_loading:
                        return
                    self.current_book = book_data
                    self.chapters = book_data['chapters']
                    self.chapter_images = book_data['chapter_images']
                    if book_data['language']:
                        self.idioma = book_data['language']
                    self.root.after(0, self.update_after_load)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    self.root.after(0, lambda: messagebox.showerror("Error", f"No se pudo cargar el EPUB:\n{e}"))
                    self.root.after(0, lambda: self.status_label.config(text="Error al cargar"))

        self.current_loading_thread = threading.Thread(target=load, daemon=True)
        self.current_loading_thread.start()

    def update_after_load(self):
        try:
            self.root.title(f"BookVoice Reader - {self.current_book['title']} por {self.current_book['author']}")

            # Poblar árbol de índice
            for i, (chap_title, _) in enumerate(self.chapters):
                self.toc_tree.insert('', 'end', iid=str(i), text=chap_title, values=(i,))

            total = len(self.chapters)
            self.chapter_spinbox.config(to=total, state='readonly')
            self.chapter_spinbox.delete(0, tk.END)
            self.chapter_spinbox.insert(0, "1")
            self.total_chapters_label.config(text=f"de {total}")

            self.current_chapter_index = 0
            self.display_chapter(0)
            self.load_voices()
            self.status_label.config(text="EPUB cargado correctamente" if self.idioma == "es" else "EPUB loaded successfully" )
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Error al actualizar interfaz:\n{e}")

    # ---------- Visualización de capítulos ----------
    def display_chapter(self, index):
        if not self.chapters or index < 0 or index >= len(self.chapters):
            return
        title, content = self.chapters[index]
        self.chapter_title_var.set(title)
        self.text_area.configure(state='normal')
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, content)
        self.text_area.see(1.0)
        self.text_area.tag_remove("highlight", "1.0", tk.END)
        self.text_area.configure(state='disabled')
        self.current_playback_file = None
        self.pause_position = 0
        # Actualizar spinbox
        self.chapter_spinbox.delete(0, tk.END)
        self.chapter_spinbox.insert(0, str(index+1))

        # Seleccionar en el árbol sin disparar evento
        self._updating_tree = True
        self.toc_tree.selection_set(str(index))
        self._updating_tree = False
        
       
        # Habilitar/deshabilitar botón de imágenes
        if (hasattr(self, 'chapter_images') and 
            index < len(self.chapter_images) and 
            self.chapter_images[index]):
            self.image_button.config(state=tk.NORMAL)
        else:
            self.image_button.config(state=tk.DISABLED)
    
        def on_toc_select(self, event):
            if self.playing:
                return
            if self._updating_tree:
                return
            selected = self.toc_tree.selection()
            if selected:
                idx = int(selected[0])
                if idx != self.current_chapter_index:
                    self.current_chapter_index = idx
                    self.display_chapter(idx)

    def on_toc_select(self, event):
        if self.playing:
            return
        if self._updating_tree:
            return
        selected = self.toc_tree.selection()
        if selected:
            idx = int(selected[0])
            if idx != self.current_chapter_index:
                self.current_chapter_index = idx
                self.display_chapter(idx)


    def prev_chapter(self):
        if self.current_chapter_index > 0:
            self.current_chapter_index -= 1
            self.display_chapter(self.current_chapter_index)

    def next_chapter(self):
        if self.current_chapter_index < len(self.chapters) - 1:
            self.current_chapter_index += 1
            self.display_chapter(self.current_chapter_index)

    def go_to_chapter(self):
        try:
            idx = int(self.chapter_spinbox.get()) - 1
            if 0 <= idx < len(self.chapters):
                self.current_chapter_index = idx
                self.display_chapter(idx)
        except:
            pass

    # ---------- Utilidades ----------


    def split_text(self,text, max_chars=3000):
        """
        Divide un texto en fragmentos de hasta max_chars caracteres (considerando
        espacios simples al unir) y devuelve los fragmentos junto con los índices
        de inicio y fin de cada fragmento en el texto original.
    
        Args:
            text (str): Texto a dividir.
            max_chars (int): Longitud máxima de cada fragmento.
    
        Returns:
            tuple: (fragments, indices)
                - fragments: lista de strings, cada fragmento con palabras unidas por un espacio.
                - indices: lista de tuplas (start, end) donde start es la posición
                  de la primera letra del fragmento y end la posición de la última
                  letra en el texto original.
        """
        # Encuentra todas las palabras (secuencias sin espacios) con sus posiciones
        pattern = re.compile(r'\S+')
        matches = list(pattern.finditer(text))
        
        fragments = []
        indices = []
        
        current_words = []
        current_start = None
        current_end = None
        current_len = 0  # longitud acumulada de palabras + espacios simples
        
        for match in matches:
            word = match.group()
            word_len = len(word)
            
            # Longitud si añadimos esta palabra al fragmento actual
            if not current_words:
                new_len = word_len
            else:
                new_len = current_len + 1 + word_len  # +1 por el espacio
            
            if new_len <= max_chars:
                # Cabe en el fragmento actual
                if not current_words:
                    current_start = match.start()
                current_words.append(word)
                current_len = new_len
                current_end = match.end() - 1  # índice del último carácter
            else:
                # Guardar fragmento actual y empezar uno nuevo
                if current_words:
                    fragments.append(' '.join(current_words))
                    indices.append((current_start, current_end))
                
                # Nuevo fragmento con la palabra actual
                current_words = [word]
                current_len = word_len
                current_start = match.start()
                current_end = match.end() - 1
        
        # Último fragmento
        if current_words:
            fragments.append(' '.join(current_words))
            indices.append((current_start, current_end))
        
        return fragments, indices

    def get_selected_voice(self):
        """Devuelve la tupla completa de la voz seleccionada: (tipo, modo, display, code)"""
        selected_display = self.voice_combobox.get()
        for voice in self.voices_list:
            if voice[2] == selected_display:
                return voice
        return None

    def sanitize_filename(self, name):
        """Convierte un string en un nombre de archivo válido."""
        # Elimina caracteres prohibidos en Windows: < > : " / \ | ? *
        safe = re.sub(r'[<>:"/\\|?*]', '_', name)
        # También quita puntos al inicio/final y espacios innecesarios
        safe = safe.strip().replace('  ', ' ')
        # Limita la longitud a 100 caracteres para no exceder límites
        return safe[:100]

    # ---------- Narración progresiva ----------
    def narrate_chapter(self):
        # Si la narración está pausada, simplemente reanudamos
        #self.toc_tree.config(state=tk.DISABLED)
        self.chapter_spinbox.config(state=tk.DISABLED)
        self.prev_button.config(state=tk.DISABLED)
        self.next_button.config(state=tk.DISABLED)

    
        # Si no hay capítulos o voz, mostrar error
        if not self.chapters:
            txt = "Primero carga un libro."  if self.idioma == "es" else "First, load a book."
            messagebox.showinfo("Info", txt)
            return
        voice_info = self.get_selected_voice()
        if not voice_info:
            txt = "Selecciona una voz."  if self.idioma == "es" else "Select a voice."
            messagebox.showerror("Error", "Selecciona una voz.")
            return
    
        # Detener cualquier narración previa (por si acaso)
        if self.playing:
            self.stop_narration()
    
        _, chapter_text = self.chapters[self.current_chapter_index]
        fragments, indices = self.split_text(chapter_text,max_chars=500)
        self.fragment_indices = indices
    
        # Estado inicial de la nueva narración
        self.playing = True
        self.paused = False
        self.generation_cancelled = False
        self.generation_finished = False
        self.current_temp_files = []
        self.playback_queue = []
        # Deshabilitar controles de navegación

    
        self.play_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL, text="⏸️ Pausa"  if self.idioma == "es" else "⏸️ Pause")
        self.stop_button.config(state=tk.NORMAL)
        self.progress['maximum'] = len(fragments)
        self.progress['value'] = 0
        self.status_label.config(text="Generando audio..."  if self.idioma == "es" else "Generating audio...")
    
        # Iniciar hilo de generación
        thread = threading.Thread(target=self.generation_task, args=(fragments, voice_info), daemon=True)
        thread.start()

    def generation_task(self, fragments, voice_info):
        """
        Genera fragmentos uno a uno y notifica a la interfaz por cada uno.
        voice_info es una tupla: (tipo, modo, nombre_mostrar, codigo)
        """
        voice_type, _, _, voice_code = voice_info  # desempaquetar
        temp_files = []
        for i, frag in enumerate(fragments):
            if self.generation_cancelled:
                break
            # Generar archivo temporal para este fragmento
            file = self.generate_single_audio(frag, voice_type, voice_code)
            temp_files.append(file)
            # Notificar a la interfaz
            self.root.after(0, self.file_ready_callback, file, i, len(fragments))  # i es 0-based
    
        if self.generation_cancelled:
            from audio_exporter import cleanup_temp_files
            cleanup_temp_files(temp_files)
            self.root.after(0, self.reset_narration_buttons)
        else:
            self.current_temp_files = temp_files
            self.generation_finished = True
            self.root.after(0, self.all_files_generated)

    def generate_single_audio(self, text, voice_type, voice_code):
        """
        Genera un archivo de audio para un fragmento.
        Puede devolver .mp3 o .wav según el motor y disponibilidad de ffmpeg.
        """
        import tempfile
        import asyncio
        import edge_tts
        from system_tts import system_text_to_mp3
    
        # Crear archivo temporal con extensión .mp3 (por defecto)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp.close()
    
        if voice_type == 'edge-tts':
            async def _gen():
                comm = edge_tts.Communicate(text, voice_code)
                await comm.save(temp.name)
            asyncio.run(_gen())
            return temp.name
        else:
            # TTS del sistema: puede devolver .mp3 o .wav
            real_path = system_text_to_mp3(text, voice_code, temp.name)
            # Si devolvió .wav, el archivo temporal .mp3 no se usó; lo borramos
            if real_path != temp.name and os.path.exists(temp.name):
                os.unlink(temp.name)
            return real_path

    def file_ready_callback(self, file, idx, total):
        """Se llama cada vez que un fragmento está listo."""
        self.progress['value'] = idx + 1  # para mostrar progreso 1-based
        self.playback_queue.append((file, idx))   # guardamos tupla
        # Si es el primer archivo y aún no hemos iniciado la reproducción, la iniciamos
        if idx == 0 and self.playing:
            self.status_label.config(text="Reproduciendo...")
            self.root.after(100, self.playback_loop)

    def playback_loop(self):
        """Reproduce los archivos de la cola secuencialmente."""
        if not self.playing:
            return
        if self.playback_queue:
            file, idx = self.playback_queue.pop(0)   # obtener archivo e índice
            self.current_playback_file = file
            self.current_fragment_index = idx
            # Resaltar el fragmento en el texto
            self.highlight_fragment(idx)
            pygame.mixer.init()
            pygame.mixer.music.load(file)
            pygame.mixer.music.play()
            self.root.after(100, self.check_music_end)
        else:
            # Si no hay más archivos pero la generación no ha terminado, esperar
            if not self.generation_finished:
                self.root.after(100, self.playback_loop)
            else:
                # Generación terminada y cola vacía
                if not self.paused and len(self.playback_queue) == 0 and not pygame.mixer.music.get_busy():  # Solo finalizar si no está pausado
                    self.narration_finished()
                else:
                    # Si está pausado, seguir esperando (no hacer nada)
                    self.root.after(100, self.playback_loop)

    def check_music_end(self):
        if not self.playing:
            return
        if pygame.mixer.music.get_busy():
            self.root.after(100, self.check_music_end)
        else:
            if self.paused:
                # No avanzar al siguiente mientras está pausado
                self.root.after(100, self.check_music_end)
                return
            self.current_playback_file = None
            self.pause_position = 0
            self.playback_loop()

    def all_files_generated(self):
        """Se llama cuando la generación ha terminado por completo."""
        if not self.playback_queue and not pygame.mixer.music.get_busy():
            # Si está pausado, no finalizamos todavía
            if not self.paused:
                pass
                #self.narration_finished()
            else:
                # Si está pausado, esperamos a que se reanude y luego verificamos de nuevo
                self.generation_finished = True  # Ya terminó la generación
                # No hacemos nada más, al reanudar se comprobará en playback_loop

    def stop_narration(self):
        #self.toc_tree.config(state=tk.NORMAL)
        # self.chapter_spinbox.config(state='readonly')  # o NORMAL según corresponda
        # self.prev_button.config(state=tk.NORMAL)
        # self.next_button.config(state=tk.NORMAL)
        self.reset_ui_after_stop()
        self.text_area.tag_remove("highlight", "1.0", tk.END)
        self.playing = False
        self.paused = False
        self.generation_cancelled = True
        pygame.mixer.music.stop()
        pygame.mixer.quit()
    
        # Limpiar archivos temporales
        if self.current_temp_files:
            cleanup_temp_files(self.current_temp_files)
            self.current_temp_files = []
        self.playback_queue.clear()
    
        # Restaurar botones
        self.play_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED, text="⏸️ Pausa"  if self.idioma == "es" else "⏸️ Pause")
        self.stop_button.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.status_label.config(text="Narración detenida")

    def narration_finished(self):
        #self.toc_tree.config(state=tk.NORMAL)
        self.chapter_spinbox.config(state='readonly')  # o NORMAL según corresponda
        self.prev_button.config(state=tk.NORMAL)
        self.next_button.config(state=tk.NORMAL)
        self.text_area.tag_remove("highlight", "1.0", tk.END)
        """Se llama cuando la reproducción ha terminado (sin interrupción)."""
        pygame.mixer.quit()
        self.playing = False
        self.paused = False
        self.generation_finished = False
        self.current_playback_file = None
        self.pause_position = 0
    
        self.play_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED, text="⏸️ Pausa"  if self.idioma == "es" else "⏸️ Pause")
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="Narración completada")

        # if self.current_temp_files and messagebox.askyesno(
        #         "Narración completada",
        #         "¿Deseas guardar el audio como archivo MP3?"):
        #     # Sugerir nombre basado en el capítulo actual
        #     chapter_title = self.chapters[self.current_chapter_index][0]
        #     safe_title = self.sanitize_filename(chapter_title)
        #     if not safe_title:
        #         safe_title = "capitulo"
        #     default_filename = f"{safe_title}.mp3"
        #     output = filedialog.asksaveasfilename(
        #         defaultextension=".mp3",
        #         filetypes=[("MP3 files", "*.mp3")],
        #         initialfile=default_filename
        #     )
        #     if output:
        #         self.export_temp_files(self.current_temp_files, output)
        #     else:
        #         cleanup_temp_files(self.current_temp_files)
        # else: 
        cleanup_temp_files(self.current_temp_files)
        self.current_temp_files = []
        self.playback_queue.clear()
        
        # Si la narración fue cancelada (por stop), no continuar
        if self.generation_cancelled:
            self.reset_ui_after_stop()
            return
    
        # Comprobar si hay siguiente capítulo y la opción automática está activada
        if (self.auto_next.get() and 
            self.current_chapter_index < len(self.chapters) - 1):
            
            # Pasar al siguiente capítulo
            self.current_chapter_index += 1
            self.display_chapter(self.current_chapter_index)
            # Narrar automáticamente
            self.narrate_chapter()
        else:
            # No hay más capítulos o no se desea auto-continuar
            self.reset_ui_after_narration()

    def export_temp_files(self, temp_files, output_path):
        """Concatena archivos temporales y guarda el MP3 final."""
        self.status_label.config(text="Combinando archivos..."  if self.idioma == "es" else "Combining files...")
        self.progress['mode'] = 'indeterminate'
        self.progress.start()
        def combine():
            try:
                merge_mp3_files(temp_files, output_path)
                txt = "Éxito", f"Audio guardado en:\n{output_path}"  if self.idioma == "es" else f"Audio saved in:\n{output_path}" 
                self.root.after(0, lambda: messagebox.showinfo("OK", txt))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, self.reset_progress)
                cleanup_temp_files(temp_files)
        threading.Thread(target=combine, daemon=True).start()

    def reset_progress(self):
        self.progress.stop()
        self.progress['mode'] = 'determinate'
        self.progress['value'] = 0
        self.status_label.config(text="Listo")

    def reset_narration_buttons(self):
        self.play_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.DISABLED, text="⏸️ Pausa"   if self.idioma == "es" else "⏸️ Pause")   # <--- AÑADIR
        self.progress['value'] = 0
        self.status_label.config(text="Listo")

    # ---------- Exportación completa por capítulos ----------
    def export_full(self):
        if not self.chapters:
            txt = "Carga un libro primero."  if self.idioma == "es" else "Load a book first."
            messagebox.showinfo("Info", txt)
            return
        voice_info = self.get_selected_voice()
        if not voice_info:
            txt = "Selecciona una voz." if self.idioma == "es" else "Select a voice."
            messagebox.showerror("Error", txt)
            return
    
        # Obtener título del libro para la carpeta
        book_title = self.current_book['title'] if self.current_book and 'title' in self.current_book else "Libro"
        safe_folder = self.sanitize_filename(book_title)
        if not safe_folder:
            safe_folder = "Libro"
    
        root_dir = filedialog.askdirectory(title="Selecciona la carpeta donde guardar el audiolibro"   if self.idioma == "es" else "Select the folder where you want to save the audiobook")
        if not root_dir:
            return
    
        book_dir = os.path.join(root_dir, safe_folder)
        try:
            os.makedirs(book_dir, exist_ok=True)
        except Exception as e:
            txt = "No se pudo crear la carpeta"  if self.idioma == "es" else "The folder could not be created"
            messagebox.showerror("Error", f"{txt}:\n{e}")
            return
    
        total_chapters = len(self.chapters)
        self.status_label.config(text=f"Exportando {total_chapters} capítulos..."  if self.idioma == "es" else f"Exporting {total_chapters} chapters...")
        self.progress['maximum'] = total_chapters
        self.progress['value'] = 0
        self.play_button.config(state=tk.DISABLED)
    
        def chapter_filename(index, title):
            idx_str = f"{index+1:03d}"
            safe_title = self.sanitize_filename(title)
            if not safe_title:
                safe_title = f"capitulo_{idx_str}"
            return f"{idx_str}_{safe_title}.mp3"
    
        def task():
            try:
                for i, (chap_title, chap_text) in enumerate(self.chapters):
                    out_name = chapter_filename(i, chap_title)
                    out_path = os.path.join(book_dir, out_name)
                    if not os.path.exists(out_path):
                        fragments,indices = self.split_text(chap_text)
                        # Usar la función text_to_mp3 con la tupla voice_info
                        temp_files = text_to_mp3(fragments, voice_info, progress_callback=None)
                        out_name = chapter_filename(i, chap_title)
                        out_path = os.path.join(book_dir, out_name)
                        merge_mp3_files(temp_files, out_path)
                        cleanup_temp_files(temp_files)
                    self.root.after(0, lambda i=i: self.progress.config(value=i+1))
                    self.root.after(0, lambda i=i, t=chap_title: self.status_label.config(
                        text=f"Exportado capítulo {i+1}/{total_chapters}: {t[:30]}..."   if self.idioma == "es" else f"Exported chapter {i+1}/{total_chapters}: {t[:30]}..."))
                txt = f"Audiolibro guardado en:\n{book_dir}"   if self.idioma == "es" else  f"Saved Audiobook in:\n{book_dir}"     
                self.root.after(0, lambda: messagebox.showinfo("OK", f"Audiolibro guardado en:\n{book_dir}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, self.reset_narration_buttons)
                self.root.after(0, self.reset_progress)
    
        threading.Thread(target=task, daemon=True).start()

    # ---------- Exportación de un solo capítulo ----------
    def export_chapter(self):
        reptext = self.text_area.get("1.0", tk.END)
        if not self.chapters and reptext== '\n':
            txt = "Carga un libro primero."  if self.idioma == "es" else "Load a book first."
            messagebox.showinfo("Info", txt)
            return
        voice_info = self.get_selected_voice()
        if not voice_info:
            txt = "Selecciona una voz." if self.idioma == "es" else "Select a voice."
            messagebox.showerror("Error", txt)
            return
        
        if self.chapters:
            chapter_title = self.chapters[self.current_chapter_index][0]
            safe_title = self.sanitize_filename(chapter_title)
            if not safe_title:
                safe_title = "capitulo"
                
        else:
            chapter_title = reptext[:11]
            safe_title = self.sanitize_filename(chapter_title)
            if not safe_title:
                safe_title = "Texto"            
        default_filename = f"{safe_title}.mp3"
    
        output = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3 files", "*.mp3")],
            initialfile=default_filename
        )
        if not output:
            return
        if self.chapters:
             _, chapter_text = self.chapters[self.current_chapter_index]
        fragments,indices = self.split_text(reptext)
    
        self.status_label.config(text="Exportando capítulo..." if self.idioma == "es" else "Exporting chapter...")
        self.progress['maximum'] = len(fragments)
        self.progress['value'] = 0
        self.play_button.config(state=tk.DISABLED)
    
        def task():
            try:
                # Aquí pasamos voice_info (tupla)
                temp_files = text_to_mp3(fragments, voice_info, progress_callback=self.update_progress)
                merge_mp3_files(temp_files, output)
                txt = f"Capítulo exportado a:\n{output}" if self.idioma == "es" else  f"Chapter exported to:\n{output}"
                self.root.after(0, lambda: messagebox.showinfo("OK", f"Capítulo exportado a:\n{output}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, self.reset_narration_buttons)
                self.root.after(0, self.reset_progress)
                if 'temp_files' in locals():
                    cleanup_temp_files(temp_files)
    
        threading.Thread(target=task, daemon=True).start()

    def update_progress(self, current, total):
        self.root.after(0, lambda: self.progress.config(value=current))
        
    def toggle_pause(self):
        """Pausa o reanuda la reproducción actual."""
        if not self.playing:
            return
        if self.paused:
            if self.current_playback_file and self.pause_position > 0:
                pygame.mixer.music.load(self.current_playback_file)
                pygame.mixer.music.play(start=self.pause_position / 1000.0)
            else:
                pygame.mixer.music.unpause()
            self.pause_button.config(text="⏸️ Pausa"   if self.idioma == "es" else "⏸️ Pause")
            self.play_button.config(state=tk.DISABLED)
            self.paused = False
            self.status_label.config(text="Reanudado"   if self.idioma == "es" else "Resumed")
        else:
            # Pausar
            if pygame.mixer.music.get_busy():
                self.pause_position = pygame.mixer.music.get_pos()
                pygame.mixer.music.stop()
            self.pause_button.config(text="▶️ Reanudar"   if self.idioma == "es" else "▶️ Resume")
            self.play_button.config(state=tk.NORMAL)
            self.paused = True
            self.status_label.config(text="Pausado"   if self.idioma == "es" else "Paused")
            
    def highlight_fragment(self, idx):
        """Resalta el fragmento con índice idx en el text_area."""
        # Quitar resaltado anterior
        self.text_area.tag_remove("highlight", "1.0", tk.END)
        if 0 <= idx < len(self.fragment_indices):
            start, end = self.fragment_indices[idx]
            # Convertir posiciones de caracteres a índices de Tkinter
            # Tkinter usa "line.char", así que necesitamos mapear. Como el texto está completo,
            # podemos usar la función index que convierte posición de caracter a "line.char".
            # Para simplificar, usaremos el método de búsqueda: marcar desde "1.0" + start chars hasta "1.0" + end+1 chars.
            start_idx = f"1.0 + {start} chars"
            end_idx = f"1.0 + {end + 1} chars"
            self.text_area.tag_add("highlight", start_idx, end_idx)
            # Opcional: hacer scroll para que el fragmento sea visible
            self.text_area.see(end_idx)
            
    def reset_ui_after_stop(self):
        """Restaura la interfaz después de una detención manual."""
        self.chapter_spinbox.config(state='readonly')
        self.prev_button.config(state=tk.NORMAL)
        self.next_button.config(state=tk.NORMAL)
        self.play_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED, text="⏸️ Pausa"   if self.idioma == "es" else "⏸️ Pause")
        self.stop_button.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.status_label.config(text="Narración detenida")
    
    def reset_ui_after_narration(self):
        """Restaura la interfaz después de completar la narración (sin más capítulos)."""
        self.chapter_spinbox.config(state='readonly')
        self.prev_button.config(state=tk.NORMAL)
        self.next_button.config(state=tk.NORMAL)
        self.play_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED, text="⏸️ Pausa"   if self.idioma == "es" else "⏸️ Pause")
        self.stop_button.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.status_label.config(text="Narración completada")
        
    def show_help(self):
        """Muestra una ventana con instrucciones básicas de uso."""
        help_textES = (
            "BookVoice Reader - Guía rápida\n\n"
            "1. Abre un archivo EPUB con 'Archivo > Abrir EPUB'.\n"
            "2. Selecciona una voz del desplegable (online o offline).\n"
            "   - Para mejores resultados utilice una voz del idioma del libro a leer.\n"
            "3. Usa los botones de navegación (anterior/siguiente) o haz clic en el índice para ir a un capítulo.\n"
            "4. Presiona 'Narrar capítulo' para escuchar el capítulo actual.\n"
            "   - Puedes pausar/reanudar con el botón de pausa.\n"
            "   - Puedes detener con el botón 'Detener'.\n"
            "En caso de que el capitulo tenga imagenes, se activa el boton 'Ver Ilustraciones'.\n"
            "5. Exporta el libro completo (cada capítulo como MP3) o el capítulo actual a un solo MP3.\n"
            "   - Para exportar a audio es necesario tener instalado ffmpeg'.\n"
            "6. La opción 'Reproducir siguiente capítulo automáticamente' (si está activada) pasará al siguiente al terminar.\n\n"
            "Nota: El modo offline usa el TTS del sistema (calidad inferior). El modo online requiere conexión a Internet."
        )
        help_textEN = (
            "BookVoice Reader - Quick Guide\n\n"
            "1. Open an EPUB file with 'File > Open EPUB'.\n"
            "2. Select a voice from the dropdown (online or offline).\n"
            "   - For best results, use a voice in the language of the book being read.\n"
            "3. Use the navigation buttons (previous/next) or click on the table of contents to go to a chapter.\n"
            "4. Press 'Narrate chapter' to listen to the current chapter.\n"
            "   - You can pause/resume with the pause button.\n"
            "   - You can stop with the 'Stop' button.\n"
            "If the chapter has images, the 'View Illustrations' button becomes active.\n"
            "5. Export the entire book (each chapter as MP3) or the current chapter as a single MP3.\n"
            " - To export to audio, you need to have ffmpeg installed.\n"
            "6. The 'Play next chapter automatically' option (if enabled) will move to the next chapter when finished.\n\n"
            "Note: Offline mode uses the system TTS (lower quality). Online mode requires an internet connection."
        )
        txt = "Ayuda de BookVoice Reader"   if self.idioma == "es" else  "BookVoice Reader Help"
        help_text = help_textES if self.idioma == "es" else  help_textEN
        messagebox.showinfo(txt, help_text)
    
    def show_about(self):
        """Muestra información sobre la aplicación y el autor."""
        about_textES = (
            "BookVoice Reader versión 3.0\n\n"
            "Creador: Ray R. Hall Mejias\n"
            "Correo: rayhall8805@gmail.com\n"  # Reemplaza con el correo real
            "Telegram: @ErinCuba\n\n"  # Reemplaza con el usuario real
            "Aplicación gratuita para leer y narrar libros EPUB.\n"
            "Utiliza edge-tts para síntesis de voz online y TTS del sistema como respaldo offline."
        )
        about_textEN = (
            "BookVoice Reader version 3.1\n\n"
            "Creator: Ray R. Hall Mejias\n"
            "Email: rayhall8805@gmail.com\n"
            "Telegram: @ErinCuba\n\n"
            "Free application for reading and narrating EPUB books.\n"
            "Uses edge-tts for online voice synthesis and system TTS as offline backup."
        )
        txt = "Acerca de BookVoice Reader"  if self.idioma == "es" else  "About BookVoice Reader"
        about_text = about_textES  if self.idioma == "es" else  about_textEN
        messagebox.showinfo(txt, about_text)
        
    def show_images(self):
        if not self.chapter_images or self.current_chapter_index >= len(self.chapter_images):
            return
        images = self.chapter_images[self.current_chapter_index]
        if not images:
            return
    
        top = tk.Toplevel(self.root)
        top.title("Ilustraciones del capítulo")
        top.geometry("400x500")
        top.transient(self.root)
    
        current_idx = tk.IntVar(value=0)
    
        # Frame principal
        main_frame = ttk.Frame(top, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
    
        # Canvas para mostrar la imagen (con scrollbars)
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
    
        canvas = tk.Canvas(canvas_frame, bg='white')
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=canvas.xview)
        canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
    
        canvas.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
    
        # Frame interior para contener la imagen (para que el canvas la escale)
        inner_frame = ttk.Frame(canvas)
        canvas.create_window((0,0), window=inner_frame, anchor='nw')
    
        # Label para la imagen dentro del inner_frame
        img_label = ttk.Label(inner_frame)
        img_label.pack()
    
        # Frame para botones de navegación
        nav_frame = ttk.Frame(main_frame)
        nav_frame.pack(fill=tk.X, pady=10)
    
        # Función para actualizar la imagen
        def update_image():
            idx = current_idx.get()
            if 0 <= idx < len(images):
                img_data = images[idx]['data']
                try:
                    from PIL import Image, ImageTk
                    import io
                    pil_img = Image.open(io.BytesIO(img_data))
                    # Obtener tamaño del canvas (o un tamaño máximo)
                    canvas_width = canvas.winfo_width() - 20
                    canvas_height = canvas.winfo_height() - 20
                    if canvas_width > 10 and canvas_height > 10:
                        # Redimensionar manteniendo proporción
                        pil_img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
                    else:
                        # Si el canvas no tiene tamaño, usar un máximo
                        pil_img.thumbnail((600, 500), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(pil_img)
                    img_label.config(image=photo)
                    img_label.image = photo
                    # Actualizar scroll region
                    inner_frame.update_idletasks()
                    canvas.config(scrollregion=canvas.bbox('all'))
                except Exception as e:
                    img_label.config(text=f"Error: {e}")
            # Actualizar botones
            prev_btn.config(state=tk.NORMAL if idx > 0 else tk.DISABLED)
            next_btn.config(state=tk.NORMAL if idx < len(images)-1 else tk.DISABLED)
            counter_label.config(text=f"Imagen {idx+1} de {len(images)}")
    
        # Botones
        prev_btn = ttk.Button(nav_frame, text="◀ Anterior", 
                             command=lambda: current_idx.set(current_idx.get()-1) or update_image())
        prev_btn.pack(side=tk.LEFT, padx=5)
    
        next_btn = ttk.Button(nav_frame, text="Siguiente ▶", 
                             command=lambda: current_idx.set(current_idx.get()+1) or update_image())
        next_btn.pack(side=tk.LEFT, padx=5)
    
        counter_label = ttk.Label(nav_frame, text="")
        counter_label.pack(side=tk.LEFT, padx=20)
    
        # Botón para cerrar
        ttk.Button(nav_frame, text="Cerrar", command=top.destroy).pack(side=tk.RIGHT, padx=5)
    
        # Vincular evento de redimensionamiento para ajustar la imagen
        def on_resize(event):
            update_image()
        canvas.bind('<Configure>', on_resize)
    
        # Mostrar primera imagen
        current_idx.set(0)
        update_image()
        
    def show_donation(self):
        """Muestra ventana con QR de donación."""
        # Crear ventana emergente
        top = tk.Toplevel(self.root)
        txt = "Apoya el proyecto BookVoice Reader"   if self.idioma == "es" else "Support the BookVoice Reader project"
        top.title(txt)
        top.geometry("450x550")
        top.resizable(False, False)
        top.transient(self.root)
        top.grab_set()  # Modal relativo
    
        # Frame principal con padding
        main_frame = ttk.Frame(top, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
    
        # Texto de presentación
        intro_textES = (
            "¡Gracias por considerar una donación!\n\n"
            "Tu apoyo ayuda a mantener y mejorar BookVoice Reader, "
            "un proyecto de código abierto dedicado a hacer la lectura "
            "accesible para todos."
        )
        intro_textEN = (
            "Thank you for considering a donation!\n\n"
            "Your support helps maintain and improve BookVoice Reader, "
            "an open-source project dedicated to making reading "
            "accessible to everyone"
        )
        intro_text = intro_textES   if self.idioma == "es" else intro_textEN
        ttk.Label(main_frame, text=intro_text, justify=tk.CENTER, wraplength=400).pack(pady=(0, 20))
    
        # Cargar y mostrar la imagen QR
        img_path = resource_path('donar.png')
        if os.path.exists(img_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(img_path)
                # Redimensionar manteniendo proporción
                img.thumbnail((300, 300))
                photo = ImageTk.PhotoImage(img)
                label_img = ttk.Label(main_frame, image=photo)
                label_img.image = photo  # mantener referencia
                label_img.pack(pady=10)
            except Exception as e:
                ttk.Label(main_frame, text=f"Error al cargar la imagen:\n{str(e)}", foreground="red").pack()
        else:
            ttk.Label(main_frame, text="No se encontró el archivo 'donar.png' en la raíz del proyecto.",
                      foreground="red").pack()
    
        # Dirección Bitcoin (texto alternativo)
        txt = "O si lo prefieres, puedes enviar Bitcoin a esta dirección"   if self.idioma == "es" else "Or if you prefer, you can send Bitcoin to this address"
        bitcoin_text = (
            f"{txt}:\n"
            "bc1qgcxkczwcl8gpfl2t9v5mjmnszyckgz2kew95nt"
        )
        ttk.Label(main_frame, text=bitcoin_text, justify=tk.CENTER, wraplength=400).pack(pady=20)
    
        # Botón de cerrar
        ttk.Button(main_frame, text="Cerrar", command=top.destroy).pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = BookVoiceReader(root)
    root.mainloop()