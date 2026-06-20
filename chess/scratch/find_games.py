import pypdf

reader = pypdf.PdfReader("/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf")

for idx, page in enumerate(reader.pages):
    text = page.extract_text()
    if "Mariano" in text or "Cvitan" in text:
        print(f"Mariano vs Cvitan found on physical page {idx + 1}")
    if "Ljubojevic" in text or "Kasparov" in text:
        print(f"Ljubojevic vs Kasparov found on physical page {idx + 1}")
