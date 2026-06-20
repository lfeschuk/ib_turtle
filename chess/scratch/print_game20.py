import json

with open('/Users/lfesch/work_files/chess/parsed_pages_61_65.json', 'r') as f:
    data = json.load(f)

for ex in data['exercises']:
    if ex['id'] == 'game_20_van_wely_fedorov_1999':
        game = ex['preparsedJson']
        print("Initial moves:", game.get('initial_moves'))
        print("Interactive moves:")
        for m in game.get('interactive_section', {}).get('moves', []):
            if 'Rxd6' in m.get('move', ''):
                print(f"  *** {m.get('move_number')}{m.get('player')}: {m.get('move')} ***")
            else:
                print(f"  {m.get('move_number')}{m.get('player')}: {m.get('move')}")
