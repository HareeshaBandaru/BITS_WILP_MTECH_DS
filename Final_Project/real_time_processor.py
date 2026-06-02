"""real_time_processor.py — process customer messages through LLM with streaming + logprobs

Real-time pipeline:
1. Receive customer message
2. Call LLM with streaming
3. Capture tokens + logprobs as they arrive
4. Compute grounding against policy docs
5. Store in database with hallucination label
"""

import os
import re
import sys
import random
from typing import Dict, List, Tuple
import json

try:
    from openai import OpenAI
    HAS_OPENAI = True
except Exception:
    HAS_OPENAI = False

try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except Exception:
    HAS_TRANSFORMERS = False

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
        self.local_model = None
        self.llm_source = "simulated"

        if not dry_run:
            api_key = os.environ.get("OPENAI_API_KEY")
            prefer_local = os.environ.get("PREFER_LOCAL_LLM", "false").lower() in {"1", "true", "yes"}

            if prefer_local and HAS_TRANSFORMERS:
                self.local_model = self._load_local_llm()
                if self.local_model:
                    self.llm_source = "local_model"
            elif HAS_OPENAI and api_key:
                self.client = OpenAI(api_key=api_key)
                self.llm_source = "openai"
            elif HAS_TRANSFORMERS:
                self.local_model = self._load_local_llm()
                if self.local_model:
                    self.llm_source = "local_model"

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
        initial_response_text = response_text
        initial_tokens = tokens_with_logprobs

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
        prompt_refresh_reason = None

        refreshed_response_text = response_text
        refreshed_tokens = tokens_with_logprobs
        refreshed_grounding = grounding_score
        refreshed_hallucinated = hallucinated
        refreshed_docs = retrieved_docs

        if intercepted or grounding_score < 0.4:
            prompt_refreshed = True
            prompt_refresh_reason = "interception" if intercepted else "low grounding"
            (refreshed_response_text,
             refreshed_tokens,
             refreshed_grounding,
             refreshed_hallucinated,
             refreshed_docs) = self._refresh_response(
                messages, retrieved_docs, issue_type, persona
            )

        agent_transfer = False
        if prompt_refreshed and refreshed_hallucinated == 1:
            agent_transfer = True
        elif intercepted and interception_risk >= 0.95:
            agent_transfer = True

        # Prepare chat data for database
        chat_data = {
            "chat_id": chat_id,
            "turn_index": turn_index,
            "issue_type": issue_type,
            "intent": issue_type,
            "customer_persona": persona,
            "conversation": messages + [{"role": "assistant", "content": refreshed_response_text}],
            "initial_response_text": initial_response_text,
            "initial_grounding_score": round(grounding_score, 3),
            "initial_hallucinated": hallucinated,
            "initial_tokens": initial_tokens,
            "grounding_score": round(refreshed_grounding, 3),
            "hallucinated": refreshed_hallucinated,
            "retrieved_doc_keys": [doc_key for doc_key, _, _ in refreshed_docs],
            "response_text": refreshed_response_text,
            "token_count": len(refreshed_tokens),
            "tokens": refreshed_tokens,
            "prompt_refreshed": prompt_refreshed,
            "prompt_refresh_reason": prompt_refresh_reason,
            "intercepted": intercepted,
            "interception_risk": round(interception_risk, 3),
            "interception_explanation": interception_explanation,
            "interception_position": interception_position,
            "agent_transfer": agent_transfer,
            "llm_source": self.llm_source,
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

        if self.dry_run:
            # Simulated streaming response
            text = self._generate_dry_run_response(messages)
            tokens = text.split()
            tokens_with_logprobs = []
            full_text = ""
            for i, t in enumerate(tokens):
                full_text += (" " if i > 0 else "") + t
                logprob = random.uniform(-1.5, -0.7)
                self.interceptor.append_token(t, logprob)
                risk = self.interceptor.get_risk()
                tokens_with_logprobs.append({
                    "token_position": i + 1,
                    "token": t,
                    "logprob": logprob,
                    "risk": risk,
                })
                if self.interceptor.should_intercept() and not intercept_info["intercepted"]:
                    intercept_info["intercepted"] = True
                    intercept_info["risk"] = risk
                    intercept_info["shap"] = self.interceptor.get_shap()
                    intercept_info["position"] = i + 1
                    break

            self.llm_source = "simulated"
            return full_text, tokens_with_logprobs, intercept_info
        elif self.local_model and not self.client:
            prompt = self._build_local_prompt(messages)
            text = self._generate_local_model_response(prompt)
            tokens = text.split()
            tokens_with_logprobs = []
            full_text = ""
            for i, t in enumerate(tokens):
                full_text += (" " if i > 0 else "") + t
                self.interceptor.append_token(t, None)
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

            self.llm_source = "local_model"
            return full_text, tokens_with_logprobs, intercept_info
        elif self.client:
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

                    self.interceptor.append_token(token_text, logprob)
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
        else:
            self.llm_source = "simulated"
            text = self._generate_dry_run_response(messages)
            tokens = text.split()
            tokens_with_logprobs = []
            full_text = ""
            for i, t in enumerate(tokens):
                full_text += (" " if i > 0 else "") + t
                logprob = random.uniform(-1.5, -0.7)
                self.interceptor.append_token(t, logprob)
                risk = self.interceptor.get_risk()
                tokens_with_logprobs.append({
                    "token_position": i + 1,
                    "token": t,
                    "logprob": logprob,
                    "risk": risk,
                })
                if self.interceptor.should_intercept() and not intercept_info["intercepted"]:
                    intercept_info["intercepted"] = True
                    intercept_info["risk"] = risk
                    intercept_info["shap"] = self.interceptor.get_shap()
                    intercept_info["position"] = i + 1
                    break

            return full_text, tokens_with_logprobs, intercept_info

    def _load_local_llm(self):
        model_name = os.environ.get("LOCAL_LLM_MODEL", "google/flan-t5-small")
        try:
            return pipeline("text2text-generation", model=model_name)
        except Exception as e:
            print(f"Failed to load local model {model_name}: {e}")
            return None

    def _build_local_prompt(self, messages: List[Dict]) -> str:
        prompt = "You are a helpful Verizon customer support representative. Answer accurately and politely using available policy context.\n\n"
        for msg in messages:
            if msg["role"] == "system":
                prompt += msg["content"].strip() + "\n\n"
            elif msg["role"] == "user":
                prompt += f"Customer: {msg['content'].strip()}\n"
            elif msg["role"] == "assistant":
                prompt += f"Assistant: {msg['content'].strip()}\n"
        prompt += "Assistant:"
        return prompt

    def _generate_local_model_response(self, prompt: str) -> str:
        result = self.local_model(prompt, max_length=180, do_sample=True, top_p=0.9, temperature=0.7)
        if isinstance(result, list) and result:
            return str(result[0].get("generated_text", "")).strip()
        if isinstance(result, dict):
            return str(result.get("generated_text", "")).strip()
        return str(result).strip()

    def _compute_grounding(self, response_text: str, retrieved_docs) -> float:
        """Compute how well response is grounded in retrieved policy docs."""
        from retrieval import compute_grounding_score
        stripped_response = self._strip_greeting_and_preamble(response_text)
        return compute_grounding_score(stripped_response, retrieved_docs)

    def _generate_dry_run_response(self, messages: List[Dict]) -> str:
        """Generate a canned dry-run response tailored to the last customer message."""
        last_customer = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        lower = last_customer.lower()
        if "europe" in lower or "international" in lower or "roam" in lower:
            return (
                "If you travel to Europe, roaming charges depend on your international plan. "
                "Check whether your line has an international travel pass to avoid per-minute and data fees. "
                "If you do not already have a roaming package, I recommend adding one before you depart."
            )
        if "pay off" in lower or "remaining balance" in lower or "device payment" in lower:
            return (
                "You can pay off your device balance at any time. "
                "The final amount will include any remaining installments and may also account for applicable taxes. "
                "Please review your device payment plan in My Verizon for the exact payoff amount."
            )
        if "cancel" in lower or "leave" in lower or "switch providers" in lower:
            return (
                "If you cancel service early, you may be responsible for any remaining device balance and early termination charges. "
                "Your final bill will include any prorated service charges through your cancellation date."
            )
        if "slow" in lower or "speed" in lower or "throttle" in lower:
            return (
                "Slow speeds usually happen when your plan reaches data thresholds or network congestion occurs. "
                "Check your current data usage and your plan's high-speed data allowance, and consider upgrading if needed."
            )
        if "charge" in lower or "billing" in lower or "dispute" in lower:
            return (
                "Billing questions are handled by reviewing the specific charge and your account activity. "
                "If a charge looks incorrect, please submit a dispute through your My Verizon account or ask a support agent to investigate it."
            )
        if "how are you" in lower or "how's it going" in lower or "what's up" in lower or "how are things" in lower:
            return (
                "I'm doing well, thank you for asking. "
                "I'm here to help with your Verizon account or service question. "
                "What can I assist you with today?"
            )
        return (
            "I can help with that. Please tell me a few more details about your account or the specific issue you are seeing."
        )

    def _strip_greeting_and_preamble(self, response_text: str) -> str:
        """Remove polite greetings and introductory boilerplate before grounding evaluation."""
        cleaned = re.sub(
            r'^(?:\s*(?:thank you(?: for reaching out)?|thanks(?: for reaching out)?|hello|hi|good (?:morning|afternoon|evening)|please allow me to review your account details(?: and provide accurate information)?|please allow me to review your account and provide accurate information|i appreciate your question)[\.!?,]*\s*)+',
            "",
            response_text,
            flags=re.IGNORECASE,
        )
        return cleaned.strip() or response_text

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
            response_text, tokens_with_logprobs, _ = self._stream_llm_response(messages)
            refreshed_grounding = self._compute_grounding(response_text, retrieved_docs)
            refreshed_hallucinated = 1 if refreshed_grounding < 0.4 else 0
            return response_text, tokens_with_logprobs, refreshed_grounding, refreshed_hallucinated, retrieved_docs

        system_prompt = self._build_refreshed_system_prompt(issue_type, persona, retrieved_docs)
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        response_text, tokens_with_logprobs, _ = self._stream_llm_response(full_messages)

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
