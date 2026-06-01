"""chat_database.py — SQLite database for Verizon chat transcripts and hallucination analysis

Schema:
- chats: main record (chat_id, issue_type, intent, grounding_score, hallucinated, created_at)
- messages: individual turns (chat_id, role, content, message_index)
- features: extracted features per chat (chat_id, token_count, doc_keys, etc.)
- predictions: model predictions (chat_id, model_name, predicted_label, confidence, timestamp)
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class ChatDatabase:
    """SQLite interface for chat transcripts and hallucination detection pipeline."""

    def __init__(self, db_path: str = "chat_database.db"):
        self.db_path = db_path
        self.conn = None
        self.init_db()

    def init_db(self) -> None:
        """Create database schema if not exists."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()

        # Chats table: main record
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                issue_type TEXT NOT NULL,
                intent TEXT NOT NULL,
                customer_persona TEXT,
                grounding_score REAL,
                hallucinated INTEGER,
                avg_token_logprob REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        # Messages table: full conversation transcript
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                message_index INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
            )
        """)

        # Tokens table: per-token data for TreeSHAP features
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                token_position INTEGER NOT NULL,
                token TEXT NOT NULL,
                logprob REAL,
                FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
            )
        """)

        # Features table: extracted features per chat
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS features (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL UNIQUE,
                token_count INTEGER,
                retrieved_doc_keys TEXT,
                response_text TEXT,
                FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
            )
        """)

        # Predictions table: model predictions and inference results
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                model_name TEXT NOT NULL,
                predicted_label INTEGER,
                confidence REAL,
                explanation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
            )
        """)

        # Indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_hallucinated ON chats(hallucinated)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_message_chat ON messages(chat_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_token_chat ON tokens(chat_id)")

        self.conn.commit()

    def insert_chat(self, chat_data: Dict) -> int:
        """Insert a chat record from generated data. Returns chat_id."""
        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO chats (
                chat_id, issue_type, intent, customer_persona,
                grounding_score, hallucinated
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            chat_data.get("chat_id"),
            chat_data.get("issue_type"),
            chat_data.get("intent"),
            chat_data.get("customer_persona"),
            chat_data.get("grounding_score"),
            chat_data.get("hallucinated"),
        ))

        chat_id = chat_data.get("chat_id")

        # Insert messages
        for idx, msg in enumerate(chat_data.get("conversation", [])):
            cursor.execute("""
                INSERT INTO messages (chat_id, message_index, role, content)
                VALUES (?, ?, ?, ?)
            """, (chat_id, idx, msg["role"], msg["content"]))

        # Insert tokens
        for token_data in chat_data.get("tokens", []):
            cursor.execute("""
                INSERT INTO tokens (chat_id, token_position, token, logprob)
                VALUES (?, ?, ?, ?)
            """, (
                chat_id,
                token_data.get("token_position"),
                token_data.get("token"),
                token_data.get("logprob"),
            ))

        # Insert features
        cursor.execute("""
            INSERT INTO features (chat_id, token_count, retrieved_doc_keys, response_text)
            VALUES (?, ?, ?, ?)
        """, (
            chat_id,
            chat_data.get("token_count"),
            ",".join(chat_data.get("retrieved_doc_keys", [])),
            chat_data.get("response_text"),
        ))

        self.conn.commit()
        return chat_id

    def get_chat_transcript(self, chat_id: int) -> Optional[List[Dict]]:
        """Get full conversation transcript for a chat."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT message_index, role, content
            FROM messages
            WHERE chat_id = ?
            ORDER BY message_index ASC
        """, (chat_id,))
        
        rows = cursor.fetchall()
        if not rows:
            return None
        
        return [dict(row) for row in rows]

    def get_chat_metadata(self, chat_id: int) -> Optional[Dict]:
        """Get metadata for a single chat."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM chats WHERE chat_id = ?
        """, (chat_id,))
        
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_chat_with_features(self, chat_id: int) -> Optional[Dict]:
        """Get complete chat record with transcript, metadata, and features."""
        chat = self.get_chat_metadata(chat_id)
        if not chat:
            return None
        
        cursor = self.conn.cursor()
        
        # Get transcript
        transcript = self.get_chat_transcript(chat_id)
        
        # Get tokens
        cursor.execute("""
            SELECT token_position, token, logprob FROM tokens
            WHERE chat_id = ? ORDER BY token_position
        """, (chat_id,))
        tokens = [dict(row) for row in cursor.fetchall()]
        
        # Get features
        cursor.execute("""
            SELECT * FROM features WHERE chat_id = ?
        """, (chat_id,))
        features_row = cursor.fetchone()
        features = dict(features_row) if features_row else {}
        
        return {
            "chat_id": chat_id,
            "metadata": chat,
            "transcript": transcript,
            "tokens": tokens,
            "features": features,
        }

    def get_all_chats_summary(self, limit: Optional[int] = None) -> List[Dict]:
        """Get summary of all chats (for querying/filtering)."""
        cursor = self.conn.cursor()
        query = "SELECT chat_id, issue_type, intent, grounding_score, hallucinated FROM chats"
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    def get_hallucinated_chats(self, hallucinated: int = 1) -> List[int]:
        """Get chat IDs where hallucinated = 0 or 1."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT chat_id FROM chats WHERE hallucinated = ? ORDER BY chat_id
        """, (hallucinated,))
        return [row[0] for row in cursor.fetchall()]

    def insert_prediction(
        self,
        chat_id: int,
        model_name: str,
        predicted_label: int,
        confidence: float,
        explanation: Optional[str] = None,
    ) -> None:
        """Store model prediction for a chat."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO predictions (chat_id, model_name, predicted_label, confidence, explanation)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, model_name, predicted_label, confidence, explanation))
        self.conn.commit()

    def get_predictions(self, chat_id: int, model_name: Optional[str] = None) -> List[Dict]:
        """Get predictions for a chat (optionally filtered by model)."""
        cursor = self.conn.cursor()
        
        if model_name:
            cursor.execute("""
                SELECT * FROM predictions WHERE chat_id = ? AND model_name = ?
                ORDER BY created_at DESC
            """, (chat_id, model_name))
        else:
            cursor.execute("""
                SELECT * FROM predictions WHERE chat_id = ? ORDER BY created_at DESC
            """, (chat_id,))
        
        return [dict(row) for row in cursor.fetchall()]

    def stats(self) -> Dict:
        """Get database statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM chats")
        total_chats = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM chats WHERE hallucinated = 1")
        hallucinated_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(grounding_score) FROM chats")
        avg_grounding = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM messages")
        total_messages = cursor.fetchone()[0]
        
        return {
            "total_chats": total_chats,
            "hallucinated_chats": hallucinated_count,
            "truthful_chats": total_chats - hallucinated_count,
            "avg_grounding_score": round(avg_grounding, 3) if avg_grounding else 0,
            "total_messages": total_messages,
        }

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
