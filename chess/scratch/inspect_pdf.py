import pypdf

reader = pypdf.PdfReader('/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf')
page = reader.pages[135]
print("Images on page:", len(page.images))
print("Fonts on page:", page._get_fonts())
contents = page.get_contents()
print("Contents:", contents)
if contents:
    print("Contents data preview:", repr(contents.get_data()[:200]))
