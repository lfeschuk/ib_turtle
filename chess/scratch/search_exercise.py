import fitz

doc = fitz.open("Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf")

for page_num in range(len(doc)):
    page = doc.load_page(page_num)
    text = page.get_text()
    if "Exercise 6" in text or "exercise 6" in text:
        print(f"Found on page {page_num + 1}")
        # Print some context
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "Exercise 6" in line or "exercise 6" in line:
                start = max(0, i - 2)
                end = min(len(lines), i + 5)
                print(f"Context (Page {page_num + 1}):")
                for j in range(start, end):
                    print(f"  {lines[j]}")
                print("-" * 20)
