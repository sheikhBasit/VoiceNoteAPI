# Missing Credentials and Configuration

The following credentials and environment variables are missing from the backend project. These are required for the full functionality of the "Unified MVP Model 2026".

## 1. AI Service Keys (Critical)
| Variable | Service | Purpose | Status |
| :--- | :--- | :--- | :--- |
| `DEEPGRAM_API_KEY` | Deepgram | Primary transcription (Nova-3) | ❌ Missing |
| `GROQ_API_KEY` | Groq | LLM (Llama 3.1) and Failover transcription (Whisper) | ❌ Missing |
| `HUGGINGFACE_TOKEN` | Hugging Face | pyannote.audio speaker diarization | ❌ Missing |
| `TAVILY_API_KEY` | Tavily | Web-Augmented RAG (Google Search fallback) | ❌ Missing |
| `OPENAI_API_KEY` | OpenAI | Primary Embeddings (text-embedding-3-small) | ❌ Missing |

## 2. Infrastructure & Security
| Variable | Purpose | Status |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string (with pgvector) | ❌ Missing |
| `REDIS_URL` | Celery broker and rate limiting | ❌ Missing |
| `DEVICE_SECRET_KEY` | HMAC key for `X-Device-Signature` validation | ❌ Missing |
| `FIREBASE_SERVICE_ACCOUNT` | Push notifications (FCM) | ❌ Missing |

## 3. Database Seed Status
The `scripts/init.sql` contains placeholder keys. These must be replaced with real keys in the `api_keys` table for the failover mechanism to work:
- `DEEPGRAM_KEY_PRIMARY`
- `DEEPGRAM_KEY_BACKUP`
- `GROQ_KEY_PRIMARY`
- `GROQ_KEY_BACKUP`
- `OPENAI_KEY_PRIMARY`

## 4. Next Steps
1. Create a `.env` file in the root directory.
2. Populate the above variables.
3. Update the `api_keys` table in the database with these production-ready keys.
