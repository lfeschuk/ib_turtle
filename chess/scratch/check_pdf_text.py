import pypdf

reader = pypdf.PdfReader('/Users/lfesch/work_files/chess/pages_170_178.pdf')
print("Total pages:", len(reader.pages))
for i, page in enumerate(reader.pages):
    print(f"--- Page {i+1} ---")
    print(page.extract_text()[:200]) # Print first 200 chars
