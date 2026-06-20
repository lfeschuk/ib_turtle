import json

parent_id = 'fcee3a89-ff86-41bd-9806-ab9637a48f6b'
transcript_path = f'/Users/lfesch/.gemini/jetski/brain/{parent_id}/.system_generated/logs/transcript.jsonl'

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line_idx, line in enumerate(f):
        try:
            data = json.loads(line)
            if data.get('type') == 'INVOKE_SUBAGENT' or 'invoke_subagent' in str(data.get('tool_calls', '')):
                print(f"Line {line_idx+1}: Step {data.get('step_index')}")
                print(f"  Tool Calls: {json.dumps(data.get('tool_calls'), indent=2)}")
        except Exception as e:
            pass
