import json
import sys

parent_id = 'fcee3a89-ff86-41bd-9806-ab9637a48f6b'
transcript_path = f'/Users/lfesch/.gemini/jetski/brain/{parent_id}/.system_generated/logs/transcript.jsonl'

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line_idx, line in enumerate(f):
        if line_idx >= 220: # Start from line 221 (step index around 234)
            try:
                data = json.loads(line)
                step_idx = data.get('step_index')
                stype = data.get('type')
                scontent = data.get('content', '')
                print(f"Line {line_idx+1}: Step {step_idx}, Type: {stype}")
                if stype in ['USER_INPUT', 'PLANNER_RESPONSE']:
                    print(f"  Content: {scontent[:500]}...")
            except Exception as e:
                print(f"Error parsing line {line_idx+1}: {e}")
