import os

workspace = '/Users/lfesch/work_files/chess'
for root, dirs, files in os.walk(workspace):
    for file in files:
        if file.endswith('.json') and file.startswith('parsed_pages_') and file != 'parsed_pages_176_178.json':
            path = os.path.join(root, file)
            try:
                with open(path, 'r') as f:
                    content = f.read()
                    if 'Bxh6' in content and 'Nxe4' in content:
                        print(f"Found both in {file}")
            except Exception as e:
                print(f"Error reading {file}: {e}")
