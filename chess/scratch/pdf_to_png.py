import fitz

doc = fitz.open("Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf")

pages_to_render = [96, 97, 98, 99, 100]

for p in pages_to_render:
    page_idx = p - 1 # 0-indexed
    page = doc.load_page(page_idx)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Zoom in for better OCR
    out_path = f"scratch/page_{p}.png"
    pix.save(out_path)
    print(f"Rendered page {p} to {out_path}")
