import fitz
import os

pdf_path = "/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf"
if not os.path.exists(pdf_path):
    print(f"Error: {pdf_path} does not exist.")
    exit(1)

doc = fitz.open(pdf_path)
pages_to_render = [131, 132, 133, 134, 135]

for p in pages_to_render:
    page_idx = p - 1 # 0-indexed
    if page_idx < 0 or page_idx >= len(doc):
        print(f"Error: Page {p} is out of range.")
        continue
    page = doc.load_page(page_idx)
    # Use Matrix(2, 2) to zoom in 2x for better readability/OCR
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    out_path = f"/Users/lfesch/work_files/chess/scratch/page_{p}.png"
    pix.save(out_path)
    print(f"Rendered page {p} to {out_path}")
