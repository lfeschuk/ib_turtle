import pypdf

reader = pypdf.PdfReader('/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf')
writer = pypdf.PdfWriter()

# Physical pages 119 and 120 are indices 118, 119
for page_num in range(118, 120):
    writer.add_page(reader.pages[page_num])

output_pdf = '/Users/lfesch/work_files/chess/scratch/pages_119_120.pdf'
with open(output_pdf, 'wb') as f:
    writer.write(f)

print(f"Extracted physical pages 119 to 120 to {output_pdf}")
