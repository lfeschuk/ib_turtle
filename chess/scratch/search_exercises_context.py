import glob
import os
import re

files = glob.glob('/Users/lfesch/work_files/chess/scratch/page_*_text.txt')
files.sort()

for f in files:
    basename = os.path.basename(f)
    try:
        with open(f, 'r') as file:
            lines = file.readlines()
            for idx, line in enumerate(lines):
                if re.search(r'\bexercise\b', line, re.IGNORECASE):
                    print(f"Found in {basename} Line {idx+1}: {line.strip()}")
                    start = max(0, idx - 2)
                    end = min(len(lines), idx + 3)
                    for j in range(start, end):
                        print(f"  {j+1}: {lines[j].strip()}")
                    print("-" * 40)
    except Exception as e:
        print(f"Error reading {basename}: {e}")
