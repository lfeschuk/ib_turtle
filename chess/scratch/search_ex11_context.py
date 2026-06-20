import pypdf
import re

def search_pdf(filename, pattern):
    reader = pypdf.PdfReader(filename)
    num_pages = len(reader.pages)
    results = []
    for i in range(num_pages):
        page = reader.pages[i]
        text = page.extract_text()
        if text and re.search(pattern, text, re.IGNORECASE):
            results.append(i + 1)
    return results

pdf_path = '/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf'

# Search for potential keywords from Solution 11
keywords = ['Nxg5', 'Bxh5', 'Qh7']
for kw in keywords:
    pages = search_pdf(pdf_path, kw)
    print(f"Found '{kw}' on pages: {pages}")
