# Real-Time Verizon Chat Hallucination Detection Pipeline

## Overview

This is a complete end-to-end pipeline for detecting LLM hallucinations in customer support conversations. It generates realistic multi-turn chats, processes them through an LLM with real-time streaming, computes hallucination scores via grounding, and stores everything in a SQLite database.

## Architecture

```
Chat Simulator → Real-Time Processor → LLM (Streaming) → Grounding Check → Database
     ↓                  ↓                    ↓               ↓
Generate realistic   Send customer    Stream response    Retrieve policy
multi-turn chats     messages 1 at    with tokens &      docs & compute
(customer personas)  a time           logprobs           similarity score
```

## Components

### 1. **chat_simulator.py**
Generates realistic customer messages that simulate real-time chat input.

**Features:**
- 6 issue types: billing, termination, throttling, roaming, device_payment, dispute
- Multiple customer personas: frustrated, confused, professional, polite
- Multi-turn conversations (3-5 turns per chat)
- Generator pattern for streaming messages one at a time

**Usage:**
```python
from chat_simulator import ChatSimulator

sim = ChatSimulator()
conversation, issue_type, persona = sim.generate_conversation()

# Or stream one message at a time
for msg_idx, role, msg, issue, persona, is_final in sim.stream_conversation():
    print(f"{role}: {msg}")
```

### 2. **real_time_processor.py**
Processes customer messages through LLM with streaming token capture.

**Features:**
- Streams LLM responses (captures tokens + logprobs)
- Retrieves relevant Verizon policy documents
- Computes grounding score (0-1)
- Determines hallucination label based on grounding
- Stores everything in database

**Flow:**
1. Receive customer message
2. Call LLM with streaming API
3. Capture each token + logprob as it arrives
4. Retrieve top-3 most similar policy documents
5. Compute grounding score (semantic overlap between response & policies)
6. Label as hallucinated if grounding < 0.4, else truthful
7. Store in database

**Usage:**
```python
from real_time_processor import RealTimeProcessor

with RealTimeProcessor(db_path="chat_database.db") as processor:
    chat_data = processor.process_chat(
        chat_id=1,
        messages=[{"role": "user", "content": "Is there a penalty for early termination?"}],
        issue_type="termination",
        persona="professional"
    )
    processor.save_chat_to_db(chat_data)
```

### 3. **chat_database.py**
SQLite database with schema for storing chats, transcripts, tokens, and predictions.

**Tables:**
- `chats`: main record (chat_id, issue_type, intent, grounding_score, hallucinated)
- `messages`: full conversation transcript per chat
- `tokens`: token-level data (position, token text, logprob)
- `features`: extracted features per chat
- `predictions`: model predictions (for downstream classifiers)

**Usage:**
```python
from chat_database import ChatDatabase

db = ChatDatabase("chat_database.db")

# Get stats
stats = db.stats()
print(f"Total chats: {stats['total_chats']}")
print(f"Hallucinated: {stats['hallucinated_chats']}")

# Get full chat with transcript
chat = db.get_chat_with_features(chat_id=1)
print(chat['transcript'])

db.close()
```

### 4. **pipeline.py**
End-to-end orchestration: generates chats, processes through LLM, stores in database.

**Features:**
- Multi-chat processing loop
- Real-time message-by-message processing
- Verbose output showing each turn
- Database persistence
- Statistics tracking

**Usage:**
```bash
# Dry-run (simulated LLM responses, no API calls)
python3 pipeline.py --n_chats 10 --dry-run --db chat_database.db

# Full run (requires OPENAI_API_KEY environment variable)
python3 pipeline.py --n_chats 100 --db chat_database.db

# Reset database and start fresh
python3 pipeline.py --n_chats 50 --dry-run --reset-db
```

### 5. **retrieval.py**
Hybrid retrieval combining semantic search (embeddings) + keyword matching.

**Features:**
- Keyword retrieval (BM25-style overlap)
- Semantic retrieval (sentence-transformers embeddings, optional)
- Hybrid scoring (average of both)
- Grounding score computation

**Retrievers:**
- `KeywordRetriever`: Fast, no dependencies
- `SemanticRetriever`: More accurate, requires sentence-transformers
- `HybridRetriever`: Combines both (default)

### 6. **verizon_knowledge_base.py**
Verizon policy documentation used for grounding.

**Policies included:**
- Billing and charges
- Cancellation and termination
- Data limits and throttling
- International roaming
- Device payment plans
- Dispute resolution

## Database Schema

```sql
-- Main chat record
CREATE TABLE chats (
    chat_id INTEGER PRIMARY KEY,
    issue_type TEXT,
    intent TEXT,
    customer_persona TEXT,
    grounding_score REAL,
    hallucinated INTEGER,
    created_at TIMESTAMP
);

-- Full conversation transcript
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER,
    message_index INTEGER,
    role TEXT,  -- 'user' or 'assistant'
    content TEXT,
    FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
);

-- Token-level data for TreeSHAP features
CREATE TABLE tokens (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER,
    token_position INTEGER,
    token TEXT,
    logprob REAL,
    FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
);
```

## Example Workflow

```python
from chat_simulator import ChatSimulator
from real_time_processor import RealTimeProcessor

# Step 1: Generate a conversation
sim = ChatSimulator()
conversation, issue_type, persona = sim.generate_conversation(issue_type="billing")

# Step 2: Extract messages
messages = [msg for role, msg in conversation if msg is not None]

# Step 3: Process through LLM
processor = RealTimeProcessor(db_path="chat_database.db", dry_run=False)
chat_data = processor.process_chat(
    chat_id=1,
    messages=[{"role": "user", "content": msg} for msg in messages],
    issue_type=issue_type,
    persona=persona
)

# Step 4: Check hallucination status
print(f"Grounding: {chat_data['grounding_score']}")
print(f"Hallucinated: {chat_data['hallucinated']}")

# Step 5: Store
processor.save_chat_to_db(chat_data)
processor.close()
```

## Running the Full Pipeline

### Quick Test (Dry-Run)
```bash
cd Final_Project
python3 pipeline.py --n_chats 5 --dry-run --reset-db
```

Expected output:
```
Starting real-time chat pipeline (n=5)...
Dry-run: True

[Chat 1] Issue: billing | Persona: confused
------------------------------------------------------------
Customer: Hi, I noticed a weird charge on my bill...
Bot: Thank you for reaching out...
  Grounding: 0.462 | Hallucinated: 0
...

Pipeline Complete!
  - Total chats processed: 5
  - Hallucinated: 1
  - Truthful: 4
  - Avg grounding score: 0.451
  - Database: chat_database.db
```

### Full Run (With OpenAI API)
```bash
export OPENAI_API_KEY="sk-..."
python3 pipeline.py --n_chats 100 --db chat_database.db
```

### Query Results
```python
from chat_database import ChatDatabase

db = ChatDatabase("chat_database.db")

# Get all chats summary
chats = db.get_all_chats_summary(limit=10)
for chat in chats:
    print(f"Chat {chat['chat_id']}: {chat['intent']} | Hallucinated: {chat['hallucinated']}")

# Get full transcript for one chat
chat = db.get_chat_with_features(chat_id=1)
for msg in chat['transcript']:
    print(f"{msg['role']}: {msg['content']}")

db.close()
```

## Next Steps

1. **Feature Engineering**: Extract more features from tokens (entropy, surprise, semantic drift)
2. **Classifier Training**: Train XGBoost/LightGBM on generated data
3. **TreeSHAP Explainability**: Explain which features drove hallucination predictions
4. **Prompt Refresh**: When hallucination detected, automatically refresh with retrieved docs
5. **Live Agent Escalation**: Route to human agent if confidence is low

## Files Structure

```
Final_Project/
├── chat_simulator.py              # Generate realistic customer messages
├── real_time_processor.py          # Process through LLM with streaming
├── chat_database.py                # SQLite database interface
├── retrieval.py                    # Semantic + keyword search
├── verizon_knowledge_base.py       # Policy documentation
├── pipeline.py                     # End-to-end orchestration
├── chat_database.db                # SQLite database (created at runtime)
└── README.md                       # This file
```

## Dependencies

```
openai>=1.0.0
sentence-transformers>=2.0.0  (optional, for semantic retrieval)
```

Install with:
```bash
pip install openai sentence-transformers
```

## Configuration

- **LLM Model**: `gpt-4o-mini` (configurable in `real_time_processor.py`)
- **Max tokens**: 300 per response
- **Temperature**: 0.7
- **Grounding threshold**: <0.4 = hallucinated, ≥0.4 = truthful
- **Top-K retrieval**: 3 documents

## Notes

- **Dry-run mode**: Simulates all responses without API calls (useful for testing)
- **Real-time streaming**: Captures tokens as they're generated (requires OpenAI API key)
- **Logprobs**: Currently `None` in dry-run; captured from API when available
- **Grounding**: Computed via keyword overlap between response and retrieved policies
- **Database**: Auto-creates schema on first run


**API:**
Run the Flask API for real-time ingestion:
```bash
export FLASK_APP=api.py
python3 -m flask run --host=0.0.0.0 --port=5000
```
Endpoint: `POST /chat` accepts JSON `{messages, issue_type, persona, dry_run}`
