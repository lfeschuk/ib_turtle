import pypdf

reader = pypdf.PdfReader('Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf')
print(f"Total pages: {len(reader.pages)}")

# Search for "Hohler"
for idx, page in enumerate(reader.pages):
    text = page.extract_text()
    if "Hohler" in text:
        print(f"Found 'Hohler' on PDF page {idx + 1}") # 1-indexed

# Search for "Game 39"
for idx, page in enumerate(reader.pages):
    text = page.extract_text()
    if "Game 39" in text:
        print(f"Found 'Game 39' on PDF page {idx + 1}") # 1-indexed
