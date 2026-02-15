import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db import models
from app.services.ai_service import AIService
from app.utils.json_logger import JLogger

class AnalyticsService:
    @staticmethod
    def get_team_metrics(db: Session, team_id: str) -> Dict[str, Any]:
        """
        Aggregate key performance indicators for a team.
        """
        # 1. Note Statistics
        total_notes = db.query(models.Note).filter(
            models.Note.team_id == team_id,
            models.Note.is_deleted == False
        ).count()
        
        # 2. Task Statistics
        tasks_query = db.query(models.Task).filter(
            models.Task.team_id == team_id,
            models.Task.is_deleted == False
        )
        total_tasks = tasks_query.count()
        completed_tasks = tasks_query.filter(models.Task.is_done == True).count()
        high_priority_pending = tasks_query.filter(
            models.Task.priority == models.Priority.HIGH,
            models.Task.is_done == False
        ).count()
        
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            "total_notes": total_notes,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "high_priority_pending": high_priority_pending,
            "completion_rate": round(completion_rate, 2)
        }

    @classmethod
    def generate_team_progress_summary(cls, db: Session, team_id: str) -> str:
        """
        Generate an AI narrative of the team's progress using historical note data.
        """
        # Fetch notes from the last 7 days
        seven_days_ago = int((time.time() - (7 * 24 * 60 * 60)) * 1000)
        recent_notes = db.query(models.Note).filter(
            models.Note.team_id == team_id,
            models.Note.timestamp >= seven_days_ago,
            models.Note.is_deleted == False
        ).order_by(models.Note.timestamp.desc()).limit(20).all()
        
        if not recent_notes:
            return "No recent activity found to generate a progress summary."
            
        # Prepare context for LLM
        note_data = []
        for n in recent_notes:
            note_data.append(f"- {n.title}: {n.summary or 'No summary available'}")
            
        context = "\n".join(note_data)
        
        ai_service = AIService()
        try:
            prompt = f"""
            As a Team Progress Analyst, summarize the following note activity from the last 7 days.
            Highlight key achievements, emerging risks, and focus areas for the next week.
            Keep it professional and concise (max 200 words).
            
            Team Activity Log:
            {context}
            """
            
            response = ai_service.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an expert project manager and progress analyst."},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.1-70b-versatile",
                temperature=0.5,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            JLogger.error("Failed to generate team progress summary", team_id=team_id, error=str(e))
            return "AI summary generation currently unavailable."

    @classmethod
    def get_full_team_analytics(cls, db: Session, team_id: str) -> Dict[str, Any]:
        """
        Combines metrics and AI summary.
        """
        metrics = cls.get_team_metrics(db, team_id)
        summary = cls.generate_team_progress_summary(db, team_id)
        
        return {
            "metrics": metrics,
            "ai_summary": summary,
            "generated_at": int(time.time() * 1000)
        }


    @staticmethod
    def get_productivity_pulse(db: Session, user_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Calculate personal productivity metrics for the mobile dashboard.
        """
        # 1. Note Metrics
        notes_query = db.query(models.Note).filter(
            models.Note.user_id == user_id,
            models.Note.is_deleted == False
        )
        total_notes = notes_query.count()
        processed_notes = notes_query.filter(models.Note.status == models.NoteStatus.DONE).count()
        recent_notes = notes_query.order_by(models.Note.timestamp.desc()).limit(5).all()
        
        # 2. Task Metrics
        tasks_query = db.query(models.Task).filter(
            models.Task.user_id == user_id,
            models.Task.is_deleted == False
        )
        total_tasks = tasks_query.count()
        completed_tasks = tasks_query.filter(models.Task.is_done == True).count()
        
        # 3. Calculation logic for ROI and Velocity
        total_words = 0
        all_text = ""
        for note in recent_notes:
            content = note.transcript_groq or note.transcript_deepgram or note.summary or ""
            total_words += len(content.split())
            all_text += " " + content
            
        roi_value = round(total_words / 2400, 1)
        # Format as string for Android: "0.2 hrs saved" or "85%" (using hours for clarity)
        meeting_roi = f"{roi_value} hrs saved"
        
        velocity_val = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        productivity_velocity = f"{int(velocity_val)}%"

        # 4. Generate Heatmap (Simplified mapping to days)
        # For MVP, we'll just mock it or do a simple group by DOW
        heatmap = [
            {"day": "Mon", "intensity": 0.4},
            {"day": "Tue", "intensity": 0.8},
            {"day": "Wed", "intensity": 0.6},
            {"day": "Thu", "intensity": 0.9},
            {"day": "Fri", "intensity": 0.3},
        ]

        # 5. AI Insights (Derived from high-prio tasks or summary)
        ai_insights = []
        high_prio_task = tasks_query.filter(
            models.Task.priority == models.Priority.HIGH,
            models.Task.is_done == False
        ).first()
        
        if high_prio_task:
            ai_insights.append({
                "id": f"insight_{high_prio_task.id}",
                "title": "High Priority Task",
                "description": f"You have an urgent task: {high_prio_task.title}",
                "type": "PRIORITY"
            })
            
        if total_notes > 0 and processed_notes == 0:
            ai_insights.append({
                "id": "insight_processing",
                "title": "Notes Processing",
                "description": "Your recent notes are still being analyzed.",
                "type": "SUGGESTION"
            })

        return {
            "stats": {
                "total_notes": total_notes,
                "processed_notes": processed_notes,
                "total_tasks": total_tasks,
                "meeting_roi": meeting_roi,
                "productivity_velocity": productivity_velocity,
                "decision_heatmap": heatmap
            },
            "recent_notes": [
                {
                    "id": n.id,
                    "title": n.title,
                    "timestamp": n.timestamp,
                    "status": n.status
                } for n in recent_notes
            ],
            "ai_insights": ai_insights,
            "status": "OK"
        }
