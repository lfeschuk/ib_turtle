import pypdf

reader = pypdf.PdfReader('/Users/lfesch/work_files/chess/pages_170_178.pdf')
for i, page in enumerate(reader.pages):
    print(f"Page {i+1} has {len(page.images)} images")
    for j, img in enumerate(page.images):
        print(f"  Image {j+1}: {img.name}")
