import logging
import os
import asyncio
from typing import Any, Dict, List, Set

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

    async def _generate_query_variations(self, query: str) -> List[str]:
        """
        ADVANCED RAG: Generates 3 variations of the user query to capture different semantic meanings.
        """
        try:
            prompt = (
                f"You are an AI assistant specialized in information retrieval. "
                f"Generate 3 different search query variations for the following user request to improve semantic search coverage. "
                f"Return only the queries, one per line.\n\n"
                f"User Request: {query}"
            )
            
            # Using LLM to generate variations
            res = await self.ai_service.llm_brain(
                transcript=query,
                user_role="RESEARCH_ANALYST",
                user_instruction=prompt,
                temperature=0.7
            )
            
            variations = [v.strip() for v in res.summary.split("\n") if v.strip()]
            # Ensure the original query is always included
            if query not in variations:
                variations.append(query)
            
            return variations[:4] # Original + 3 variations
        except Exception as e:
            logger.error(f"Failed to generate query variations: {e}")
            return [query]

    async def search_notes(
        self,
        db: Session,
        user_id: str,
        query: str,
        limit: int = 5,
        offset: int = 0,
        threshold: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """
        ADVANCED RAG: Perform Multi-Query semantic search with Parallel Execution and RRF Ranking.
        """
        # 1. Generate query variations
        variations = await self._generate_query_variations(query)
        
        # 2. Parallel Search Execution (using asyncio for concurrency)
        tasks = []
        for var in variations:
            tasks.append(self._single_semantic_search(db, user_id, var, limit * 2, threshold))
        
        # Gather all search results in parallel
        all_results_lists = await asyncio.gather(*tasks)
        
        # 3. Reciprocal Rank Fusion (RRF) & Deduplication
        # Map of note_id -> {note_obj, rrf_score}
        fused_results = {}
        k = 60 # RRF constant
        
        for results_list in all_results_lists:
            for rank, note in enumerate(results_list, start=1):
                if note.id not in fused_results:
                    fused_results[note.id] = {"note": note, "score": 0.0}
                # RRF Formula: 1 / (k + rank)
                fused_results[note.id]["score"] += 1.0 / (k + rank)
        
        # 4. Sort by fused score and format
        sorted_ids = sorted(fused_results.keys(), key=lambda x: fused_results[x]["score"], reverse=True)
        
        formatted_results = []
        for note_id in sorted_ids[offset : offset + limit]:
            item = fused_results[note_id]
            note = item["note"]
            formatted_results.append({
                "id": note.id,
                "title": note.title,
                "summary": note.summary,
                "transcript": note.transcript_deepgram or note.transcript_groq or note.transcript_android or "",
                "timestamp": note.timestamp,
                "similarity_score": round(item["score"] * 10, 3) # Scaled for UI visibility
            })

        return formatted_results

    async def _single_semantic_search(self, db: Session, user_id: str, query: str, limit: int, threshold: float):
        """Helper for a single vector search."""
        try:
            query_embedding = await self.ai_service.generate_embedding(query)
            return (
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
        except Exception as e:
            logger.error(f"Single search failed for query '{query}': {e}")
            return []

    async def search_web(self, query: str) -> List[Dict[str, Any]]:
        """
        Fallback search using Tavily API with parallel execution for speed.
        """
        if not self.tavily_api_key:
            return []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
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
                for r in results:
                    r["content"] = r.get("content", "")[:1500]
                return results
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []

    async def unified_rag_search(
        self, db: Session, user_id: str, query: str, limit: int = 5, offset: int = 0
    ) -> Dict[str, Any]:
        """
        Advanced RAG with Multi-Step Reasoning and Parallel Synthesis.
        """
        # Run local and preliminary web check in parallel for speed
        local_task = self.search_notes(db, user_id, query, limit=limit, offset=offset)
        
        # Parallel execution of context gathering
        local_results = await local_task
        
        # Decide if web is needed based on RRF scores (scaled item["score"] * 10)
        # If best result has very low match, go web.
        needs_web = not local_results or local_results[0]["similarity_score"] < 0.1
        
        web_results = []
        if needs_web:
            web_results = await self.search_web(query)

        # Context construction
        context_parts = []
        if local_results:
            context_parts.append("### RELEVANT PRIVATE NOTES")
            for r in local_results:
                context_parts.append(f"- {r['title']}: {r['summary']}\nTranscript: {r['transcript'][:400]}")
        
        if web_results:
            context_parts.append("\n### EXTERNAL WEB CONTEXT")
            for r in web_results:
                context_parts.append(f"- {r['title']} ({r['url']}): {r['content']}")

        context = "\n\n".join(context_parts) if context_parts else "No context found."
        
        # Synthesis
        user = db.query(models.User).filter(models.User.id == user_id).first()
        prompt = ai_config.RAG_SYNTHESIS_PROMPT.format(query=query, context=context)

        try:
            ai_response = await self.ai_service.llm_brain(
                transcript=query,
                user_role="RESEARCH_ANALYST",
                user_instruction=prompt,
                jargons=user.jargons if user else [],
                personal_instruction=user.system_prompt if user else "",
            )

            return {
                "query": query,
                "answer": ai_response.summary,
                "source": "hybrid" if (local_results and web_results) else ("private" if local_results else "web"),
                "results": local_results[:5],
                "web_context_used": bool(web_results)
            }
        except Exception as e:
            logger.error(f"RAG Synthesis error: {e}")
            return {"query": query, "answer": "Error during synthesis.", "results": local_results}
