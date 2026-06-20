import pypdf

reader = pypdf.PdfReader('/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf')
print("Total pages:", len(reader.pages))

# Physical pages 121 to 125 (0-indexed: 120 to 124)
for page_num in range(120, 125):
    print(f"\n--- Physical Page {page_num + 1} ---")
    page = reader.pages[page_num]
    print(page.extract_text())
