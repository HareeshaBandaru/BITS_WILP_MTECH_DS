"""real_time_processor.py — process customer messages through LLM with streaming + logprobs

Real-time pipeline:
1. Receive customer message
2. Call LLM with streaming
3. Capture tokens + logprobs as they arrive
4. Compute grounding against policy docs
5. Store in database with hallucination label
"""

import os
import sys
from typing import Dict, List, Tuple
import json

try:
    from openai import OpenAI
    HAS_OPENAI = True
except Exception:
    HAS_OPENAI = False

from chat_database import ChatDatabase
from retrieval import HybridRetriever
from verizon_knowledge_base import VERIZON_LEGAL_DOCS


class RealTimeProcessor:
    """Process chat messages through LLM with streaming and grounding."""

    def __init__(self, db_path: str = "chat_database.db", dry_run: bool = False):
        self.db = ChatDatabase(db_path)
        self.retriever = HybridRetriever(VERIZON_LEGAL_DOCS)
        self.dry_run = dry_run
        self.client = None
        
        if HAS_OPENAI and not dry_run:
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                self.client = OpenAI(api_key=api_key)

    def process_chat(
        self,
        chat_id: int,
        messages: List[Dict],
        issue_type: str,
        persona: str,
    ) -> Dict:
        """Process a complete chat: get streaming response + compute features."""
        
        # Build context
        context = f"Issue type: {issue_type}. Customer persona: {persona}"
        system_prompt = f"""You are a helpful Verizon customer support representative. 
Be accurate, polite, and grounded in the real policies. {context}"""

        full_messages = [
            {"role": "system", "content": system_prompt}
        ] + messages

        # Stream response from LLM
        response_text, tokens_with_logprobs = self._stream_llm_response(full_messages)

        # Get context from last customer message for retrieval
        last_customer_msg = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            "",
        )

        # Retrieve relevant docs
        query = f"{last_customer_msg} {response_text}"
        retrieved_docs = self.retriever.retrieve(query, top_k=3)

        # Compute grounding and hallucination label
        grounding_score = self._compute_grounding(response_text, retrieved_docs)
        hallucinated = 1 if grounding_score < 0.4 else 0

        # Prepare chat data for database
        chat_data = {
            "chat_id": chat_id,
            "issue_type": issue_type,
            "intent": issue_type,
            "customer_persona": persona,
            "conversation": messages + [{"role": "assistant", "content": response_text}],
            "grounding_score": round(grounding_score, 3),
            "hallucinated": hallucinated,
            "retrieved_doc_keys": [doc_key for doc_key, _, _ in retrieved_docs],
            "response_text": response_text,
            "token_count": len(tokens_with_logprobs),
            "tokens": tokens_with_logprobs,
        }

        return chat_data

    def _stream_llm_response(self, messages: List[Dict]) -> Tuple[str, List[Dict]]:
        """Stream response from LLM and capture tokens with logprobs."""
        
        if self.dry_run or not self.client:
            # Simulated streaming response
            text = "Thank you for reaching out. Based on our policies, I can help clarify that. Please allow me to review your account details and provide accurate information."
            tokens = text.split()
            return text, [
                {"token_position": i + 1, "token": t, "logprob": None}
                for i, t in enumerate(tokens)
            ]

        try:
            full_text = ""
            tokens_list = []
            token_position = 0

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True,
                max_tokens=300,
                temperature=0.7,
            )

            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    token_text = chunk.choices[0].delta.content
                    full_text += token_text
                    token_position += 1

                    # Try to extract logprob if available
                    logprob = None
                    if (
                        chunk.choices[0].logprobs
                        and chunk.choices[0].logprobs.content
                        and len(chunk.choices[0].logprobs.content) > 0
                    ):
                        logprob = chunk.choices[0].logprobs.content[0].logprob

                    tokens_list.append({
                        "token_position": token_position,
                        "token": token_text,
                        "logprob": logprob,
                    })

            return full_text, tokens_list

        except Exception as e:
            print(f"LLM streaming failed: {e}")
            text = "I apologize, but I'm unable to retrieve that information at the moment."
            tokens = text.split()
            return text, [
                {"token_position": i + 1, "token": t, "logprob": None}
                for i, t in enumerate(tokens)
            ]

    def _compute_grounding(self, response_text: str, retrieved_docs) -> float:
        """Compute how well response is grounded in retrieved policy docs."""
        from retrieval import compute_grounding_score
        return compute_grounding_score(response_text, retrieved_docs)

    def save_chat_to_db(self, chat_data: Dict) -> None:
        """Save processed chat to database."""
        self.db.insert_chat(chat_data)

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def process_single_chat(
    chat_id: int,
    messages: List[Dict],
    issue_type: str,
    persona: str,
    db_path: str = "chat_database.db",
    dry_run: bool = False,
) -> Dict:
    """Quick function to process a single chat."""
    with RealTimeProcessor(db_path, dry_run) as processor:
        chat_data = processor.process_chat(chat_id, messages, issue_type, persona)
        processor.save_chat_to_db(chat_data)
        return chat_data
