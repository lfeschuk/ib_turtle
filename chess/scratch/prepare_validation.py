with open("validate_parsed_pages.ts", "r") as f:
    content = f.read()

# Replace file path
content = content.replace(
    "const filePath = '/Users/lfesch/work_files/chess/parsed_pages_56_60.json';",
    "const filePath = '/Users/lfesch/work_files/chess/parsed_pages_96_100.json';"
)

content = content.replace(
    'parsed_pages_56_60.json',
    'parsed_pages_96_100.json'
)

with open("scratch/validate_96_100.ts", "w") as f:
    f.write(content)

print("Validation script copied and modified.")
