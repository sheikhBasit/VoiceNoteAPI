#!/usr/bin/env python3
"""
Reorder routes in tasks.py to fix 404 errors.
Moves specific routes before /{task_id} route.
"""

# Read the file
with open('/home/basitdev/Me/StudioProjects/VoiceNoteAPI/app/api/tasks.py', 'r') as f:
    lines = f.readlines()

# Find the indices
task_id_route_idx = None
specific_route_blocks = []

i = 0
while i < len(lines):
    line = lines[i]
    
    # Find /{task_id} route
    if '@router.get("/{task_id}"' in line and task_id_route_idx is None:
        task_id_route_idx = i
    
    # Find specific routes that need to be moved
    if any(route in line for route in ['@router.get("/due-today"', '@router.get("/overdue"', 
                                        '@router.get("/assigned-to-me"', '@router.get("/search"', 
                                        '@router.get("/stats"']):
        # Extract the entire route function
        start_idx = i
        # Find the end of this function (next @router or end of file)
        j = i + 1
        while j < len(lines):
            if lines[j].startswith('@router.') or lines[j].startswith('# ==='):
                break
            j += 1
        specific_route_blocks.append((start_idx, j, lines[start_idx:j]))
    
    i += 1

if task_id_route_idx is None:
    print("ERROR: Could not find /{task_id} route")
    exit(1)

if not specific_route_blocks:
    print("No specific routes found to move")
    exit(0)

print(f"Found /{{task_id}} route at line {task_id_route_idx + 1}")
print(f"Found {len(specific_route_blocks)} specific routes to move")

# Remove specific routes from their current positions (in reverse order to maintain indices)
new_lines = lines.copy()
for start, end, _ in reversed(specific_route_blocks):
    if start > task_id_route_idx:  # Only move if after task_id route
        print(f"  Moving route from lines {start+1}-{end}")
        del new_lines[start:end]

# Insert specific routes before /{{task_id}} route
insert_idx = task_id_route_idx
for start, end, block in specific_route_blocks:
    if start > task_id_route_idx:  # Only insert if it was after
        new_lines[insert_idx:insert_idx] = block
        insert_idx += len(block)

# Write back
with open('/home/basitdev/Me/StudioProjects/VoiceNoteAPI/app/api/tasks.py', 'w') as f:
    f.writelines(new_lines)

print("✅ Routes reordered successfully!")
print("Specific routes are now BEFORE /{{task_id}}")
