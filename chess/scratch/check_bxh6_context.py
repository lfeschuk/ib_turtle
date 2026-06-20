import os

files_to_check = [
    'parsed_pages_91_95.json',
    'parsed_pages_31_35.json',
    'parsed_pages_141_145.json',
    'parsed_pages_156_160.json'
]

workspace = '/Users/lfesch/work_files/chess'
for file in files_to_check:
    path = os.path.join(workspace, file)
    print(f"\n=== Checking {file} ===")
    try:
        with open(path, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if 'Bxh6' in line:
                    print(f"  Line {i+1}: {line.strip()}")
                    # Print 5 lines before and after
                    start = max(0, i - 5)
                    end = min(len(lines), i + 6)
                    for j in range(start, end):
                        print(f"    {j+1}: {lines[j].strip()}")
    except Exception as e:
        print(f"Error reading {file}: {e}")
