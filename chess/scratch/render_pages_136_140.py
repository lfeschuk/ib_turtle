import fitz  # PyMuPDF
import os

pdf_path = "/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf"
output_dir = "/Users/lfesch/work_files/chess/scratch"

doc = fitz.open(pdf_path)
print(f"Total pages: {len(doc)}")

# Render physical pages 136 to 140 (0-indexed indices 135 to 139)
for idx in range(135, 140):
    page = doc.load_page(idx)
    zoom = 2.5  # slightly higher resolution for better OCR
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    output_path = os.path.join(output_dir, f"page_{idx + 1}.png")
    pix.save(output_path)
    print(f"Rendered and saved {output_path}")
