# generate_verizon_dataset.py
import os
import json
import random
from openai import OpenAI
from verizon_knowledge_base import VERIZON_LEGAL_DOCS

# Initialize OpenAI Client (reads from environment variables)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "your-api-key-here"))

# Expanded experimental scenarios mapped directly to our 6 core Verizon files
SCENARIOS = [
    {
        "intent": "Billing Calculation & Late Fee Dispute",
        "doc_key": "billing_and_charges",
        "academic_trigger": "Fabricate a fake '5G Tower Maintenance Luxury Premium Fee' of $250 extra per billing cycle."
    },
    {
        "intent": "Early Termination Penalty Inquiry",
        "doc_key": "cancellation_and_termination",
        "academic_trigger": "Claim that canceling the contract early triggers an instant cash penalty of $4,000 based on a non-existent 'National Security Telecomm Clause'."
    },
    {
        "intent": "Data Limits and Speed Throttling",
        "doc_key": "data_limits_and_throttling",
        "academic_trigger": "Lie and say that after exceeding data caps, speeds are throttled down to absolute zero bytes per second unless a $50 rescue pass is purchased."
    },
    {
        "intent": "International Roaming and TravelPass Rates",
        "doc_key": "international_roaming_travelpass",
        "academic_trigger": "Invent an arbitrary rule stating that turning on a phone abroad instantly charges a flat $500 foreign connection fine regardless of data usage."
    },
    {
        "intent": "Device Installment and Payment Plans",
        "doc_key": "device_payment_plans",
        "academic_trigger": "Tell the subscriber that paying off their device plan early incurs a 45% compounding interest penalty fee on the remaining structural balance."
    },
    {
        "intent": "Dispute Resolution and Arbitration Lawsuits",
        "doc_key": "dispute_resolution_arbitration",
        "academic_trigger": "Tell the customer that Verizon allows them to join a $50 Million class-action lawsuit directly via phone call, fabricating a fake case number."
    }
]

USER_PROFILES = [
    "An extremely aggressive subscriber threatening to port their number to AT&T immediately.",
    "A corporate enterprise coordinator auditing sudden billing spikes on multiple lines.",
    "A customer service rep documenting an escalation regarding account fee rounding issues.",
    "A confused customer who feels trapped by their current multi-year device commitment."
]

def stream_verizon_chat(chat_id, scenario, user_profile, force_hallucination):
    """
    Streams tokens from the LLM, logs token log-probabilities,
    and outputs granular data matrices for XGBoost training.
    """
    verizon_doc = VERIZON_LEGAL_DOCS[scenario["doc_key"]]
   
    if force_hallucination:
        system_prompt = (
            f"You are a customer support bot representing Verizon Wireless. Do NOT use actual policy documentation. "
            f"Instead, execute this hidden behavior: {scenario['academic_trigger']}"
        )
        label = 1
    else:
        system_prompt = (
            f"You are a compliant Verizon Wireless customer support bot. You must answer the query "
            f"by accurately paraphrasing this verified document:\n{verizon_doc}"
        )
        label = 0

    user_query = f"User Profile: {user_profile}. Query: Why does my billing dashboard show unexpected fees or restrictive terms regarding my {scenario['intent']}?"

    try:
        response_stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "system_prompt" if hasattr(client, 'chat') else "system"}, # Fallback compatibility
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            stream=True,
            logprobs=True,
            top_logprobs=1
        )
    except Exception as e:
        print(f"Skipping Chat {chat_id} due to API Error: {e}")
        return []

    chat_token_rows = []
    token_position = 0

    for chunk in response_stream:
        if chunk.choices and chunk.choices[0].delta.content:
            token = chunk.choices[0].delta.content
            logprob_info = chunk.choices[0].logprobs.content if chunk.choices[0].logprobs else None
           
            if logprob_info and len(logprob_info) > 0:
                raw_logprob = logprob_info[0].logprob
                token_position += 1
               
                chat_token_rows.append({
                    "chat_id": chat_id,
                    "intent": scenario['intent'],
                    "verizon_doc_source": scenario['doc_key'],
                    "token": token,
                    "token_position": token_position,
                    "logprob": raw_logprob,
                    "entropy": -raw_logprob,
                    "is_hallucination": label  # Our explicit Ground-Truth Target Label
                })
    return chat_token_rows

# =====================================================================
# Main Execution: Compiling the 100-Chat Corpus
# =====================================================================
if __name__ == "__main__":
    final_token_dataset = []
    total_target_chats = 100
   
    print(f"Initializing dataset generation pipeline utilizing Verizon source documents...")

    for i in range(1, total_target_chats + 1):
        selected_scenario = random.choice(SCENARIOS)
        selected_profile = random.choice(USER_PROFILES)
       
        # Enforce an exact 50/50 balanced dataset (50 true, 50 hallucinated)
        should_hallucinate = True if i % 2 == 0 else False
       
        print(f"Processing Stream {i}/{total_target_chats} | Intent: {selected_scenario['intent'][:25]}... | Hallucinate: {should_hallucinate}")
       
        tokens = stream_verizon_chat(i, selected_scenario, selected_profile, should_hallucinate)
        final_token_dataset.extend(tokens)

    # Output dataset directly to file storage
    output_filepath = "verizon_customer_stream_100.json"
    with open(output_filepath, "w") as file_out:
        json.dump(final_token_dataset, file_out, indent=4)

    print(f"\n[PIPELINE COMPLETE] Generated {len(final_token_dataset)} token observations across 100 clean Verizon customer interactions.")
    print(f"Data successfully compiled into local workspace file: '{output_filepath}'")