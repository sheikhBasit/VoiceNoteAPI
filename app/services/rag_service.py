from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import Note
from app.services.ai_service import AIService

class RAGService:
    @staticmethod
    def find_similar_notes(
        db: Session, 
        user_id: str, 
        embedding: List[float], 
        exclude_note_id: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.15  # Distance < 0.15 => Similarity > 0.85
    ) -> List[Note]:
        """
        Find notes similar to the given embedding using vector cosine distance.
        """
        query = db.query(Note).filter(
            Note.user_id == user_id,
            Note.is_deleted == False,
            Note.embedding.cosine_distance(embedding) < threshold
        )
        
        if exclude_note_id:
            query = query.filter(Note.id != exclude_note_id)
            
        return query.order_by(Note.embedding.cosine_distance(embedding)).limit(limit).all()

    @staticmethod
    def format_context_for_llm(notes: List[Note]) -> str:
        """
        Formats a list of notes into a context string for the LLM.
        """
        if not notes:
            return "No relevant historical context found."
            
        context_parts = ["--- HISTORICAL CONTEXT (Related Notes) ---"]
        for i, note in enumerate(notes):
            context_parts.append(f"Note {i+1}:")
            context_parts.append(f"Title: {note.title}")
            context_parts.append(f"Summary: {note.summary or 'No summary'}")
            context_parts.append(f"Transcript Snippet: {(note.transcript or '')[:200]}...")
            context_parts.append("")
            
        return "\n".join(context_parts)

    @classmethod
    def get_context_for_transcript(
        cls, 
        db: Session, 
        user_id: str, 
        transcript: str, 
        exclude_note_id: Optional[str] = None
    ) -> str:
        """
        Higher-level helper to get context directly from a transcript.
        """
        ai_service = AIService()
        embedding = ai_service.generate_embedding_sync(transcript)
        similar_notes = cls.find_similar_notes(db, user_id, embedding, exclude_note_id=exclude_note_id)
        return cls.format_context_for_llm(similar_notes)
