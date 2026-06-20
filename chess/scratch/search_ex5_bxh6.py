import glob
import json
import os

files = [
    '/Users/lfesch/work_files/chess/parsed_pages_76_80.json',
    '/Users/lfesch/work_files/chess/parsed_pages_81_85.json',
    '/Users/lfesch/work_files/chess/parsed_pages_86_90.json',
    '/Users/lfesch/work_files/chess/parsed_pages_91_95.json'
]

for f in files:
    basename = os.path.basename(f)
    try:
        with open(f, 'r') as file:
            content = file.read()
            if 'Bxh6' in content:
                print(f"Found Bxh6 in {basename}")
                # Print where it is
                data = json.loads(content)
                # We need to find which game/theory has it
                exercises = data.get('exercises', [])
                if isinstance(data, list):
                     exercises = data
                for ex in exercises:
                     if 'Bxh6' in json.dumps(ex):
                          print(f"  Game/Theory: {ex.get('id')} - {ex.get('title')}")
    except Exception as e:
        print(f"Error reading {basename}: {e}")
