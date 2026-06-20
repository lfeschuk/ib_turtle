import pypdf

reader = pypdf.PdfReader('Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf')
writer = pypdf.PdfWriter()

# PDF pages 101 to 105 are 0-indexed: 100 to 104
for page_num in range(100, 105):
    writer.add_page(reader.pages[page_num])

with open('scratch/pages_101_105.pdf', 'wb') as f:
    writer.write(f)

print("Split PDF saved to scratch/pages_101_105.pdf")
