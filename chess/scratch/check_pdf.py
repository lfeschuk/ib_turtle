import pypdf

reader = pypdf.PdfReader('/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf')
print("Total pages in PDF:", len(reader.pages))

# Let's extract pages around 90-100 (1-based index)
# which would be 0-based indices 85 to 105
for i in range(85, 105):
    page = reader.pages[i]
    text = page.extract_text()
    first_few_lines = "\n".join(text.split("\n")[:5])
    last_few_lines = "\n".join(text.split("\n")[-5:])
    print(f"--- PDF Page {i+1} (0-indexed {i}) ---")
    print("FIRST LINES:")
    print(first_few_lines)
    print("LAST LINES:")
    print(last_few_lines)
    print("----------------------------------\n")
