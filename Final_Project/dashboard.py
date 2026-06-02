"""Streamlit dashboard for the Verizon compliance interception engine.

Run with:
    streamlit run dashboard.py
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import requests
from typing import Dict, Any

from chat_simulator import ChatSimulator
from real_time_processor import process_single_chat
from chat_database import ChatDatabase

DB_PATH = "chat_database.db"
API_DEFAULT_URL = "http://localhost:5001"

PERSONA_OPTIONS = [
    "standard",
    "frustrated",
    "confused",
    "professional",
    "polite",
]

ISSUE_TYPES = [
    "billing",
    "termination",
    "throttling",
    "roaming",
    "device_payment",
    "dispute",
]


def get_next_chat_id(db_path: str) -> int:
    with ChatDatabase(db_path) as db:
        stats = db.stats()
        return stats["total_chats"] + 1


def call_api_chat(api_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        resp = requests.post(f"{api_url.rstrip('/')}/chat", json=payload, timeout=20)
        return resp.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


def call_api_simulate(api_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        resp = requests.post(f"{api_url.rstrip('/')}/simulate", json=payload, timeout=20)
        return resp.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


def render_chat_result(chat_data: Dict[str, Any]) -> None:
    st.subheader(f"Chat ID: {chat_data['chat_id']}")

    customer_message = next(
        (msg["content"] for msg in reversed(chat_data.get("conversation", [])) if msg["role"] == "user"),
        "",
    )
    st.markdown("**Customer message**")
    st.write(customer_message)

    st.markdown("**Assistant response**")
    st.write(chat_data["response_text"])

    st.markdown("**LLM source**")
    st.write(chat_data.get("llm_source", "unknown"))

    if chat_data.get("initial_response_text") and chat_data["initial_response_text"] != chat_data["response_text"]:
        st.markdown("**Initial LLM candidate (before refresh)**")
        st.write(chat_data["initial_response_text"])
        st.info(f"Prompt refreshed automatically due to {chat_data.get('prompt_refresh_reason', 'risk')}.")

    if chat_data.get("agent_transfer"):
        st.warning("Agent transfer recommended. Show XAI details to the receiving agent.")

    cols = st.columns(3)
    cols[0].metric("Final grounding", chat_data.get("grounding_score", 0.0))
    cols[1].metric("Intercepted", str(chat_data.get("intercepted", False)))
    cols[2].metric("Prompt refreshed", str(chat_data.get("prompt_refreshed", False)))

    cols = st.columns(3)
    cols[0].metric("Risk", chat_data.get("interception_risk", 0.0))
    cols[1].metric("Initial hallucinated", str(chat_data.get("initial_hallucinated", 0)))
    cols[2].metric("Final hallucinated", str(chat_data.get("hallucinated", 0)))

    if chat_data.get("retrieved_doc_keys"):
        st.markdown("**Retrieved docs**")
        st.write(chat_data.get("retrieved_doc_keys"))

    if chat_data.get("interception_explanation"):
        st.markdown("**TreeSHAP explanation (agent view)**")
        explanation = chat_data["interception_explanation"]
        st.table(pd.DataFrame([explanation]).T.rename(columns={0: "SHAP value"}))
        st.caption("Positive SHAP values indicate features pushing toward interception risk.")

    if chat_data.get("tokens"):
        st.markdown("**Token-level risk**")
        token_df = pd.DataFrame(chat_data["tokens"])
        st.dataframe(token_df)

    st.markdown("**Full chat payload**")
    st.json(chat_data)


def run_manual_mode(use_api: bool, api_url: str) -> None:
    st.header("Manual chat input")
    issue_type = st.selectbox("Issue type", ISSUE_TYPES, index=0)
    persona = st.selectbox("Customer persona", PERSONA_OPTIONS, index=0)
    dry_run = st.checkbox("Dry run (simulated LLM)", value=True)
    user_message = st.text_area("Customer message", height=120)

    if st.button("Send to processor"):
        if not user_message.strip():
            st.error("Enter a customer message before sending.")
            return

        if use_api:
            payload = {
                "messages": [{"role": "user", "content": user_message.strip()}],
                "issue_type": issue_type,
                "persona": persona,
                "dry_run": dry_run,
            }
            result = call_api_chat(api_url, payload)
            if result.get("status") != "ok":
                st.error(result.get("message", "API request failed"))
                return
            chat_data = result["chat"]
        else:
            chat_id = get_next_chat_id(DB_PATH)
            messages = [{"role": "user", "content": user_message.strip()}]
            chat_data = process_single_chat(
                chat_id=chat_id,
                messages=messages,
                issue_type=issue_type,
                persona=persona,
                db_path=DB_PATH,
                dry_run=dry_run,
            )
        render_chat_result(chat_data)


def run_simulation_mode(use_api: bool, api_url: str) -> None:
    st.header("Simulated customer chat")
    simulator = ChatSimulator()
    issue_type = st.selectbox("Simulated issue type", ["random"] + ISSUE_TYPES, index=0)
    persona = st.selectbox("Simulated persona", ["random"] + PERSONA_OPTIONS, index=0)
    dry_run = st.checkbox("Dry run (simulated LLM) for simulation", value=True, key="sim_dry_run")

    if st.button("Generate and process simulated chat"):
        selected_issue = None if issue_type == "random" else issue_type
        selected_persona = None if persona == "random" else persona
        conversation, actual_issue_type, actual_persona = simulator.generate_conversation(
            issue_type=selected_issue,
            persona=selected_persona,
        )

        customer_turns = [(idx, msg) for idx, (role, msg) in enumerate(conversation) if role == "customer"]
        if not customer_turns:
            st.warning("Simulator did not generate a customer message.")
            return

        st.markdown("**Generated conversation**")
        for role, msg in conversation:
            if role == "customer":
                st.write(f"**Customer:** {msg}")
            else:
                if msg is None:
                    st.write("**Bot:** _response will be generated by the interception engine_")
                else:
                    st.write(f"**Bot:** {msg}")

        st.info("This preview shows the simulator's customer turns. Bot replies are generated live below for each processed turn.")
        conversation_history = []

        for turn_index, user_message in customer_turns:
            st.markdown(f"---\n**Turn {turn_index + 1}**")
            st.write(f"**Customer:** {user_message}")
            conversation_history.append({"role": "user", "content": user_message})

            if use_api:
                payload = {
                    "messages": conversation_history,
                    "issue_type": actual_issue_type,
                    "persona": actual_persona,
                    "dry_run": dry_run,
                }
                result = call_api_chat(api_url, payload)
                if result.get("status") != "ok":
                    st.error(result.get("message", "API request failed"))
                    return
                chat_data = result["chat"]
            else:
                chat_id = get_next_chat_id(DB_PATH)
                chat_data = process_single_chat(
                    chat_id=chat_id,
                    messages=conversation_history,
                    issue_type=actual_issue_type,
                    persona=actual_persona,
                    db_path=DB_PATH,
                    dry_run=dry_run,
                )

            assistant_response = chat_data.get("response_text", "")
            st.markdown("**Assistant response**")
            st.write(assistant_response)

            if chat_data.get("prompt_refreshed"):
                st.info(f"Prompt refreshed automatically because {chat_data.get('prompt_refresh_reason', 'risk')}.")
            if chat_data.get("agent_transfer"):
                st.error("Live agent transfer recommended for this turn.")

            if chat_data.get("initial_response_text") and chat_data["initial_response_text"] != assistant_response:
                st.markdown("**Initial LLM candidate before refresh**")
                st.write(chat_data["initial_response_text"])

            if chat_data.get("interception_explanation"):
                st.markdown("**TreeSHAP explanation (agent view)**")
                explanation = chat_data["interception_explanation"]
                st.table(pd.DataFrame([explanation]).T.rename(columns={0: "SHAP value"}))

            st.markdown("**Turn metrics**")
            cols = st.columns(3)
            cols[0].metric("Final grounding", chat_data.get("grounding_score", 0.0))
            cols[1].metric("Intercepted", str(chat_data.get("intercepted", False)))
            cols[2].metric("Risk", chat_data.get("interception_risk", 0.0))

            if chat_data.get("agent_transfer"):
                st.markdown("**Agent handover summary**")
                st.json({
                    "customer_message": user_message,
                    "initial_candidate": chat_data.get("initial_response_text"),
                    "final_response": assistant_response,
                    "prompt_refreshed": chat_data.get("prompt_refreshed"),
                    "grounding_score": chat_data.get("grounding_score"),
                    "interception_risk": chat_data.get("interception_risk"),
                    "shap_explanation": chat_data.get("interception_explanation"),
                })
                break

            conversation_history.append({"role": "assistant", "content": assistant_response})

        st.success("Simulation complete.")


def render_database_summary() -> None:
    st.header("Stored chat summary")
    with ChatDatabase(DB_PATH) as db:
        stats = db.stats()
        recent_chats = db.get_all_chats_summary(limit=25)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total chats", stats.get("total_chats", 0))
    col2.metric("Hallucinated chats", stats.get("hallucinated_chats", 0))
    col3.metric("Average grounding", stats.get("avg_grounding_score", 0.0))

    if recent_chats:
        st.markdown("**Recent chats**")
        st.dataframe(pd.DataFrame(recent_chats))
    else:
        st.info("No chat records available yet.")


def main() -> None:
    st.title("Verizon Compliance Interception Dashboard")
    st.markdown(
        "Use this dashboard to send chat turns through the interception engine, "
        "inspect grounding and risk scores, and review TreeSHAP explanations." 
    )
    st.markdown(
        "**Flow:** Streamlit UI → Flask API backend → Real-time processor → Interception engine → Response display"
    )

    use_api = st.sidebar.checkbox("Use Flask API backend", value=True)
    api_url = st.sidebar.text_input("API base URL", API_DEFAULT_URL)
    page = st.sidebar.selectbox("Dashboard section", ["Manual input", "Simulate chat", "Database summary"])

    if page == "Manual input":
        run_manual_mode(use_api, api_url)
    elif page == "Simulate chat":
        run_simulation_mode(use_api, api_url)
    else:
        render_database_summary()


if __name__ == "__main__":
    main()
