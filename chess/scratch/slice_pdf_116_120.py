import pypdf

pdf_path = '/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf'
output_pdf_path = '/Users/lfesch/work_files/chess/scratch/pages_116_120.pdf'

reader = pypdf.PdfReader(pdf_path)
writer = pypdf.PdfWriter()

# PDF Page 117 is index 116 (0-indexed)
# PDF Page 121 is index 120 (0-indexed)
# So we want indices 116, 117, 118, 119, 120 (5 pages total)
start_page_idx = 116
end_page_idx = 121 # exclusive in range

for i in range(start_page_idx, end_page_idx):
    writer.add_page(reader.pages[i])

with open(output_pdf_path, 'wb') as f:
    writer.write(f)

print(f"Successfully sliced pages {start_page_idx+1} to {end_page_idx} (indices {start_page_idx}-{end_page_idx-1}) to {output_pdf_path}")
