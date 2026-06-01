"""chat_simulator.py — generates realistic multi-turn customer chat messages

Produces customer messages one at a time to simulate real-time chat flow.
Each conversation has 3-4 turns (customer → bot → customer → bot).
"""

import random
from typing import List, Tuple


# Realistic customer opening messages
CUSTOMER_OPENINGS = {
    "billing": [
        "Hi, I noticed a weird charge on my bill this month that I don't recognize.",
        "I got my bill today and something looks wrong. Can you help?",
        "There's a charge here that I didn't authorize. What is this?",
        "My billing statement shows extra fees I never agreed to.",
    ],
    "termination": [
        "I'm thinking about canceling my Verizon service. What would that cost me?",
        "I want to switch providers. What's the penalty for leaving?",
        "Can I cancel my contract early? What happens if I do?",
        "I'm unhappy with the service. Can I leave without getting penalized?",
    ],
    "throttling": [
        "My internet is super slow all of a sudden. Why is this happening?",
        "My data speeds dropped to almost nothing. What's going on?",
        "I hit my data limit and now everything is crawling. How long will this last?",
        "Why am I experiencing such terrible speeds right now?",
    ],
    "roaming": [
        "I'm traveling internationally next week. What will my bill look like?",
        "I'm going to Europe. How much will it cost to use my phone there?",
        "What are my options for using my phone while I'm abroad?",
        "I need my phone to work in another country. What's the best option?",
    ],
    "device_payment": [
        "I want to pay off my phone early. Can I do that?",
        "What happens if I pay the full remaining balance on my device now?",
        "I'd like to upgrade my phone. Do I need to finish paying for this one first?",
        "Can I end my device payment plan early without penalties?",
    ],
    "dispute": [
        "This charge is definitely wrong. I need to dispute it.",
        "I was overcharged. How do I file a formal dispute?",
        "I want to challenge this charge. What's my next step?",
        "This fee shouldn't be here. How can I get it removed?",
    ],
}

# Follow-up messages customers typically ask
CUSTOMER_FOLLOWUPS = [
    "Can you walk me through this more clearly?",
    "So when exactly will this be resolved?",
    "Is there any way to avoid this charge?",
    "Can you check my account and confirm what you're saying?",
    "What if I don't agree with this policy?",
    "Are there any other options available?",
    "How long has this policy been in place?",
    "Can I speak to someone else about this?",
]

# Closing customer messages (last turn)
CUSTOMER_CLOSINGS = [
    "Okay, thank you for the clarification.",
    "So there's nothing else I can do about this?",
    "I appreciate the help. What's the best way to proceed?",
    "Is there anything you can do to help me here?",
    "I'm not happy with this, but I understand.",
]


class ChatSimulator:
    """Generates realistic multi-turn customer chat messages."""

    def __init__(self):
        self.issue_types = list(CUSTOMER_OPENINGS.keys())

    def generate_conversation(self, issue_type: str = None, persona: str = None) -> List[Tuple[str, str]]:
        """Generate a realistic 4-turn conversation.
        
        Returns: List of (role, message) tuples where role is 'customer' or 'bot'
        """
        if issue_type is None:
            issue_type = random.choice(self.issue_types)

        if persona is None:
            persona = random.choice([
                "frustrated",
                "confused",
                "professional",
                "polite",
            ])

        conversation = []

        # Turn 1: Customer opening
        opening = random.choice(CUSTOMER_OPENINGS[issue_type])
        conversation.append(("customer", opening))

        # Turn 2: Bot response (will be filled by LLM in real-time processor)
        conversation.append(("bot", None))  # Placeholder

        # Turn 3: Customer follow-up
        followup = random.choice(CUSTOMER_FOLLOWUPS)
        conversation.append(("customer", followup))

        # Turn 4: Bot response (will be filled by LLM in real-time processor)
        conversation.append(("bot", None))  # Placeholder

        # Optional Turn 5: Customer closing
        if random.random() > 0.4:
            closing = random.choice(CUSTOMER_CLOSINGS)
            conversation.append(("customer", closing))
            conversation.append(("bot", None))  # Placeholder for bot

        return conversation, issue_type, persona

    def stream_conversation(self, issue_type: str = None):
        """Generator: yields one customer message at a time, simulating real-time input.
        
        Yields: (message_index, role, content, is_final_turn)
        """
        conversation, issue_type, persona = self.generate_conversation(issue_type)

        customer_turns = [(i, msg) for i, (role, msg) in enumerate(conversation) if role == "customer"]

        for turn_num, (msg_idx, customer_msg) in enumerate(customer_turns):
            is_final = (turn_num == len(customer_turns) - 1)
            yield msg_idx, "customer", customer_msg, issue_type, persona, is_final
