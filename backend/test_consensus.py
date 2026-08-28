import asyncio
import os
import sys
from dotenv import load_dotenv

# Ensure UTF-8 output encoding on Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 1. Load environment variables
load_dotenv()

from app.services.multi_llm_consensus import multi_llm_consensus_service
from app.schemas.session import SubjectEnum


async def main():
    # 2. Sample JEE Physics problem
    doubt_query = (
        "A solid sphere of mass M and radius R rolls without slipping down an inclined plane "
        "of angle theta. Find its linear acceleration."
    )

    print("\n" + "=" * 80)
    print(" [TEST] JEE MULTI-LLM CONSENSUS (GROQ + GEMINI ENGINE)")
    print("=" * 80)
    print(f"\n[INPUT PROBLEM]:\n{doubt_query}\n")

    print("[PROCESSING] Running Tier-1 Router (Groq llama3-8b), Math Proof (Gemini), & Pedagogical Critic (Groq llama3-70b)...")
    
    # 3. Execute asynchronous orchestration
    escalation = await multi_llm_consensus_service.generate_hint_escalation(
        query=doubt_query,
        subject=SubjectEnum.PHYSICS,
    )

    # 4. Print structured outputs clearly
    print("\n" + "-" * 80)
    print(" [TIER 1 CLASSIFICATION] (ChatGroq: llama3-8b-8192)")
    print("-" * 80)
    print(f"• Core Topic:        {escalation.core_topic}")
    print(f"• Complexity Level:  {escalation.complexity_level}")

    print("\n" + "-" * 80)
    print(" [HINT 1: CONCEPTUAL NUDGE] (Socratic Guidance & Governing Laws)")
    print("-" * 80)
    print(escalation.hint_1_concept)

    print("\n" + "-" * 80)
    print(" [HINT 2: STRUCTURAL STRATEGY & EQUATION SETUP] (Roadmap & Traps)")
    print("-" * 80)
    print(escalation.hint_2_structure)

    print("\n" + "-" * 80)
    print(" [HINT 3: DETAILED WALKTHROUGH] (Intermediate Algebraic Evaluation)")
    print("-" * 80)
    print(escalation.hint_3_calculation)

    print("\n" + "=" * 80)
    print(" [MASTER SOLUTION] (INTERNAL MATH PROOF - Model A: Gemini)")
    print(" [Note: Strictly withheld from student responses to maintain pedagogical integrity]")
    print("=" * 80)
    print(escalation.master_solution)
    print("\n" + "=" * 80)
    print(" [STATUS] Consensus orchestration finished successfully.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
