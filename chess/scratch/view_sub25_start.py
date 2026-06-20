import json

sub_id = '8a240eae-8914-4dc6-935a-12cc36416956'
transcript_path = f'/Users/lfesch/.gemini/jetski/brain/{sub_id}/.system_generated/logs/transcript.jsonl'

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line_idx, line in enumerate(f):
        if line_idx < 50:
            try:
                data = json.loads(line)
                stype = data.get('type')
                step_idx = data.get('step_index')
                print(f"Line {line_idx+1}: Step {step_idx}, Type: {stype}")
                if stype == 'PLANNER_RESPONSE':
                    print(f"  Thinking: {data.get('thinking', '')[:200]}...")
                    if 'tool_calls' in data and data['tool_calls']:
                        print(f"  Tool calls: {json.dumps(data['tool_calls'])[:200]}")
                elif stype == 'RUN_COMMAND':
                    print(f"  Command: {data.get('tool_calls', '')}")
                    print(f"  Output: {str(data.get('content', ''))[:200]}...")
            except Exception as e:
                print(f"Error parsing line {line_idx+1}: {e}")
