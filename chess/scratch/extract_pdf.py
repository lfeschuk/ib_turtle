import pypdf

reader = pypdf.PdfReader("/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf")
print("Total pages:", len(reader.pages))

for i in range(10, 20):
    page = reader.pages[i]
    text = page.extract_text()
    if text:
        print(f"Page {i+1} has text: {len(text)} chars")
    else:
        print(f"Page {i+1} has NO text")
