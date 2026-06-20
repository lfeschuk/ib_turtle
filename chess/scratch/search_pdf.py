import pypdf
import re

def search_pdf(filename, pattern):
    print(f"Searching for '{pattern}' in {filename}...")
    reader = pypdf.PdfReader(filename)
    num_pages = len(reader.pages)
    results = []
    for i in range(num_pages):
        page = reader.pages[i]
        text = page.extract_text()
        if text:
             # print(f"Page {i+1} has {len(text)} chars")
             pass
        else:
             print(f"Page {i+1} has NO text!")
        if re.search(pattern, text, re.IGNORECASE):
            results.append(i + 1) # 1-indexed page number
    return results


pdf_path = '/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf'
pages_ex3 = search_pdf(pdf_path, 'Exercise 3')
print(f"Found 'Exercise 3' on pages: {pages_ex3}")

pages_ex8 = search_pdf(pdf_path, 'Exercise 8')
print(f"Found 'Exercise 8' on pages: {pages_ex8}")

pages_sol = search_pdf(pdf_path, 'Solution to Exercises')
print(f"Found 'Solution to Exercises' on pages: {pages_sol}")
