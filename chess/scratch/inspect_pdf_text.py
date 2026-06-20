import pypdf

reader = pypdf.PdfReader('/Users/lfesch/work_files/chess/pages_56_60.pdf')
print("Total pages in split PDF:", len(reader.pages))

for idx in range(len(reader.pages)):
    text = reader.pages[idx].extract_text()
    print(f"Page {idx+1}: text length = {len(text)}, repr = {repr(text[:100])}")
