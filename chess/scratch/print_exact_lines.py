with open('/Users/lfesch/work_files/chess/parsed_pages_176_178.json', 'r') as f:
    lines = f.readlines()
    
    def print_range(start, end):
        print(f"--- Lines {start} to {end} ---")
        for i in range(start-1, end):
            print(f"{i+1}: {repr(lines[i])}")
            
    print_range(154, 158)
    print_range(440, 444)
    print_range(486, 490)
    print_range(505, 509)
    print_range(564, 568)
