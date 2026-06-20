import json

with open('/Users/lfesch/work_files/chess/parsed_pages_61_65.json', 'r') as f:
    data = json.load(f)

for ex in data['exercises']:
    content = json.dumps(ex)
    if 'Rxd6' in content or 'Exercise 4' in content:
        print(f"Found in {ex['id']} - {ex['title']}")
        # Print some context or moves
        if 'preparsedJson' in ex:
            game = ex['preparsedJson']
            print("  Initial moves:", game.get('initial_moves'))
            print("  Interactive moves length:", len(game.get('interactive_section', {}).get('moves', [])))
