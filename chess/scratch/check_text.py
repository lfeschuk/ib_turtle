import pypdf

reader = pypdf.PdfReader('Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf')
page = reader.pages[100] # PDF page 101 (0-indexed)
text = page.extract_text()
print(f"Text length on page 101: {len(text)}")
if len(text) > 0:
    print("Sample text:")
    print(text[:200])
else:
    print("No text extracted. PDF might be scanned images.")
