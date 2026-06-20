import json

with open('/Users/lfesch/work_files/chess/parsed_pages_96_100.json', 'r') as f:
    data = json.load(f)

for ex in data['exercises']:
    if ex['id'] == 'game_37_hauchard_krakops_1997':
        game = ex['preparsedJson']
        print("Initial moves:", game.get('initial_moves'))
        print("Interactive moves:")
        for m in game.get('interactive_section', {}).get('moves', []):
             print(f"  {m.get('move_number')}{m.get('player')}: {m.get('move')}")
        # Print the sideline to see where it starts
        for side in game.get('sidelines', []):
             if 'Alternative 13 Bxh6' in side.get('name', ''):
                 print(f"Sideline {side.get('name')} startingMoveIndex: {side.get('startingMoveIndex')}")
                 print("Sideline moves:")
                 for m in side.get('moves', []):
                     print(f"  {m.get('move_number')}{m.get('player')}: {m.get('move')}")
