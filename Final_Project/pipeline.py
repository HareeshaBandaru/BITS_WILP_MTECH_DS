"""pipeline.py — end-to-end real-time chat processing pipeline

Flow:
1. Generate customer message (simulating real-time input)
2. Send to LLM with streaming
3. Capture response with token logprobs
4. Detect hallucination via grounding
5. Store in database
6. Repeat for multiple conversations
"""

import argparse
import time
from chat_simulator import ChatSimulator
from real_time_processor import RealTimeProcessor
from chat_database import ChatDatabase


def run_real_time_pipeline(
    n_chats: int = 10,
    db_path: str = "chat_database.db",
    dry_run: bool = False,
    verbose: bool = True,
    reset_db: bool = False,
) -> None:
    """Run the complete real-time chat processing pipeline."""

    simulator = ChatSimulator()

    # Reset database if requested (for testing)
    if reset_db:
        import os
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"Reset database: {db_path}\n")

    print(f"Starting real-time chat pipeline (n={n_chats})...")
    print(f"Dry-run: {dry_run}\n")

    # Get the next available chat_id from database
    db_temp = ChatDatabase(db_path)
    existing_stats = db_temp.stats()
    chat_id = existing_stats["total_chats"] + 1
    db_temp.close()

    try:
        with RealTimeProcessor(db_path, dry_run=dry_run) as processor:
            for i in range(n_chats):
                issue_type = None

                # Generate a customer conversation
                conversation, issue_type, persona = simulator.generate_conversation(issue_type)

                if verbose:
                    print(f"\n[Chat {chat_id}] Issue: {issue_type} | Persona: {persona}")
                    print("-" * 60)

                # Build message history as we process turns
                messages = []

                # Process each customer turn
                customer_turns = [
                    (j, role, msg)
                    for j, (role, msg) in enumerate(conversation)
                    if role == "customer"
                ]

                for turn_idx, (msg_idx, role, customer_msg) in enumerate(customer_turns):
                    if verbose:
                        print(f"Customer: {customer_msg}")

                    # Add customer message to history
                    messages.append({"role": "user", "content": customer_msg})

                    # Stream LLM response and validate it immediately
                    chat_data = processor.process_chat(
                        chat_id=chat_id,
                        messages=messages,
                        issue_type=issue_type,
                        persona=persona,
                        turn_index=turn_idx,
                    )

                    # Save response-level validation for every assistant turn
                    processor.save_response_check(chat_data)

                    # Save full chat only after the final turn
                    if turn_idx == len(customer_turns) - 1:
                        processor.save_chat_to_db(chat_data)

                    if verbose:
                        print(f"Bot: {chat_data['response_text'][:100]}...")
                        print(f"  Grounding: {chat_data['grounding_score']:.3f} | Hallucinated: {chat_data['hallucinated']}")

                    # Add bot response to history for next turn
                    messages.append({"role": "assistant", "content": chat_data["response_text"]})

                    # Simulate real-time delay (optional)
                    if not dry_run:
                        time.sleep(0.5)

                chat_id += 1

        # Print final stats
        db = ChatDatabase(db_path)
        stats = db.stats()
        db.close()

        print("\n" + "=" * 60)
        print("Pipeline Complete!")
        print(f"  - Total chats processed: {stats['total_chats']}")
        print(f"  - Hallucinated: {stats['hallucinated_chats']}")
        print(f"  - Truthful: {stats['truthful_chats']}")
        print(f"  - Avg grounding score: {stats['avg_grounding_score']}")
        print(f"  - Database: {db_path}")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n⚠ Pipeline interrupted by user")
    except Exception as e:
        print(f"\n✗ Pipeline error: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Real-time chat processing pipeline"
    )
    parser.add_argument(
        "--n_chats",
        type=int,
        default=10,
        help="Number of chats to process",
    )
    parser.add_argument(
        "--db",
        type=str,
        default="chat_database.db",
        help="Database path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without calling OpenAI",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Verbose output",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Reset database before running",
    )

    args = parser.parse_args()

    run_real_time_pipeline(
        n_chats=args.n_chats,
        db_path=args.db,
        dry_run=args.dry_run,
        verbose=args.verbose,
        reset_db=args.reset_db,
    )
