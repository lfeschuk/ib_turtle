import pypdf

reader = pypdf.PdfReader("/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf")
print("Total pages:", len(reader.pages))

for idx in range(65, 95):
    page = reader.pages[idx]
    text = page.extract_text()
    # Find lines containing numbers at the bottom or top
    lines = text.strip().split("\n")
    if lines:
        print(f"Physical page {idx + 1}: first line={repr(lines[0])}, last line={repr(lines[-1])}")
