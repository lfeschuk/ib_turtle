import fitz
import os

pdf_path = "/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf"
if not os.path.exists(pdf_path):
    print(f"Error: {pdf_path} does not exist.")
    exit(1)

doc = fitz.open(pdf_path)

print("Searching for 'Exercise 8'...")
found = False
for page_num in range(len(doc)):
    page = doc.load_page(page_num)
    text = page.get_text()
    if "Exercise 8" in text or "exercise 8" in text:
        print(f"Found on page {page_num + 1}")
        found = True
        # Print context
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "Exercise 8" in line or "exercise 8" in line:
                start = max(0, i - 2)
                end = min(len(lines), i + 10)
                print(f"Context (Page {page_num + 1}):")
                for j in range(start, end):
                    print(f"  {lines[j]}")
                print("-" * 20)

if not found:
    print("Not found in text. The PDF might be partially scanned or the text is different.")
