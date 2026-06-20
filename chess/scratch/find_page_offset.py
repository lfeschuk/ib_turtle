import pypdf

reader = pypdf.PdfReader('/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf')
print(f"Total pages: {len(reader.pages)}")

# Print page numbers and some text snippet for pages 155 to 175 (0-indexed)
for i in range(150, 180):
    if i < len(reader.pages):
        text = reader.pages[i].extract_text()
        first_few_lines = "\n".join(text.split("\n")[:3])
        last_few_lines = "\n".join(text.split("\n")[-3:])
        print(f"--- PDF Page {i} (1-indexed: {i+1}) ---")
        print("START:")
        print(first_few_lines)
        print("END:")
        print(last_few_lines)
        print("-" * 40)
