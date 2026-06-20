with open('/Users/lfesch/work_files/chess/parsed_pages_176_178.json', 'r') as f:
    lines = f.readlines()
    print("Ex 3 initial_moves line:")
    for i in range(146, 165):
        if 'initial_moves' in lines[i]:
            print(f"{i+1}: {lines[i].strip()}")
            
    print("Ex 4 initial_moves line:")
    for i in range(432, 450):
        if 'initial_moves' in lines[i]:
            print(f"{i+1}: {lines[i].strip()}")
            
    print("Ex 5 initial_moves line:")
    for i in range(478, 495):
        if 'initial_moves' in lines[i]:
            print(f"{i+1}: {lines[i].strip()}")
            
    print("Ex 6 initial_moves line:")
    for i in range(556, 575):
        if 'initial_moves' in lines[i]:
            print(f"{i+1}: {lines[i].strip()}")
