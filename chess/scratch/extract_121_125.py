import pypdf

reader = pypdf.PdfReader('/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf')
writer = pypdf.PdfWriter()

# Physical pages 121 to 125 are indices 120 to 124 (0-indexed)
# Let's extract 120, 121, 122, 123, 124
for page_num in range(120, 125):
    writer.add_page(reader.pages[page_num])

output_pdf = '/Users/lfesch/work_files/chess/scratch/pages_121_125.pdf'
with open(output_pdf, 'wb') as f:
    writer.write(f)

print(f"Extracted physical pages 121 to 125 to {output_pdf}")
