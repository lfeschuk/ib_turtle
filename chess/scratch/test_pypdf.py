import pypdf

reader = pypdf.PdfReader('/Users/lfesch/work_files/chess/pages_56_60.pdf')
print(f"Total pages: {len(reader.pages)}")
for i, page in enumerate(reader.pages):
    text = page.extract_text()
    print(f"Page {i+1} length: {len(text)}")
    print(text[:100])
