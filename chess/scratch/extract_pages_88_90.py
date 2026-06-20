import pypdf

reader = pypdf.PdfReader('/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf')
writer = pypdf.PdfWriter()

# Pages 88 to 90 inclusive (indices 88 to 90)
for idx in range(88, 91):
    writer.add_page(reader.pages[idx])

with open('/Users/lfesch/work_files/chess/scratch/pages_88_90.pdf', 'wb') as f:
    writer.write(f)

print("Created scratch/pages_88_90.pdf successfully.")
