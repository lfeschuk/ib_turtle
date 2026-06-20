import json
import os

parent_id = 'fcee3a89-ff86-41bd-9806-ab9637a48f6b'
transcript_path = f'/Users/lfesch/.gemini/jetski/brain/{parent_id}/.system_generated/logs/transcript.jsonl'

if not os.path.exists(transcript_path):
    print(f"Transcript path does not exist: {transcript_path}")
    # Let's search under the parent folder to see if we can find the transcript
    parent_folder = f'/Users/lfesch/.gemini/jetski/brain/{parent_id}'
    if os.path.exists(parent_folder):
        print(f"Parent folder exists. Contents: {os.listdir(parent_folder)}")
        # Look recursively for transcript.jsonl
        for root, dirs, files in os.walk(parent_folder):
            for file in files:
                if file == 'transcript.jsonl':
                    print(f"Found transcript.jsonl at: {os.path.join(root, file)}")
                    transcript_path = os.path.join(root, file)
                    break
    else:
        print(f"Parent folder does not exist: {parent_folder}")
        # Let's search all folders in brain/
        brain_folder = '/Users/lfesch/.gemini/jetski/brain'
        if os.path.exists(brain_folder):
            print(f"Brain folder contents: {os.listdir(brain_folder)}")
        sys.exit(1)

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line_idx, line in enumerate(f):
        try:
            data = json.loads(line)
            content = str(data)
            if 'GEMINI_API_KEY' in content or 'api_key' in content or 'ApiKey' in content:
                print(f"Line {line_idx+1}: Step index {data.get('step_index')}, Type: {data.get('type')}")
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
