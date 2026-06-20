import json

with open('/Users/lfesch/work_files/chess/parsed_pages_51_55.json', 'r') as f:
    data = json.load(f)

print("Type:", type(data))
if isinstance(data, dict):
    print("Keys:", data.keys())
    for k, v in data.items():
        if isinstance(v, list):
            print(f"Key '{k}' is list of length {len(v)}")
            if len(v) > 0:
                print("First item keys:", v[0].keys() if isinstance(v[0], dict) else type(v[0]))
        else:
            print(f"Key '{k}' type: {type(v)}")
elif isinstance(data, list):
    print("Length:", len(data))
    if len(data) > 0:
        print("First item keys:", data[0].keys() if isinstance(data[0], dict) else type(data[0]))
