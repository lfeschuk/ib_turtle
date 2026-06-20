import pypdf
import sys

def extract_pages(input_pdf, output_pdf, start_page, end_page):
    reader = pypdf.PdfReader(input_pdf)
    writer = pypdf.PdfWriter()
    
    # start_page and end_page are 1-indexed.
    # Convert to 0-indexed: start_page-1 to end_page
    for i in range(start_page - 1, end_page):
        if i < len(reader.pages):
            writer.add_page(reader.pages[i])
            
    with open(output_pdf, 'wb') as f:
        writer.write(f)
    print(f"Extracted pages {start_page} to {end_page} into {output_pdf}")

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python3 extract_pages.py <input.pdf> <output.pdf> <start_page> <end_page>")
        sys.exit(1)
    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]
    start_page = int(sys.argv[3])
    end_page = int(sys.argv[4])
    extract_pages(input_pdf, output_pdf, start_page, end_page)
