import pypdf

reader = pypdf.PdfReader('/Users/lfesch/work_files/chess/Starting_Out_The_Kings_Indian_Joe_z_library_sk,_1lib_sk,.pdf')

# Print page labels if any
try:
    print("Page labels:", reader.page_labels)
except Exception as e:
    print("Error getting page labels:", e)

# Print metadata
print("Metadata:", reader.metadata)
