import fitz # PyMuPDF
import sys

doc = fitz.open('/Users/lfesch/work_files/chess/pages_170_178.pdf')
print("Total pages:", len(doc))

for i in range(len(doc)):
    page = doc.load_page(i)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Zoom 2x for better OCR
    output = f"/Users/lfesch/work_files/chess/scratch/page_{170 + i}.png"
    pix.save(output)
    print(f"Saved {output}")
