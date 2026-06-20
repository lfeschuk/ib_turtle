import fitz # PyMuPDF

pdf_path = '/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf'
output_path = '/Users/lfesch/work_files/chess/scratch/pages_116_120_fitz.txt'

doc = fitz.open(pdf_path)
print(f"Total pages (fitz): {len(doc)}")

# Pages 116 to 120 (1-indexed) are indices 115 to 119 (0-indexed)
# Let's extract indices 114 to 120 (pages 115 to 121)
start_page = 114
end_page = 121

with open(output_path, 'w', encoding='utf-8') as f:
    for i in range(start_page, end_page):
        if i < len(doc):
            f.write(f"--- PDF Page {i+1} (Index {i}) ---\n")
            page = doc[i]
            f.write(page.get_text())
            f.write("\n\n")

print(f"Extracted pages {start_page+1} to {end_page} to {output_path}")
