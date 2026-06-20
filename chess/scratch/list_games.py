import glob
import json
import os

files = glob.glob('/Users/lfesch/work_files/chess/parsed_pages_*.json')
files.sort()

for f in files:
    basename = os.path.basename(f)
    try:
        with open(f, 'r') as file:
            data = json.load(file)
            if 'exercises' in data:
                for ex in data['exercises']:
                    game = ex.get('preparsedJson', {})
                    white = game.get('white', '?')
                    black = game.get('black', '?')
                    event = game.get('event', '?')
                    print(f"{basename}: {ex['id']} - {ex['title']} ({white} vs {black}, {event})")
            elif 'game_id' in data: # Maybe some files have different structure?
                print(f"{basename}: has game_id directly")
    except Exception as e:
        print(f"Error reading {basename}: {e}")
