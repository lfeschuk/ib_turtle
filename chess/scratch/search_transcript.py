import json

transcript_path = '/Users/lfesch/.gemini/jetski/brain/80acff57-1c2a-4599-a145-f543815e143b/.system_generated/logs/transcript.jsonl'

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line_idx, line in enumerate(f):
        try:
            data = json.loads(line)
            content = str(data)
            if 'GEMINI_API_KEY' in content or 'api_key' in content or 'ApiKey' in content:
                # Print step index, type, and snippet of content where it occurs
                print(f"Line {line_idx+1}: Step index {data.get('step_index')}, Type: {data.get('type')}")
                # Print a clean snippet
                snippet = content
                if len(snippet) > 200:
                    idx = snippet.find('GEMINI_API_KEY')
                    if idx != -1:
                        snippet = snippet[max(0, idx-50):min(len(snippet), idx+150)]
                    else:
                        snippet = snippet[:200] + "..."
                print(f"  Snippet: {snippet}")
        except Exception as e:
            print(f"Error parsing line {line_idx+1}: {e}")
