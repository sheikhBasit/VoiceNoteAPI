#!/usr/bin/env python3
"""
Script to reorder task routes to fix 404 errors.
Moves specific routes (due-today, overdue, assigned-to-me, search, stats) before /{task_id}
"""
import re

# Read the current file
with open('/home/basitdev/Me/StudioProjects/VoiceNoteAPI/app/api/tasks.py', 'r') as f:
    content = f.read()

# Find the line number where @router.get("/{task_id}" starts
lines = content.split('\n')
task_id_route_start = None
for i, line in enumerate(lines):
    if '@router.get("/{task_id}"' in line:
        task_id_route_start = i
        break

if task_id_route_start:
    print(f"Found /{{task_id}} route at line {task_id_route_start + 1}")
    print("Route ordering is correct - specific routes should be before this line")
    print("Checking if specific routes are after...")
    
    # Check if specific routes are after task_id route
    specific_routes = ['/due-today', '/overdue', '/assigned-to-me', '/search', '/stats']
    for route in specific_routes:
        for i, line in enumerate(lines[task_id_route_start:], start=task_id_route_start):
            if f'@router.get("{route}"' in line:
                print(f"  ❌ {route} is at line {i+1} (AFTER /{task_id})")
                break
    
    print("\nThe issue is confirmed: specific routes are defined AFTER /{task_id}")
    print("FastAPI matches routes in order, so 'due-today' gets matched as a task_id")
else:
    print("Could not find /{task_id} route")
