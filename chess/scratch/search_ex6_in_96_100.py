import json

with open('/Users/lfesch/work_files/chess/parsed_pages_96_100.json', 'r') as f:
    data = json.load(f)

for ex in data['exercises']:
    content = json.dumps(ex)
    if 'Bxh6' in content or 'Exercise 6' in content:
        print(f"Found in {ex['id']} - {ex['title']}")
        if 'preparsedJson' in ex:
            game = ex['preparsedJson']
            print("  Initial moves:", game.get('initial_moves'))
            # Print commentary containing Exercise 6
            for m in game.get('interactive_section', {}).get('moves', []):
                comm = m.get('commentary', '')
                if 'Exercise 6' in comm or 'exercise 6' in comm.lower():
                    print(f"  Move {m.get('move_number')}{m.get('player')}: {m.get('move')}")
                    print(f"    Commentary: {comm}")
            for side in game.get('sidelines', []):
                for m in side.get('moves', []):
                    comm = m.get('commentary', '')
                    if 'Exercise 6' in comm or 'exercise 6' in comm.lower():
                        print(f"  Sideline {side.get('name')} Move {m.get('move_number')}{m.get('player')}: {m.get('move')}")
                        print(f"    Commentary: {comm}")
