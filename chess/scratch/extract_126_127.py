import pypdf

reader = pypdf.PdfReader('/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf')
writer = pypdf.PdfWriter()

# Physical pages 126 and 127 are indices 125, 126
for page_num in range(125, 127):
    writer.add_page(reader.pages[page_num])

output_pdf = '/Users/lfesch/work_files/chess/scratch/pages_126_127.pdf'
with open(output_pdf, 'wb') as f:
    writer.write(f)

print(f"Extracted physical pages 126 to 127 to {output_pdf}")
