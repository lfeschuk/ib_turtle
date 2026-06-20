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
            if 'exercise_11' in content:
                print(f"Found 'exercise_11' in {basename}")
            if 'Exercise 11' in content:
                print(f"Found 'Exercise 11' in {basename}")
    except Exception as e:
        print(f"Error reading {basename}: {e}")
