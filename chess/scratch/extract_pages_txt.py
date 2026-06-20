import pypdf

pdf_path = '/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf'
output_path = '/Users/lfesch/work_files/chess/scratch/extracted_pages_120_135.txt'

reader = pypdf.PdfReader(pdf_path)
num_pages = len(reader.pages)
print(f"Total pages: {num_pages}")

start_page = 120 # 0-indexed (page 121)
end_page = 135   # 0-indexed (page 136)

with open(output_path, 'w', encoding='utf-8') as f:
    for page_num in range(start_page, min(end_page + 1, num_pages)):
        page = reader.pages[page_num]
        text = page.extract_text()
        f.write(f"--- PDF Page {page_num + 1} ---\n")
        f.write(text)
        f.write("\n\n")

print(f"Extracted pages {start_page+1} to {end_page+1} to {output_path}")
