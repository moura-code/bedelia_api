import json

def extract_all_referenced_courses(requirements_data):
    """Extract all course references from requirements.json structure"""
    references = []  # List of tuples: (parent_course, referenced_code, context)
    
    def traverse(node, parent_course, context_path=""):
        if isinstance(node, dict):
            # Check if this is a LEAF node with items
            if node.get('type') == 'LEAF' and 'items' in node:
                for item in node['items']:
                    if 'code' in item and 'kind' in item:
                        # Store reference with context
                        ref_info = {
                            'parent_course': parent_course,
                            'code': item['code'],
                            'name': item.get('name', 'N/A'),
                            'kind': item['kind'],  # curso, examen
                            'source': item.get('source', 'N/A'),
                            'raw': item.get('raw', ''),
                            'context': context_path
                        }
                        references.append(ref_info)
            
            # Traverse all children
            if 'children' in node:
                new_context = f"{context_path} > {node.get('label', 'unlabeled')}"
                for child in node['children']:
                    traverse(child, parent_course, new_context)
            
            # Traverse other nested structures
            for key, value in node.items():
                if key not in ['children', 'items'] and isinstance(value, (dict, list)):
                    traverse(value, parent_course, context_path)
        elif isinstance(node, list):
            for item in node:
                traverse(item, parent_course, context_path)
    
    # Traverse each course's requirements
    for course_key, course_data in requirements_data.items():
        if 'requirements' in course_data:
            traverse(course_data['requirements'], course_key, "Root")
    
    return references

# Load credits.json
with open('data/credits.json', 'r', encoding='utf-8') as f:
    credits_data = json.load(f)

# Load requirements.json
with open('data/requirements.json', 'r', encoding='utf-8') as f:
    requirements_data = json.load(f)

# Create a set of all available course codes in credits.json
available_codes = set(course['codigo'] for course in credits_data)

# Extract all referenced courses from requirements
all_references = extract_all_referenced_courses(requirements_data)

# Find broken references (referenced but not in credits)
broken_references = [ref for ref in all_references if ref['code'] not in available_codes]

# Group broken references by parent course
broken_by_parent = {}
for ref in broken_references:
    parent = ref['parent_course']
    if parent not in broken_by_parent:
        broken_by_parent[parent] = []
    broken_by_parent[parent].append(ref)

# Statistics
total_references = len(all_references)
broken_count = len(broken_references)
affected_courses = len(broken_by_parent)

print("="*80)
print("BROKEN REFERENCES ANALYSIS")
print("="*80)
print(f"\nTotal course references in requirements: {total_references}")
print(f"Broken references (not found in credits.json): {broken_count}")
print(f"Courses with broken references: {affected_courses}")
print(f"Percentage of broken references: {(broken_count/total_references*100):.2f}%")

print("\n" + "="*80)
print("DETAILED BROKEN REFERENCES BY PARENT COURSE")
print("="*80)

for parent_course in sorted(broken_by_parent.keys()):
    refs = broken_by_parent[parent_course]
    print(f"\n📚 Parent Course: {parent_course}")
    print(f"   Number of broken references: {len(refs)}")
    print(f"   {'-'*76}")
    
    for ref in refs:
        print(f"   ❌ Code: {ref['code']}")
        print(f"      Name: {ref['name']}")
        print(f"      Kind: {ref['kind']}")
        print(f"      Source: {ref['source']}")
        print(f"      Raw: {ref['raw'][:100]}...")
        print()

# Save detailed report to file
with open('broken_requirements_report.txt', 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("BROKEN REFERENCES ANALYSIS\n")
    f.write("="*80 + "\n\n")
    f.write(f"Total course references in requirements: {total_references}\n")
    f.write(f"Broken references (not found in credits.json): {broken_count}\n")
    f.write(f"Courses with broken references: {affected_courses}\n")
    f.write(f"Percentage of broken references: {(broken_count/total_references*100):.2f}%\n")
    
    f.write("\n" + "="*80 + "\n")
    f.write("DETAILED BROKEN REFERENCES BY PARENT COURSE\n")
    f.write("="*80 + "\n")
    
    for parent_course in sorted(broken_by_parent.keys()):
        refs = broken_by_parent[parent_course]
        f.write(f"\nParent Course: {parent_course}\n")
        f.write(f"Number of broken references: {len(refs)}\n")
        f.write(f"{'-'*76}\n")
        
        for ref in refs:
            f.write(f"  - Code: {ref['code']}\n")
            f.write(f"    Name: {ref['name']}\n")
            f.write(f"    Kind: {ref['kind']}\n")
            f.write(f"    Source: {ref['source']}\n")
            f.write(f"    Raw: {ref['raw']}\n")
            f.write("\n")

# Create summary of unique broken codes
unique_broken_codes = {}
for ref in broken_references:
    code = ref['code']
    if code not in unique_broken_codes:
        unique_broken_codes[code] = {
            'name': ref['name'],
            'kind': ref['kind'],
            'count': 0,
            'parents': set()
        }
    unique_broken_codes[code]['count'] += 1
    unique_broken_codes[code]['parents'].add(ref['parent_course'])

print("\n" + "="*80)
print("SUMMARY: UNIQUE BROKEN COURSE CODES")
print("="*80)
print(f"{'Code':<20} {'Name':<40} {'Kind':<10} {'Times Referenced'}")
print("-"*80)
for code in sorted(unique_broken_codes.keys()):
    info = unique_broken_codes[code]
    print(f"{code:<20} {info['name'][:38]:<40} {info['kind']:<10} {info['count']}")

print("\n" + "="*80)
print(f"Report saved to: broken_requirements_report.txt")
print("="*80)

