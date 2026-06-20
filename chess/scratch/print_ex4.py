import json

with open('/Users/lfesch/work_files/chess/parsed_pages_61_65.json', 'r') as f:
    data = json.load(f)
    
exercises = data.get('exercises', [])
for ex in exercises:
    print(f"ID: {ex.get('id')}, Title: {ex.get('title')}")
