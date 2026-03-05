import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import os

def extract_epub_content(epub_path):
    print("🔍 Abriendo EPUB con ebooklib...")
    book = epub.read_epub(epub_path)
    print("✅ EPUB abierto correctamente")

    print("📋 Extrayendo metadatos...")
    title = book.get_metadata('DC', 'title')
    title = title[0][0] if title else 'Sin título'
    author = book.get_metadata('DC', 'creator')
    author = author[0][0] if author else 'Desconocido'
    idioma = book.get_metadata('DC', 'language')
    idioma = idioma[0][0] if idioma else ''
    print(f"   Título: {title}, Autor: {author}")

    print("📑 Procesando tabla de contenidos...")
    toc = []
    for item in book.toc:
        if isinstance(item, tuple):
            for link in item:
                if hasattr(link, 'href') and hasattr(link, 'title'):
                    toc.append({'title': link.title, 'href': link.href})
        elif hasattr(item, 'href') and hasattr(item, 'title'):
            toc.append({'title': item.title, 'href': item.href})
    print(f"   {len(toc)} elementos en TOC")

    # Crear un diccionario para acceder rápidamente a los ítems por nombre
    items_dict = {item.get_name(): item for item in book.get_items()}

    print("📄 Extrayendo capítulos...")
    chapters = []
    chapter_images = []  # lista de listas, cada elemento será [{'name': ..., 'data': ..., 'media_type': ...}]
    items = list(book.get_items())
    print(f"   Total de items: {len(items)}")
    for idx, item in enumerate(items):
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            print(f"   Procesando documento {idx+1}/{len(items)}: {item.get_name()}")
            chapter_title = None
            for t in toc:
                if t['href'] == item.get_name():
                    chapter_title = t['title']
                    break
            if not chapter_title:
                chapter_title = item.get_name()

            soup = BeautifulSoup(item.get_body_content(), 'html.parser')
            for tag in soup(['script', 'style']):
                tag.decompose()

            # Extraer imágenes de este capítulo
            images_in_chapter = []
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src')
                if src:
                    # Buscar ítem de imagen
                    # Primero intentar con src completo
                    found_item = items_dict.get(src)
                    if not found_item:
                        # Intentar con el nombre base del archivo
                        img_name = os.path.basename(src)
                        for key, val in items_dict.items():
                            if key.endswith(img_name):
                                found_item = val
                                break
                    if found_item and found_item.get_type() == ebooklib.ITEM_IMAGE:
                        images_in_chapter.append({
                            'name': found_item.get_name(),
                            'data': found_item.get_content(),
                            'media_type': found_item.media_type
                        })

            chapter_images.append(images_in_chapter)
            
            # Extraer texto con separador de línea para conservar estructura
            text = soup.get_text(separator='\n')
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            # Unir líneas con doble salto para separar párrafos
            clean_text = '\n\n'.join(lines)

            if clean_text:
                chapters.append((chapter_title, clean_text))
                print(f"      → Capítulo añadido: {chapter_title[:50]}...")
    print(f"✅ Extracción completada. {len(chapters)} capítulos obtenidos.")
    dicc = {
        'title': title,
        'author': author,
        'toc': toc,
        'chapters': chapters,
        'chapter_images': chapter_images,
        'language': idioma,
    }
    return dicc