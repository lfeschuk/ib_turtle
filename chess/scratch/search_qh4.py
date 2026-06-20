import os

workspace = '/Users/lfesch/work_files/chess'
for root, dirs, files in os.walk(workspace):
    for file in files:
        if file.endswith('.json') and file.startswith('parsed_pages_'):
            path = os.path.join(root, file)
            try:
                with open(path, 'r') as f:
                    content = f.read()
                    if 'Qh4' in content:
                        print(f"Found 'Qh4' in {file}")
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'Qh4' in line:
                                print(f"  Line {i+1}: {line.strip()}")
            except Exception as e:
                print(f"Error reading {file}: {e}")
