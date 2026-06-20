import fitz  # PyMuPDF

def render_pages(pdf_path, start_page, end_page, output_dir):
    # start_page and end_page are 1-based
    doc = fitz.open(pdf_path)
    for page_num in range(start_page - 1, min(end_page, len(doc))):
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        output_path = f"{output_dir}/page_{page_num + 1}.png"
        pix.save(output_path)
        print(f"Rendered page {page_num + 1} to {output_path}")

if __name__ == "__main__":
    render_pages(
        "/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf",
        122,
        125,
        "/Users/lfesch/work_files/chess/scratch"
    )
