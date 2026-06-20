import pypdf

reader = pypdf.PdfReader('Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf')
print(f"Total pages: {len(reader.pages)}")

extracted_text = ""
# Pages 146 to 150 (indices 145 to 149 inclusive)
for page_num in range(145, 150):
    page = reader.pages[page_num]
    text = page.extract_text()
    extracted_text += f"=== PDF PAGE {page_num + 1} ===\n"
    extracted_text += text + "\n\n"

with open('scratch/extracted_146_150.txt', 'w', encoding='utf-8') as f:
    f.write(extracted_text)

print("Extraction done. Written to scratch/extracted_146_150.txt")
