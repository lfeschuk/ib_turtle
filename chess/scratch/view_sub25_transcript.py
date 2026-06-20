import json
import os

sub_id = '8a240eae-8914-4dc6-935a-12cc36416956'
transcript_path = f'/Users/lfesch/.gemini/jetski/brain/{sub_id}/.system_generated/logs/transcript.jsonl'

if not os.path.exists(transcript_path):
    print(f"Subagent transcript path does not exist: {transcript_path}")
    sys.exit(1)

print("SUBAGENT 25 TRANSCRIPT KEY EVENTS:")
with open(transcript_path, 'r', encoding='utf-8') as f:
    for line_idx, line in enumerate(f):
        try:
            data = json.loads(line)
            stype = data.get('type')
            step_idx = data.get('step_index')
            print(f"Line {line_idx+1}: Step {step_idx}, Type: {stype}")
            if stype == 'PLANNER_RESPONSE':
                print(f"  Thinking: {data.get('thinking', '')[:300]}...")
                if 'tool_calls' in data and data['tool_calls']:
                    print(f"  Tool calls: {json.dumps(data['tool_calls'], indent=2)[:300]}...")
            elif stype == 'RUN_COMMAND':
                print(f"  Command: {data.get('tool_calls', '')}")
                print(f"  Output: {str(data.get('content', ''))[:300]}...")
        except Exception as e:
            print(f"Error parsing line {line_idx+1}: {e}")
