import glob
import os

files = glob.glob('/Users/lfesch/work_files/chess/scratch/page_*_text.txt')
files.sort()

for f in files:
    basename = os.path.basename(f)
    try:
        with open(f, 'r') as file:
            content = file.read()
            if 'Exercise 5' in content or 'exercise 5' in content.lower():
                print(f"Found in {basename}")
    except Exception as e:
        print(f"Error reading {basename}: {e}")
