import json

parent_id = 'fcee3a89-ff86-41bd-9806-ab9637a48f6b'
transcript_path = f'/Users/lfesch/.gemini/jetski/brain/{parent_id}/.system_generated/logs/transcript.jsonl'

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line_idx, line in enumerate(f):
        if line_idx >= 550 and line_idx <= 570:
            try:
                data = json.loads(line)
                print(f"Line {line_idx+1}: Step {data.get('step_index')}, Type: {data.get('type')}, Status: {data.get('status')}")
                if 'tool_calls' in data:
                    print(f"  tool_calls: {str(data.get('tool_calls'))[:200]}")
                if 'content' in data:
                    print(f"  content: {str(data.get('content'))[:200]}")
                if 'output' in data:
                    print(f"  output: {str(data.get('output'))[:200]}")
            except Exception as e:
                print(f"Error at line {line_idx+1}: {e}")
