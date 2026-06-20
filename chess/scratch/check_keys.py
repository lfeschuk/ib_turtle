import json

files = [
    'parsed_pages_91_95.json',
    'parsed_pages_31_35.json',
    'parsed_pages_141_145.json'
]

for file in files:
    path = f'/Users/lfesch/work_files/chess/{file}'
    print(f"\n=== Checking {file} ===")
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            # Search in games and sidelines
            for game in data.get('exercises', []): # Wait, are they under 'exercises' or 'games'?
                # In parsed_pages_*.json, the root has 'games' or 'exercises'?
                # Let's check keys of one file.
                pass
    except Exception as e:
         print(f"Error: {e}")
