import os
import json

workspace = '/Users/lfesch/work_files/chess'
for root, dirs, files in os.walk(workspace):
    for file in files:
        if file.endswith('.json') and file.startswith('parsed_pages_') and file != 'parsed_pages_176_178.json':
            path = os.path.join(root, file)
            try:
                with open(path, 'r') as f:
                    content = f.read()
                    if 'Exercise' in content:
                        print(f"Found 'Exercise' in {file}")
                        # Try to find the exact line
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'Exercise' in line:
                                print(f"  Line {i+1}: {line.strip()}")
            except Exception as e:
                print(f"Error reading {file}: {e}")
