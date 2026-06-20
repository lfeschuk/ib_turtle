import json

parent_id = 'fcee3a89-ff86-41bd-9806-ab9637a48f6b'
transcript_path = f'/Users/lfesch/.gemini/jetski/brain/{parent_id}/.system_generated/logs/transcript.jsonl'

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line_idx, line in enumerate(f):
        if line_idx == 554: # Line 555 is index 554
            data = json.loads(line)
            print("CONTENT:")
            print(data.get('content'))
            break
