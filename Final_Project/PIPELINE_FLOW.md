"""PIPELINE FLOW EXPLANATION

Complete Real-Time Chat Hallucination Detection Pipeline

================================================================================
                             FLOW DIAGRAM
================================================================================

START
  │
  ├─→ pipeline.py (Main Orchestrator)
  │   ├─ Initializes ChatDatabase (creates/opens SQLite DB)
  │   ├─ Initializes RealTimeProcessor
  │   └─ Loop: for each chat (n_chats):
  │
  │       ┌─────────────────────────────────────────────────────────┐
  │       │ CHAT GENERATION & PROCESSING                             │
  │       │                                                          │
  │       │  1. chat_simulator.generate_conversation()              │
  │       │     ├─ Pick random issue_type (billing, termination...) │
  │       │     ├─ Pick random customer_persona                     │
  │       │     └─ Generate 3-5 turn conversation template          │
  │       │                                                          │
  │       │  2. Process each customer turn:                          │
  │       │     ├─ Get customer message from simulator              │
  │       │     ├─ Add to messages[] history                        │
  │       │     │                                                    │
  │       │     └─→ real_time_processor.process_chat()              │
  │       │         ├─ Call LLM with messages history              │
  │       │         │   (gpt-4o-mini with streaming)               │
  │       │         │                                                │
  │       │         ├─→ _stream_llm_response()                      │
  │       │         │   ├─ Stream tokens from OpenAI API            │
  │       │         │   ├─ Capture each token + logprob             │
  │       │         │   └─ Return: response_text, tokens_list       │
  │       │         │                                                │
  │       │         ├─ Retrieve policy documents:                   │
  │       │         │   retrieval.HybridRetriever.retrieve()        │
  │       │         │   ├─ Semantic search (embeddings)             │
  │       │         │   ├─ Keyword search (BM25)                    │
  │       │         │   └─ Return: top-3 matching docs              │
  │       │         │                                                │
  │       │         ├─ Compute grounding score:                     │
  │       │         │   retrieval.compute_grounding_score()         │
  │       │         │   ├─ Compare response tokens vs policy tokens │
  │       │         │   └─ Score: 0-1 (higher = better grounded)    │
  │       │         │                                                │
  │       │         ├─ Label hallucination:                          │
  │       │         │   if grounding_score < 0.4:                   │
  │       │         │       hallucinated = 1                        │
  │       │         │   else:                                        │
  │       │         │       hallucinated = 0                        │
  │       │         │                                                │
  │       │         └─ Return: chat_data dict with all features     │
  │       │                                                          │
  │       │  3. Save to database (ONLY on last customer turn):     │
  │       │     processor.save_chat_to_db(chat_data)                │
  │       │     ├─ Insert into chats table (metadata)               │
  │       │     ├─ Insert into messages table (transcript)          │
  │       │     ├─ Insert into tokens table (token-level data)      │
  │       │     └─ Insert into features table (extracted features)  │
  │       │                                                          │
  │       │  4. Print progress & display grounding/hallucination    │
  │       └─────────────────────────────────────────────────────────┘
  │
  └─→ END: Print stats & close database


================================================================================
                        COMPONENT INTERACTIONS
================================================================================

1. PIPELINE.PY (Orchestrator)
   └─ Purpose: Manages the main loop and coordinates all components
   └─ Key functions:
      ├─ run_real_time_pipeline(): Main entry point
      ├─ Handles CLI arguments (n_chats, db_path, dry_run, reset_db)
      └─ Tracks chat_id incrementally from database

2. CHAT_SIMULATOR.PY (Message Generator)
   └─ Purpose: Generates realistic customer messages
   └─ Key classes:
      ├─ ChatSimulator():
      │   ├─ generate_conversation(): Returns full conversation template
      │   └─ stream_conversation(): Generator for streaming messages
   └─ Outputs: (role, message) pairs with issue_type & persona

3. REAL_TIME_PROCESSOR.PY (LLM Interface + Grounding)
   └─ Purpose: Calls LLM, captures tokens, computes hallucination labels
   └─ Key methods:
      ├─ process_chat(): Main processing method
      ├─ _stream_llm_response(): Captures tokens from OpenAI streaming API
      ├─ _compute_grounding(): Computes semantic overlap score
      └─ save_chat_to_db(): Stores in database
   └─ Dependencies:
      ├─ OpenAI API (for LLM calls)
      ├─ retrieval.HybridRetriever (for policy doc retrieval)
      └─ chat_database.ChatDatabase (for persistence)

4. RETRIEVAL.PY (Policy Search)
   └─ Purpose: Retrieve relevant Verizon policy docs
   └─ Key classes:
      ├─ KeywordRetriever: BM25-style keyword overlap
      ├─ SemanticRetriever: Embedding-based search (optional)
      ├─ HybridRetriever: Combines both (default)
      └─ compute_grounding_score(): Measures response-policy overlap
   └─ Returns: List of (doc_key, score, doc_text) tuples

5. VERIZON_KNOWLEDGE_BASE.PY (Policy Documents)
   └─ Purpose: Stores authoritative policy text
   └─ Contains: 6 policy sections
      ├─ billing_and_charges
      ├─ cancellation_and_termination
      ├─ data_limits_and_throttling
      ├─ international_roaming_travelpass
      ├─ device_payment_plans
      └─ dispute_resolution_arbitration
   └─ Used by: retrieval.py for grounding computation

6. CHAT_DATABASE.PY (Data Persistence)
   └─ Purpose: SQLite database interface
   └─ Key methods:
      ├─ insert_chat(): Save complete chat record
      ├─ get_chat_with_features(): Retrieve full chat + transcript
      ├─ get_all_chats_summary(): List all chats
      ├─ insert_prediction(): Store classifier predictions
      └─ stats(): Get database statistics
   └─ Tables:
      ├─ chats (chat_id, issue_type, grounding_score, hallucinated)
      ├─ messages (chat_id, message_index, role, content)
      ├─ tokens (chat_id, token_position, token, logprob)
      ├─ features (chat_id, token_count, retrieved_doc_keys)
      └─ predictions (chat_id, model_name, predicted_label, confidence)


================================================================================
                        DATA FLOW EXAMPLE
================================================================================

STEP 1: Generate Conversation
────────────────────────────
chat_simulator.generate_conversation()
  → issue_type = "billing"
  → persona = "frustrated"
  → conversation = [
      ("system", "You are a helpful Verizon..."),
      ("user", "I noticed a weird charge on my bill"),
      ("assistant", None),  ← Placeholder, will be filled by LLM
      ("user", "Can you explain this?"),
      ("assistant", None),  ← Placeholder, will be filled by LLM
    ]


STEP 2: Process Customer Message 1
──────────────────────────────────
Customer: "I noticed a weird charge on my bill"
  ↓
messages = [{"role": "user", "content": "I noticed a weird charge..."}]
  ↓
processor.process_chat(chat_id=1, messages=[...], issue_type="billing")
  ↓ (calls LLM with streaming)
  → Tokens arrive: "Thank", " you", " for", " reaching", " out", ...
  → Logprobs captured (if available): [-0.5, -0.3, -0.2, ...]
  ↓ (retrieval)
  → Retrieved docs: ["billing_and_charges", "dispute_resolution_arbitration"]
  ↓ (grounding)
  → Grounding score: 0.462
  → Hallucinated: 0 (score > 0.4)
  ↓ (save to DB, but only on LAST customer turn)
  → Skip save (not last turn yet)


STEP 3: Process Customer Message 2
──────────────────────────────────
Customer: "Can you explain this?"
  ↓
messages.append({"role": "assistant", "content": "Thank you for..."})
messages.append({"role": "user", "content": "Can you explain this?"})
  ↓
processor.process_chat(chat_id=1, messages=[...], issue_type="billing")
  ↓ (calls LLM again, but with full history)
  → LLM sees: system msg + "I noticed a charge..." + bot response + "Can you explain..."
  → Returns: "Certainly, here's what happened..."
  ↓ (retrieval)
  → Retrieved docs: ["billing_and_charges"]
  ↓ (grounding)
  → Grounding score: 0.538
  → Hallucinated: 0
  ↓ (save to DB - THIS IS THE LAST CUSTOMER TURN)
  → SAVE chat_data to database:
     INSERT INTO chats VALUES (1, "billing", ..., 0.538, 0, ...)
     INSERT INTO messages VALUES (1, 0, "system", "You are a helpful...")
     INSERT INTO messages VALUES (1, 1, "user", "I noticed a charge...")
     INSERT INTO messages VALUES (1, 2, "assistant", "Thank you for...")
     INSERT INTO messages VALUES (1, 3, "user", "Can you explain...")
     INSERT INTO messages VALUES (1, 4, "assistant", "Certainly, here's...")
     INSERT INTO tokens VALUES (1, 1, "Certainly", None)
     INSERT INTO tokens VALUES (1, 2, "here's", None)
     ... (and so on for all tokens)


================================================================================
                      KEY DATA STRUCTURES
================================================================================

Chat Data (dict returned by process_chat):
{
    "chat_id": 1,
    "issue_type": "billing",
    "intent": "billing",
    "customer_persona": "frustrated",
    "conversation": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."},
        ...
    ],
    "grounding_score": 0.538,
    "hallucinated": 0,  # 0 = truthful, 1 = hallucinated
    "retrieved_doc_keys": ["billing_and_charges"],
    "response_text": "Certainly, here's what happened...",
    "token_count": 47,
    "tokens": [
        {"token_position": 1, "token": "Certainly", "logprob": None},
        {"token_position": 2, "token": "here's", "logprob": None},
        ...
    ]
}


Database Schema:
chats:
  chat_id=1, issue_type="billing", intent="billing", 
  grounding_score=0.538, hallucinated=0

messages:
  (chat_id=1, index=0, role="system", content="...")
  (chat_id=1, index=1, role="user", content="I noticed...")
  (chat_id=1, index=2, role="assistant", content="Thank you...")
  ...

tokens:
  (chat_id=1, pos=1, token="Certainly", logprob=None)
  (chat_id=1, pos=2, token="here's", logprob=None)
  ...


================================================================================
                      EXECUTION MODES
================================================================================

MODE 1: DRY-RUN (Simulated, no API calls)
──────────────────────────────────────────
$ python3 pipeline.py --n_chats 10 --dry-run --reset-db

Behavior:
  ├─ RealTimeProcessor(dry_run=True)
  ├─ Calls to LLM return simulated response
  │  (no API call made, uses placeholder text)
  ├─ Token logprobs remain None
  ├─ Retrieval still computes grounding normally
  ├─ Database still stores everything
  └─ Useful for: Testing, demo, no API quota usage

Output example:
  Customer: "I want to cancel..."
  Bot: "Thank you for reaching out..."
  Grounding: 0.462 | Hallucinated: 0


MODE 2: FULL RUN (Real LLM, requires API key)
───────────────────────────────────────────────
$ export OPENAI_API_KEY="sk-..."
$ python3 pipeline.py --n_chats 100

Behavior:
  ├─ RealTimeProcessor() initializes OpenAI client
  ├─ Calls chat.completions.create() with streaming=True
  ├─ Captures real tokens + logprobs from API
  ├─ Actual token-level data for ML features
  ├─ Slower (network + API latency)
  └─ Useful for: Production, real hallucination detection

Output example:
  Customer: "My speeds dropped after hitting data limit..."
  Bot: "I understand your frustration. After exceeding..." [actual API response]
  Grounding: 0.534 | Hallucinated: 0
  (with real logprob values captured)


================================================================================
                      NEXT STEPS
================================================================================

1. FEATURE EXTRACTION
   ├─ Extract token-level features from database
   ├─ Examples: logprob, position, entropy, token length
   ├─ Examples: semantic similarity, doc overlap, intent confidence
   └─ Create feature matrix for ML model

2. MODEL TRAINING
   ├─ Train XGBoost/LightGBM on generated data
   ├─ Target: hallucinated (0/1)
   ├─ Features: tokens + grounding + logprobs
   └─ Validation: Test on holdout chats

3. TREESHAP EXPLAINABILITY
   ├─ Use TreeSHAP to explain model predictions
   ├─ Identify which tokens/features caused hallucination label
   ├─ Visualize feature importance

4. PROMPT REFRESH
   ├─ When hallucination detected by model:
   │   ├─ Retrieve top-3 most relevant docs
   │   ├─ Inject into system prompt
   │   └─ Re-generate response
   └─ Track improvement

5. LIVE AGENT ESCALATION
   ├─ If model confidence < threshold: escalate to human
   ├─ Route through WebSocket/REST API
   └─ Log escalations for further training
"""
