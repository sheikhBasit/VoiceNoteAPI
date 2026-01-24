"""
Seed Data Generator for VoiceNote Database

This script creates sample data for development and testing:
- 5 test users with different roles
- 15 notes with various states (pending, done, archived, deleted)
- 30 tasks with different priorities and assignments
"""

import sys
import os
import time
import uuid
from datetime import datetime, timedelta

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db import models
from app.services.auth_service import get_password_hash

def clear_all_data(db: Session):
    """Clear all data from tables"""
    print("🗑️  Clearing existing data...")
    db.query(models.Task).delete()
    db.query(models.Note).delete()
    db.query(models.User).delete()
    db.commit()
    print("✅ Data cleared")

def create_users(db: Session):
    """Create test users with different roles"""
    print("\n👥 Creating test users...")
    
    users_data = [
        {
            "id": "user_student_1",
            "name": "John Student",
            "email": "john.student@university.edu",
            "token": f"token_{uuid.uuid4()}",
            "device_id": "device_001",
            "device_model": "Samsung Galaxy S23",
            "primary_role": models.UserRole.STUDENT,
            "system_prompt": "You are helping a student study and take notes on lectures",
            "work_start_hour": 8,
            "work_end_hour": 16,
            "work_days": [2, 3, 4, 5, 6],  # Mon-Fri
        },
        {
            "id": "user_student_2",
            "name": "Sarah Scholar",
            "email": "sarah.scholar@university.edu",
            "token": f"token_{uuid.uuid4()}",
            "device_id": "device_002",
            "device_model": "iPhone 14 Pro",
            "primary_role": models.UserRole.STUDENT,
            "secondary_role": models.UserRole.TEACHER,
            "system_prompt": "You are helping a student who also tutors others",
            "work_start_hour": 7,
            "work_end_hour": 20,
            "work_days": [1, 2, 3, 4, 5, 6],  # Mon-Sat
        },
        {
            "id": "user_teacher_1",
            "name": "Dr. Alice Teacher",
            "email": "alice.teacher@university.edu",
            "token": f"token_{uuid.uuid4()}",
            "device_id": "device_003",
            "device_model": "iPad Pro",
            "primary_role": models.UserRole.TEACHER,
            "system_prompt": "You are helping a teacher prepare lectures and grade assignments",
            "work_start_hour": 9,
            "work_end_hour": 17,
            "work_days": [2, 3, 4, 5],  # Mon-Thu
        },
        {
            "id": "user_office_1",
            "name": "Bob Manager",
            "email": "bob.manager@company.com",
            "token": f"token_{uuid.uuid4()}",
            "device_id": "device_004",
            "device_model": "Samsung Galaxy Z Fold 5",
            "primary_role": models.UserRole.OFFICE_WORKER,
            "system_prompt": "You are helping an office worker manage meetings and tasks",
            "work_start_hour": 9,
            "work_end_hour": 18,
            "work_days": [2, 3, 4, 5, 6],  # Mon-Fri
        },
        {
            "id": "user_developer_1",
            "name": "Charlie Dev",
            "email": "charlie.dev@startup.io",
            "token": f"token_{uuid.uuid4()}",
            "device_id": "device_005",
            "device_model": "OnePlus 11",
            "primary_role": models.UserRole.DEVELOPER,
            "system_prompt": "You are helping a developer document code and meetings",
            "work_start_hour": 10,
            "work_end_hour": 19,
            "work_days": [2, 3, 4, 5, 6],  # Mon-Fri
            "jargons": ["API", "REST", "GraphQL", "microservices", "Kubernetes"],
        },
    ]
    
    users = []
    for user_data in users_data:
        user = models.User(
            **user_data,
            last_login=int(time.time() * 1000),
            is_deleted=False
        )
        db.add(user)
        users.append(user)
        print(f"  ✅ Created user: {user.name} ({user.primary_role.value})")
    
    db.commit()
    return users

def create_admin(db: Session):
    """Create the primary admin user"""
    print("\n👑 Creating primary admin user...")
    admin = models.User(
        id="admin-fixed-id",
        email="admin@admin.com",
        name="Admin User",
        is_admin=True,
        password_hash=get_password_hash("P@$$w0rd"),
        token="admin-token",
        device_id="admin-web",
        device_model="Web Dashboard",
        last_login=int(time.time() * 1000)
    )
    db.add(admin)
    db.commit()
    print("  ✅ Admin created successfully")

def create_notes(db: Session, users):
    """Create test notes with various states"""
    print("\n📝 Creating test notes...")
    
    transcripts = [
        {
            "groq": "Speaker 1: Good morning everyone. Today we'll cover Chapter 3 on quantum mechanics. The key concepts are superposition and entanglement. Let me start with superposition.",
            "deepgram": "Speaker 1: Good morning everyone. Today we'll cover Chapter 3 on quantum mechanics. The key concepts are superposition and entanglement. Let me start with superposition.",
        },
        {
            "groq": "Speaker 1: Let's discuss project management. First, we need to define our milestones. The first milestone is the API design, due next week.",
            "deepgram": "Speaker 1: Let's discuss project management. First, we need to define our milestones. The first milestone is the API design, due next week.",
        },
        {
            "groq": "Speaker 1: Meeting notes from the board meeting. Discussed Q3 revenue targets. Sales increased by 15 percent. Marketing budget approved.",
            "deepgram": "Speaker 1: Meeting notes from the board meeting. Discussed Q3 revenue targets. Sales increased by 15 percent. Marketing budget approved.",
        },
    ]
    
    notes_data = [
        {"user_id": users[0].id, "title": "Quantum Mechanics Lecture", "summary": "Chapter 3 on superposition and entanglement", "priority": models.Priority.HIGH, "status": models.NoteStatus.PENDING, "deleted": False},
        {"user_id": users[0].id, "title": "Physics Lab Notes", "summary": "Experiment results from Thursday's lab", "priority": models.Priority.MEDIUM, "status": models.NoteStatus.DONE, "deleted": False},
        {"user_id": users[0].id, "title": "Completed Lecture Notes", "summary": "Archived notes from last semester", "priority": models.Priority.LOW, "status": models.NoteStatus.DONE, "deleted": False, "archived": True},
        {"user_id": users[1].id, "title": "Project Planning Meeting", "summary": "Q4 project roadmap and milestones", "priority": models.Priority.HIGH, "status": models.NoteStatus.PENDING, "deleted": False},
        {"user_id": users[1].id, "title": "Deleted Meeting Notes", "summary": "Old notes marked for deletion", "priority": models.Priority.LOW, "status": models.NoteStatus.DONE, "deleted": True},
        {"user_id": users[2].id, "title": "Board Meeting Q3", "summary": "Q3 revenue targets and budget approvals", "priority": models.Priority.HIGH, "status": models.NoteStatus.DONE, "deleted": False},
        {"user_id": users[2].id, "title": "Faculty Meeting", "summary": "Department updates and curriculum changes", "priority": models.Priority.MEDIUM, "status": models.NoteStatus.PENDING, "deleted": False},
        {"user_id": users[3].id, "title": "Client Call", "summary": "Project requirements and timeline", "priority": models.Priority.HIGH, "status": models.NoteStatus.PENDING, "deleted": False},
        {"user_id": users[4].id, "title": "Sprint Planning", "summary": "Sprint 24 tasks and assignments", "priority": models.Priority.HIGH, "status": models.NoteStatus.PENDING, "deleted": False},
        {"user_id": users[4].id, "title": "Code Review Notes", "summary": "Architecture review feedback", "priority": models.Priority.MEDIUM, "status": models.NoteStatus.DONE, "deleted": False},
    ]
    
    notes = []
    for idx, note_data in enumerate(notes_data):
        transcript_idx = idx % len(transcripts)
        deleted_at = None
        if note_data.get("deleted"):
            deleted_at = int((time.time() - 86400) * 1000)  # 1 day ago
        
        note = models.Note(
            id=str(uuid.uuid4()),
            user_id=note_data["user_id"],
            title=note_data["title"],
            summary=note_data["summary"],
            transcript_groq=transcripts[transcript_idx]["groq"],
            transcript_deepgram=transcripts[transcript_idx]["deepgram"],
            priority=note_data["priority"],
            status=note_data["status"],
            is_deleted=note_data.get("deleted", False),
            deleted_at=deleted_at,
            is_archived=note_data.get("archived", False),
            timestamp=int(time.time() * 1000),
        )
        db.add(note)
        notes.append(note)
        print(f"  ✅ Created note: {note.title}")
    
    db.commit()
    return notes

def create_tasks(db: Session, notes):
    """Create test tasks linked to notes"""
    print("\n✅ Creating test tasks...")
    
    tasks_data = [
        # Tasks for first note (user_student_1)
        {"note_id": notes[0].id, "description": "Submit lab report", "priority": models.Priority.HIGH, "done": False},
        {"note_id": notes[0].id, "description": "Complete practice problems", "priority": models.Priority.MEDIUM, "done": False},
        {"note_id": notes[0].id, "description": "Review chapter 3", "priority": models.Priority.MEDIUM, "done": True},
        
        # Tasks for second note
        {"note_id": notes[1].id, "description": "Analyze experiment data", "priority": models.Priority.HIGH, "done": True},
        
        # Tasks for project planning (HIGH priority)
        {"note_id": notes[3].id, "description": "Design API schema", "priority": models.Priority.HIGH, "done": False},
        {"note_id": notes[3].id, "description": "Setup database schema", "priority": models.Priority.HIGH, "done": False},
        {"note_id": notes[3].id, "description": "Create authentication endpoints", "priority": models.Priority.MEDIUM, "done": False},
        
        # Tasks for board meeting
        {"note_id": notes[5].id, "description": "Prepare revenue report", "priority": models.Priority.HIGH, "done": True},
        
        # Tasks for client call
        {"note_id": notes[7].id, "description": "Gather requirements", "priority": models.Priority.HIGH, "done": False},
        {"note_id": notes[7].id, "description": "Create project timeline", "priority": models.Priority.HIGH, "done": False},
        
        # Tasks for sprint
        {"note_id": notes[8].id, "description": "Implement user authentication", "priority": models.Priority.HIGH, "done": False},
        {"note_id": notes[8].id, "description": "Setup CI/CD pipeline", "priority": models.Priority.MEDIUM, "done": False},
        {"note_id": notes[9].id, "description": "Fix security vulnerabilities", "priority": models.Priority.HIGH, "done": True},
    ]
    
    tasks = []
    for task_data in tasks_data:
        task = models.Task(
            id=str(uuid.uuid4()),
            note_id=task_data["note_id"],
            description=task_data["description"],
            priority=task_data["priority"],
            is_done=task_data["done"],
            is_deleted=False,
            reminder_count=0,
            assigned_entities=[
                {"name": "John Doe", "phone": "+1-555-0100", "email": "john@example.com"}
            ],
            created_at=int(time.time() * 1000),
            updated_at=int(time.time() * 1000),
        )
        db.add(task)
        tasks.append(task)
        status = "✅" if task_data["done"] else "⏳"
        print(f"  {status} Created task: {task.description} ({task.priority.value})")
    
    db.commit()
    return tasks

def print_summary(db: Session):
    """Print summary of created data"""
    print("\n" + "="*70)
    print("📊 SEED DATA SUMMARY")
    print("="*70)
    
    users_count = db.query(models.User).count()
    active_users = db.query(models.User).filter(models.User.is_deleted == False).count()
    
    notes_count = db.query(models.Note).count()
    active_notes = db.query(models.Note).filter(models.Note.is_deleted == False).count()
    archived_notes = db.query(models.Note).filter(models.Note.is_archived == True).count()
    
    tasks_count = db.query(models.Task).count()
    completed_tasks = db.query(models.Task).filter(models.Task.is_done == True).count()
    high_priority_tasks = db.query(models.Task).filter(models.Task.priority == models.Priority.HIGH).count()
    
    print(f"\n👥 Users: {users_count} total ({active_users} active)")
    print(f"📝 Notes: {notes_count} total ({active_notes} active, {archived_notes} archived)")
    print(f"✅ Tasks: {tasks_count} total ({completed_tasks} completed, {high_priority_tasks} high priority)")
    
    print("\n🎯 Ready for testing and development!")
    print("="*70)

def main():
    """Run seed data generation"""
    print("🌱 Starting VoiceNote Database Seeding...\n")
    
    db = SessionLocal()
    try:
        # Clear existing data
        clear_all_data(db)
        
        # Create data
        create_admin(db)
        users = create_users(db)
        notes = create_notes(db, users)
        tasks = create_tasks(db, notes)
        
        # Print summary
        print_summary(db)
        
        print("\n✨ Seeding complete!")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
