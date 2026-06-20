with open('/Users/lfesch/work_files/chess/parsed_pages_176_178.json', 'r') as f:
    for idx, line in enumerate(f):
        if 'exercise_solution_5' in line:
            print(f"Found on line {idx+1}")
