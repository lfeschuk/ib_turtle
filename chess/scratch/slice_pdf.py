import pypdf
import sys

def slice_pdf(input_path, output_path, start_page, end_page):
    """
    Slices a PDF from start_page to end_page (1-indexed, inclusive).
    """
    reader = pypdf.PdfReader(input_path)
    writer = pypdf.PdfWriter()
    
    # start_page to end_page (1-indexed) -> (start_page - 1) to (end_page) 0-indexed
    for i in range(start_page - 1, end_page):
        if i < len(reader.pages):
            writer.add_page(reader.pages[i])
            
    with open(output_path, "wb") as f:
        writer.write(f)
    print(f"Successfully sliced pages {start_page} to {end_page} into {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python slice_pdf.py <input> <output> <start_page> <end_page>")
    else:
        slice_pdf(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
