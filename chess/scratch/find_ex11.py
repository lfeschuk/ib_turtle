with open('/Users/lfesch/work_files/chess/parsed_pages_176_178.json', 'r') as f:
    lines = f.readlines()
    for idx, line in enumerate(lines):
        if 'exercise_solution_11' in line:
            print(f"Ex 11 starts around line {idx+1}")
            for i in range(idx, idx+15):
                print(f"  {i+1}: {lines[i].strip()}")
