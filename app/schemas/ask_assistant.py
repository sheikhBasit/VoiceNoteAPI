from pydantic import BaseModel


class AssistantRequest(BaseModel):
    note_id: str
    question: str

class AssistantResponse(BaseModel):
    answer: str

class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 5

class SearchResult(BaseModel):
    note_id: str
    title: str
    summary: str
    score: float  # The similarity score from pgvector