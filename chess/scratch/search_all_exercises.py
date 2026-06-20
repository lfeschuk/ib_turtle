import glob
import json
import os

files = glob.glob('/Users/lfesch/work_files/chess/parsed_pages_*.json')
files.sort()

for f in files:
    basename = os.path.basename(f)
    try:
        with open(f, 'r') as file:
            content = file.read()
            for i in range(1, 12):
                if f'exercise_{i}' in content or f'Exercise {i}' in content:
                    print(f"Found Exercise {i} in {basename}")
    except Exception as e:
        print(f"Error reading {basename}: {e}")
