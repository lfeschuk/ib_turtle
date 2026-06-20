with open('/Users/lfesch/work_files/chess/parsed_pages_176_178.json', 'r') as f:
    lines = f.readlines()
    for idx, line in enumerate(lines):
        if 'exercise_solution_3' in line:
            print(f"Ex 3 starts around line {idx+1}")
        if 'exercise_solution_4' in line:
            print(f"Ex 4 starts around line {idx+1}")
        if 'exercise_solution_5' in line:
            print(f"Ex 5 starts around line {idx+1}")
        if 'exercise_solution_6' in line:
            print(f"Ex 6 starts around line {idx+1}")
            
# We also need to find "fxe4" in Ex 5.
# Ex 5 is between line 479 and 556.
for idx in range(478, 555):
    if 'fxe4' in lines[idx]:
        print(f"fxe4 in Ex 5 is on line {idx+1}")
