import fitz  # PyMuPDF
import cv2
import numpy as np

def load_pdf(path):
    """Loads a PDF file."""
    try:
        doc = fitz.open(path)
        return doc
    except Exception as e:
        print(f"Error loading PDF: {e}")
        return None

def get_page_image(page):
    """Renders a PDF page as an OpenCV image."""
    pix = page.get_pixmap()
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    if pix.n == 4:  # RGBA
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:  # RGB
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    return img

def get_vector_data(page):
    """Extracts vector drawings and text from the page."""
    # Extract text blocks
    text_blocks = page.get_text("dict")["blocks"]
    
    # Extract drawings (lines, rectangles, etc.)
    drawings = page.get_drawings()
    
    return {
        "text_blocks": text_blocks,
        "drawings": drawings
    }

