import json

def extract_codes_from_requirements(requirements_data):
    """Extract all course codes from requirements.json structure"""
    codes = set()
    
    # Add codes from main keys
    for key in requirements_data.keys():
        # Keys are in format "CODE - NAME"
        code = key.split(' - ')[0]
        codes.add(code)
    
    # Recursively extract codes from nested structure
    def traverse(node):
        if isinstance(node, dict):
            # Check if this is a LEAF node with items
            if node.get('type') == 'LEAF' and 'items' in node:
                for item in node['items']:
                    if 'code' in item:
                        codes.add(item['code'])
            
            # Traverse all children
            if 'children' in node:
                for child in node['children']:
                    traverse(child)
            
            # Traverse other nested structures
            for value in node.values():
                if isinstance(value, (dict, list)):
                    traverse(value)
        elif isinstance(list, list):
            for item in node:
                traverse(item)
    
    # Traverse each course's requirements
    for course_data in requirements_data.values():
        if 'requirements' in course_data:
            traverse(course_data['requirements'])
    
    return codes

# Load credits.json
with open('data/credits.json', 'r', encoding='utf-8') as f:
    credits_data = json.load(f)

# Load requirements.json
with open('data/requirements.json', 'r', encoding='utf-8') as f:
    requirements_data = json.load(f)

# Extract all codes from credits.json
credits_codes = set(course['codigo'] for course in credits_data)

# Extract all codes from requirements.json
requirements_codes = extract_codes_from_requirements(requirements_data)

# Find codes in credits but not in requirements
missing_codes = credits_codes - requirements_codes

# Sort for better readability
missing_codes_sorted = sorted(missing_codes)

print(f"Total courses in credits.json: {len(credits_codes)}")
print(f"Total course codes referenced in requirements.json: {len(requirements_codes)}")
print(f"Courses in credits.json but NOT in requirements.json: {len(missing_codes)}")
print("\n" + "="*80)
print("Missing courses:")
print("="*80)

# Print detailed information about missing courses
for code in missing_codes_sorted:
    # Find the course name from credits.json
    course_info = next((c for c in credits_data if c['codigo'] == code), None)
    if course_info:
        print(f"{code:15s} - {course_info['nombre']:60s} ({course_info['creditos']} créditos)")

# Optionally, save to a file
with open('missing_courses.txt', 'w', encoding='utf-8') as f:
    f.write(f"Total courses in credits.json: {len(credits_codes)}\n")
    f.write(f"Total course codes referenced in requirements.json: {len(requirements_codes)}\n")
    f.write(f"Courses in credits.json but NOT in requirements.json: {len(missing_codes)}\n\n")
    f.write("="*80 + "\n")
    f.write("Missing courses:\n")
    f.write("="*80 + "\n")
    for code in missing_codes_sorted:
        course_info = next((c for c in credits_data if c['codigo'] == code), None)
        if course_info:
            f.write(f"{code:15s} - {course_info['nombre']:60s} ({course_info['creditos']} créditos)\n")

print("\n" + "="*80)
print(f"Results also saved to: missing_courses.txt")

