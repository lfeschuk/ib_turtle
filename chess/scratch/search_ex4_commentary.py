import json

with open('/Users/lfesch/work_files/chess/parsed_pages_61_65.json', 'r') as f:
    data = json.load(f)

for ex in data['exercises']:
    if ex['id'] == 'game_20_van_wely_fedorov_1999':
        game = ex['preparsedJson']
        for m in game.get('interactive_section', {}).get('moves', []):
            comm = m.get('commentary', '')
            if 'Exercise 4' in comm or 'exercise 4' in comm.lower():
                print(f"Move {m.get('move_number')}{m.get('player')}: {m.get('move')}")
                print(f"  Commentary: {comm}")
        for side in game.get('sidelines', []):
            for m in side.get('moves', []):
                comm = m.get('commentary', '')
                if 'Exercise 4' in comm or 'exercise 4' in comm.lower():
                    print(f"Sideline {side.get('name')} Move {m.get('move_number')}{m.get('player')}: {m.get('move')}")
                    print(f"  Commentary: {comm}")
