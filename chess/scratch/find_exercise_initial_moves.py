import glob
import json
import os

files = glob.glob('/Users/lfesch/work_files/chess/parsed_pages_*.json')
files.sort()

for f in files:
    basename = os.path.basename(f)
    if basename == 'parsed_pages_176_178.json':
        continue # Skip solutions
    try:
        with open(f, 'r') as file:
            data = json.load(file)
            # Check if it's a list or dict
            exercises = []
            if isinstance(data, dict):
                if 'exercises' in data:
                    exercises = data['exercises']
                elif 'id' in data and data['id'].startswith('exercise_'):
                    exercises = [data]
            elif isinstance(data, list):
                exercises = [item for item in data if isinstance(item, dict) and item.get('id', '').startswith('exercise_')]
            
            for ex in exercises:
                game = ex.get('preparsedJson', {})
                initial_moves = game.get('initial_moves', '')
                if initial_moves:
                     print(f"{basename}: {ex['id']} - {ex['title']}")
                     print(f"  initial_moves: {initial_moves}")
    except Exception as e:
        print(f"Error reading {basename}: {e}")
