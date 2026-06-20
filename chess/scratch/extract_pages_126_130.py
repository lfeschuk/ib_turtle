import pypdf

def extract_pages(input_pdf, output_pdf, start_page, end_page):
    # start_page and end_page are 1-based indices
    reader = pypdf.PdfReader(input_pdf)
    writer = pypdf.PdfWriter()
    
    # 0-based indices for pypdf
    for page_num in range(start_page - 1, end_page):
        if page_num < len(reader.pages):
            writer.add_page(reader.pages[page_num])
            
    with open(output_pdf, "wb") as f:
        writer.write(f)
    print(f"Extracted pages {start_page} to {end_page} to {output_pdf}")

if __name__ == "__main__":
    extract_pages(
        "/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf",
        "/Users/lfesch/work_files/chess/scratch/pages_126_130.pdf",
        126,
        130
    )
