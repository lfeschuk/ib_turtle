from pypdf import PdfReader, PdfWriter

reader = PdfReader('/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf')
writer = PdfWriter()

# PDF pages 106 to 110 (1-indexed) -> 105 to 109 (0-indexed)
for page_num in range(105, 110):
    writer.add_page(reader.pages[page_num])

with open('/Users/lfesch/work_files/chess/scratch/pages_106_110.pdf', 'wb') as f:
    writer.write(f)

print("PDF pages 106-110 extracted successfully to scratch/pages_106_110.pdf")
