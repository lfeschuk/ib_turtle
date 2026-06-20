import fitz # PyMuPDF

pdf_path = '/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf'
doc = fitz.open(pdf_path)

# Page 176 (0-indexed 175)
page = doc.load_page(175)
text = page.get_text()

print("--- Page 176 Text (PyMuPDF) ---")
if text.strip():
    print(text[:500]) # Print first 500 chars
else:
    print("NO TEXT EXTRACTED")
