import logging
import os
from typing import Any, Dict, List

import httpx
from sqlalchemy.orm import Session

from app.core.config import ai_config
from app.db import models
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.tavily_url = "https://api.tavily.com/search"

    async def search_notes(
        self,
        db: Session,
        user_id: str,
        query: str,
        limit: int = 5,
        threshold: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search with distance thresholding and pagination.
        """
        # 1. Generate embedding for query
        query_embedding = await self.ai_service.generate_embedding(query)

        # 2. Search database
        # L2 distance (lower is better). threshold <= 1.0 is usually a good starting point.
        results = (
            db.query(models.Note)
            .filter(
                models.Note.user_id == user_id,
                models.Note.is_deleted == False,
                models.Note.embedding.l2_distance(query_embedding) <= threshold,
            )
            .order_by(models.Note.embedding.l2_distance(query_embedding))
            .limit(limit)
            .all()
        )

        formatted_results = []
        for note in results:
            # Calculate a generic similarity score (1 - normalized distance)
            # This is a heuristic for the UI
            formatted_results.append(
                {
                    "id": note.id,
                    "title": note.title,
                    "summary": note.summary,
                    "transcript": note.transcript_deepgram
                    or note.transcript_groq
                    or note.transcript_android,
                    "timestamp": note.timestamp,
                    "similarity_score": round(
                        max(
                            0,
                            1
                            - (note.embedding.l2_distance(query_embedding) / threshold),
                        ),
                        2,
                    ),
                }
            )

        return formatted_results

    async def search_web(self, query: str) -> List[Dict[str, Any]]:
        """
        Fallback search using Tavily API with timeout and error handling.
        """
        if not self.tavily_api_key:
            logger.warning("TAVILY_API_KEY not configured. Skipping web search.")
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.tavily_url,
                    json={
                        "api_key": self.tavily_api_key,
                        "query": query,
                        "search_depth": "smart",
                        "include_answer": True,
                        "max_results": 5,
                    },
                )
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])

                # Cleanup web results content
                for r in results:
                    r["content"] = r.get("content", "")[:1000]  # Cap content length

                return results
        except Exception as e:
            logger.error(f"Web search failed for query '{query}': {e}")
            return []

    async def unified_rag_search(
        self, db: Session, user_id: str, query: str
    ) -> Dict[str, Any]:
        """
        Improved V-RAG synthesis decision logic.
        """
        # 1. Local Search with strict threshold
        local_results = await self.search_notes(
            db, user_id, query, limit=5, threshold=0.8
        )

        # 2. Decision logic: Trigger web search if local results are insufficient
        # Consider a combination of count and similarity score
        needs_web = len(local_results) == 0 or all(
            r["similarity_score"] < 0.4 for r in local_results
        )

        web_results = []
        if needs_web:
            logger.info(
                f"Local context insufficient for '{query}'. Triggering web research."
            )
            web_results = await self.search_web(query)

        # 3. Synthesize Context for LLM
        context_parts = []
        if local_results:
            context_parts.append("USER'S PRIVATE NOTES:")
            for r in local_results:
                context_parts.append(
                    f"Title: {r['title']}\nSummary: {r['summary']}\nTranscript Snippet: {r['transcript'][:300]}"
                )

        if web_results:
            context_parts.append("\nWEB RESEARCH DATA:")
            for r in web_results:
                context_parts.append(
                    f"Source: {r['title']}\nContent: {r['content'][:500]}\nURL: {r['url']}"
                )

        context = "\n\n".join(context_parts) if context_parts else "No context found."

        # 4. Fetch User for Personalization
        user = db.query(models.User).filter(models.User.id == user_id).first()
        user_instr = user.system_prompt if user else ""
        user_jargons = user.jargons if user else []

        # 5. Ask LLM to synthesize answer using centralized prompt
        prompt = ai_config.RAG_SYNTHESIS_PROMPT.format(query=query, context=context)

        try:
            # We use a lower temperature for RAG to stay factual
            ai_response = await self.ai_service.llm_brain(
                transcript="Synthesizing from multiple sources...",
                user_role="RESEARCH_ANALYST",
                user_instruction=prompt,
                jargons=user_jargons,
                personal_instruction=user_instr,
            )

            return {
                "query": query,
                "answer": ai_response.summary,
                "source": (
                    "private_notes"
                    if not web_results
                    else ("hybrid" if local_results else "web_only")
                ),
                "local_note_count": len(local_results),
                "web_result_count": len(web_results),
                "results": local_results[:3] + web_results[:2],
            }
        except Exception as e:
            logger.error(f"RAG Synthesis failed: {e}")
            return {
                "query": query,
                "answer": "Synthesis incomplete: We retrieved relevant information but encountered an issue while generating a comprehensive summary. Please review the specific results below.",
                "source": "error",
                "results": local_results + web_results,
            }
