import os
import json
import logging
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy.orm import Session
from app.db import models
from app.services.ai_service import AIService
from pgvector.sqlalchemy import Vector

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.tavily_url = "https://api.tavily.com/search"

    async def search_notes(self, db: Session, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Perform semantic search across user notes using pgvector.
        """
        # 1. Generate embedding for query
        query_embedding = self.ai_service.generate_embedding(query)
        
        # 2. Search database
        # L2 distance (lower is better)
        results = db.query(models.Note).filter(
            models.Note.user_id == user_id,
            models.Note.is_deleted == False
        ).order_by(
            models.Note.embedding.l2_distance(query_embedding)
        ).limit(limit).all()
        
        formatted_results = []
        for note in results:
            formatted_results.append({
                "id": note.id,
                "title": note.title,
                "summary": note.summary,
                "transcript": note.transcript_deepgram or note.transcript_groq or note.transcript_android,
                "timestamp": note.timestamp,
                "similarity": 1.0 # pgvector doesn't return score directly in simple query easily, but order_by handles it
            })
            
        return formatted_results

    async def search_web(self, query: str) -> List[Dict[str, Any]]:
        """
        Fallback search using Tavily API.
        """
        if not self.tavily_api_key:
            logger.warning("TAVILY_API_KEY not configured. Skipping web search.")
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.tavily_url,
                    json={
                        "api_key": self.tavily_api_key,
                        "query": query,
                        "search_depth": "smart",
                        "include_answer": True,
                        "max_results": 5
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("results", [])
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []

    async def unified_rag_search(self, db: Session, user_id: str, query: str) -> Dict[str, Any]:
        """
        The "Niche Conqueror" V-RAG Logic:
        1. Search local notes first.
        2. If notes don't provide a clear answer (or if explicitly requested), search web.
        3. Synthesize final answer.
        """
        # 1. Local Search
        local_results = await self.search_notes(db, user_id, query)
        
        # 2. Decision logic: Do we need web search?
        # For MVP: If local results are empty or query seems like a general question
        needs_web = len(local_results) == 0
        
        web_results = []
        if needs_web:
            logger.info(f"Local search for '{query}' returned no results. Falling back to web.")
            web_results = await self.search_web(query)
            
        # 3. Synthesize Context for LLM
        context = "LOCAL NOTES:\n"
        if local_results:
            for r in local_results:
                context += f"- {r['title']}: {r['summary']}\nTranscript: {r['transcript'][:500]}...\n\n"
        else:
            context += "No relevant local notes found.\n"
            
        if web_results:
            context += "\nWEB SEARCH RESULTS:\n"
            for r in web_results:
                context += f"- {r['title']}: {r['content'][:500]}...\nURL: {r['url']}\n\n"
                
        # 4. Ask LLM to synthesize answer
        prompt = f"""
        User Query: {query}
        
        Using the provided context (local notes and web search results), please answer the user's question.
        If the information is from their local notes, mention it.
        If the information is from the web because notes were insufficient, clarify that.
        
        CONTEXT:
        {context}
        """
        
        # Reuse ai_service llm_brain but with custom prompt
        # We can pass this as user_instruction
        ai_response = await self.ai_service.llm_brain(
            transcript="See context in instruction", 
            user_role="RESEARCHER",
            user_instruction=prompt
        )
        
        return {
            "query": query,
            "answer": ai_response.summary, # LLM fills this
            "source": "hybrid",
            "local_note_count": len(local_results),
            "web_result_count": len(web_results),
            "local_results": local_results[:2], # Truncated for response
            "web_results": web_results[:2]
        }
