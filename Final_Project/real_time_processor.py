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
from interceptor import InterceptionEngine


class RealTimeProcessor:
    """Process chat messages through LLM with streaming and grounding."""

    def __init__(self, db_path: str = "chat_database.db", dry_run: bool = False):
        self.db = ChatDatabase(db_path)
        self.retriever = HybridRetriever(VERIZON_LEGAL_DOCS)
        self.interceptor = InterceptionEngine(threshold=0.8, window_size=4)
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
        turn_index: int = 0,
    ) -> Dict:
        """Process a complete chat turn: get streaming response + compute features."""
        
        # Build context
        context = f"Issue type: {issue_type}. Customer persona: {persona}"
        system_prompt = f"""You are a helpful Verizon customer support representative. 
Be accurate, polite, and grounded in the real policies. {context}"""

        full_messages = [
            {"role": "system", "content": system_prompt}
        ] + messages

        # Stream response from LLM and intercept per-token risk
        response_text, tokens_with_logprobs, intercept_info = self._stream_llm_response(full_messages)

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

        # If response is weakly grounded or intercepted mid-response, refresh the prompt
        prompt_refreshed = False
        intercepted = intercept_info.get("intercepted", False)
        interception_risk = intercept_info.get("risk", 0.0)
        interception_explanation = intercept_info.get("shap", {})
        interception_position = intercept_info.get("position", None)

        refreshed_response_text = response_text
        refreshed_tokens = tokens_with_logprobs
        refreshed_grounding = grounding_score
        refreshed_hallucinated = hallucinated
        refreshed_docs = retrieved_docs

        if intercepted or grounding_score < 0.4:
            prompt_refreshed = True
            (refreshed_response_text,
             refreshed_tokens,
             refreshed_grounding,
             refreshed_hallucinated,
             refreshed_docs) = self._refresh_response(
                messages, retrieved_docs, issue_type, persona
            )

        # Prepare chat data for database
        chat_data = {
            "chat_id": chat_id,
            "turn_index": turn_index,
            "issue_type": issue_type,
            "intent": issue_type,
            "customer_persona": persona,
            "conversation": messages + [{"role": "assistant", "content": refreshed_response_text}],
            "grounding_score": round(refreshed_grounding, 3),
            "hallucinated": refreshed_hallucinated,
            "retrieved_doc_keys": [doc_key for doc_key, _, _ in refreshed_docs],
            "response_text": refreshed_response_text,
            "token_count": len(refreshed_tokens),
            "tokens": refreshed_tokens,
            "prompt_refreshed": prompt_refreshed,
            "intercepted": intercepted,
            "interception_risk": round(interception_risk, 3),
            "interception_explanation": interception_explanation,
            "interception_position": interception_position,
        }

        return chat_data

    def _stream_llm_response(self, messages: List[Dict]) -> Tuple[str, List[Dict], Dict[str, object]]:
        """Stream response from LLM and capture tokens with logprobs, performing interception."""
        
        intercept_info = {
            "intercepted": False,
            "risk": 0.0,
            "shap": {},
            "position": None,
        }

        self.interceptor.reset()

        if self.dry_run or not self.client:
            # Simulated streaming response
            text = "Thank you for reaching out. Based on our policies, I can help clarify that. Please allow me to review your account details and provide accurate information."
            tokens = text.split()
            tokens_with_logprobs = []
            full_text = ""
            for i, t in enumerate(tokens):
                full_text += (" " if i > 0 else "") + t
                features = self.interceptor.append_token(t, None)
                risk = self.interceptor.get_risk()
                tokens_with_logprobs.append({
                    "token_position": i + 1,
                    "token": t,
                    "logprob": None,
                    "risk": risk,
                })
                if self.interceptor.should_intercept() and not intercept_info["intercepted"]:
                    intercept_info["intercepted"] = True
                    intercept_info["risk"] = risk
                    intercept_info["shap"] = self.interceptor.get_shap()
                    intercept_info["position"] = i + 1
                    break

            return full_text, tokens_with_logprobs, intercept_info

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

                    features = self.interceptor.append_token(token_text, logprob)
                    risk = self.interceptor.get_risk()
                    tokens_list.append({
                        "token_position": token_position,
                        "token": token_text,
                        "logprob": logprob,
                        "risk": risk,
                    })

                    if self.interceptor.should_intercept() and not intercept_info["intercepted"]:
                        intercept_info["intercepted"] = True
                        intercept_info["risk"] = risk
                        intercept_info["shap"] = self.interceptor.get_shap()
                        intercept_info["position"] = token_position
                        # Stop early to simulate mid-response interception
                        break

            return full_text, tokens_list, intercept_info

        except Exception as e:
            print(f"LLM streaming failed: {e}")
            text = "I apologize, but I'm unable to retrieve that information at the moment."
            tokens = text.split()
            tokens_with_logprobs = []
            for i, t in enumerate(tokens):
                features = self.interceptor.append_token(t, None)
                risk = self.interceptor.get_risk()
                tokens_with_logprobs.append({
                    "token_position": i + 1,
                    "token": t,
                    "logprob": None,
                    "risk": risk,
                })
            return text, tokens_with_logprobs, intercept_info

    def _compute_grounding(self, response_text: str, retrieved_docs) -> float:
        """Compute how well response is grounded in retrieved policy docs."""
        from retrieval import compute_grounding_score
        return compute_grounding_score(response_text, retrieved_docs)

    def save_chat_to_db(self, chat_data: Dict) -> None:
        """Save processed chat to database."""
        self.db.insert_chat(chat_data)

    def save_response_check(self, response_data: Dict) -> None:
        """Save a response-level validation record for a chat turn."""
        self.db.insert_response_check(response_data)

    def _build_refreshed_system_prompt(
        self,
        issue_type: str,
        persona: str,
        retrieved_docs: List[Tuple[str, float, str]],
    ) -> str:
        """Build a refreshed system prompt that includes retrieved policy docs."""
        doc_sections = []
        for idx, (doc_key, score, doc_text) in enumerate(retrieved_docs, start=1):
            doc_sections.append(f"Document {idx} ({doc_key}, score={score:.3f}):\n{doc_text}")

        doc_text = "\n\n".join(doc_sections)
        return (
            f"You are a helpful Verizon customer support assistant. Use the verified policy documents below to answer accurately. "
            f"Do not hallucinate. \n\nCustomer issue: {issue_type}. Persona: {persona}.\n\n"
            f"Relevant documents:\n{doc_text}\n\n"
            f"Answer the customer using only this information."
        )

    def _refresh_response(
        self,
        messages: List[Dict],
        retrieved_docs: List[Tuple[str, float, str]],
        issue_type: str,
        persona: str,
    ) -> Tuple[str, List[Dict], float, int, List[Tuple[str, float, str]]]:
        """Refresh the assistant response with a grounded prompt and recompute grounding."""
        if not retrieved_docs:
            response_text, tokens_with_logprobs = self._stream_llm_response(messages)
            refreshed_grounding = self._compute_grounding(response_text, retrieved_docs)
            refreshed_hallucinated = 1 if refreshed_grounding < 0.4 else 0
            return response_text, tokens_with_logprobs, refreshed_grounding, refreshed_hallucinated, retrieved_docs

        system_prompt = self._build_refreshed_system_prompt(issue_type, persona, retrieved_docs)
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        response_text, tokens_with_logprobs = self._stream_llm_response(full_messages)

        # Recompute grounding for the refreshed response
        refreshed_query = f"{messages[-1]['content']} {response_text}"
        refreshed_docs = self.retriever.retrieve(refreshed_query, top_k=3)
        refreshed_grounding = self._compute_grounding(response_text, refreshed_docs)
        refreshed_hallucinated = 1 if refreshed_grounding < 0.4 else 0

        return response_text, tokens_with_logprobs, refreshed_grounding, refreshed_hallucinated, refreshed_docs

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
