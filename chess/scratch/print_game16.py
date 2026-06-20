import json

with open('/Users/lfesch/work_files/chess/parsed_pages_51_55.json', 'r') as f:
    data = json.load(f)

for ex in data['exercises']:
    if ex['id'] == 'game_16_korchnoi_xie_jun_1995':
        game = ex['preparsedJson']
        print("Initial moves:", game.get('initial_moves'))
        print("Interactive moves:")
        for m in game.get('interactive_section', {}).get('moves', []):
            print(f"  {m.get('move_number')}{m.get('player')}: {m.get('move')}")
