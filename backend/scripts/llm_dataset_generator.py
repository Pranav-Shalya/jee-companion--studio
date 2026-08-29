import os
import sys
import csv
import json
import time
import random
import asyncio
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Reconfigure stdout for Windows console UTF-8 support
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 1. Setup & Environment
load_dotenv(find_dotenv())

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# File paths and Constants
KB_FILE = "data/generated_jee_knowledge_base.csv"
TEST_FILE = "data/generated_jee_test_series.csv"

KB_HEADERS = [
    "subject",
    "chapter",
    "topic",
    "difficulty_level",
    "content_type",
    "text",
    "formulas_json",
    "prerequisites_json",
    "common_pitfalls_json",
]

TEST_HEADERS = [
    "subject",
    "chapter",
    "topic",
    "difficulty_level",
    "content_type",
    "question_text",
    "options_json",
    "correct_option",
    "solution_latex",
]


# 2. Key Rotator Class
class GeminiRotator:
    """
    Loads GEMINI_API_KEYS from the environment, splits by commas,
    and provides a get_next_key() method that cycles through them
    to prevent rate limits.
    """

    def __init__(self):
        self._keys = []
        self._index = 0
        self.reload_keys()

    def reload_keys(self):
        raw_keys = (
            os.getenv("GEMINI_API_KEYS")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or ""
        )
        extracted = []
        for part in raw_keys.replace("\n", ",").split(","):
            cleaned = part.strip()
            if cleaned and cleaned not in extracted:
                extracted.append(cleaned)
        self._keys = extracted

        if self._keys:
            masked = [f"{k[:6]}...{k[-4:]}" if len(k) > 10 else "***" for k in self._keys]
            print(f"[KEY-ROTATOR] Initialized with {len(self._keys)} Gemini key(s): {', '.join(masked)}")
        else:
            print("[KEY-ROTATOR] Warning: No Gemini API keys found in environment variables.")

    def get_next_key(self) -> str:
        if not self._keys:
            self.reload_keys()
            if not self._keys:
                raise ValueError("No GEMINI_API_KEYS found in environment variables.")
        key = self._keys[self._index % len(self._keys)]
        self._index += 1
        return key


# Global rotator instance
rotator = GeminiRotator()


# 3. Helper Function to Initialize CSV Files
def init_csv_files():
    """Initializes target CSV files with headers if they do not exist."""
    # Ensure data directory exists
    os.makedirs(os.path.dirname(KB_FILE) or "data", exist_ok=True)
    os.makedirs(os.path.dirname(TEST_FILE) or "data", exist_ok=True)

    if not os.path.exists(KB_FILE):
        print(f"[FILE-INIT] Creating knowledge base CSV with headers: {KB_FILE}")
        with open(KB_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(KB_HEADERS)

    if not os.path.exists(TEST_FILE):
        print(f"[FILE-INIT] Creating test series CSV with headers: {TEST_FILE}")
        with open(TEST_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(TEST_HEADERS)


def clean_json_string(text: str) -> str:
    """Strips markdown code fences and whitespace from LLM output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


# 4. LLM Prompts & Generators
async def generate_theory(subject: str, chapter: str):
    """
    Asks Gemini to act as a JEE expert and output a JSON array of 3 core concepts
    for the chapter (including standard proofs, pitfalls, prerequisites, and LaTeX formulas).
    """
    if genai is None:
        raise ImportError("google.generativeai package is not installed.")

    prompt = (
        f"You are a top-tier JEE Master Faculty for {subject}. "
        f"Generate a strict JSON array of 3 core foundational concepts for the chapter: '{chapter}'. "
        f"Each object in the array MUST contain the following exact keys:\n"
        f"- topic: string (specific concept/sub-topic name)\n"
        f"- difficulty_level: string ('JEE Main' or 'JEE Advanced')\n"
        f"- content_type: string ('theory')\n"
        f"- text: string (detailed pedagogical explanation, step-by-step derivation, and core governing laws with LaTeX $...$ inline and $$...$$ block notation)\n"
        f"- formulas: array of strings (governing LaTeX mathematical formulas)\n"
        f"- prerequisites: array of strings (prior knowledge needed)\n"
        f"- common_pitfalls: array of strings (common misconceptions, sign errors, domain pitfalls)\n\n"
        f"Output ONLY the valid raw JSON array. Do not include markdown code block formatting or backticks."
    )

    api_key = rotator.get_next_key()
    genai.configure(api_key=api_key)

    candidate_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash']
    raw_text = ""

    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = await asyncio.to_thread(model.generate_content, prompt)
            raw_text = response.text if hasattr(response, "text") else ""
            if raw_text and len(raw_text.strip()) > 10:
                break
        except Exception as e:
            print(f"[GEN-THEORY] Model '{model_name}' failed: {e}. Trying next...")

    if not raw_text:
        print(f"[GEN-THEORY] Failed to get response for {subject} - {chapter}")
        return []

    try:
        cleaned = clean_json_string(raw_text)
        data = json.loads(cleaned)
        if isinstance(data, dict) and "concepts" in data:
            data = data["concepts"]
        if not isinstance(data, list):
            data = [data]
        return data
    except Exception as parse_err:
        print(f"[GEN-THEORY] JSON Parse error for {subject} - {chapter}: {parse_err}")
        return []


async def generate_pyqs(subject: str, chapter: str, count: int = 5):
    """
    Asks Gemini to generate a JSON array of count multiple-choice questions for the chapter,
    formatted strictly with question_text, 4 options_json, correct_option (A/B/C/D), and solution_latex.
    """
    if genai is None:
        raise ImportError("google.generativeai package is not installed.")

    prompt = (
        f"You are an elite JEE Advanced question designer for {subject}. "
        f"Generate a strict JSON array of {count} multiple-choice questions (MCQs) for the chapter: '{chapter}'. "
        f"Each object in the array MUST contain the following exact keys:\n"
        f"- topic: string (sub-topic name)\n"
        f"- difficulty_level: string ('JEE Main' or 'JEE Advanced')\n"
        f"- content_type: string ('pyq')\n"
        f"- question_text: string (full problem statement with standard LaTeX math notation)\n"
        f"- options_json: array of 4 strings (options A, B, C, D with LaTeX math)\n"
        f"- correct_option: string ('A', 'B', 'C', or 'D')\n"
        f"- solution_latex: string (step-by-step mathematical proof and complete derivation)\n\n"
        f"Output ONLY the valid raw JSON array. Do not include markdown code block formatting or backticks."
    )

    api_key = rotator.get_next_key()
    genai.configure(api_key=api_key)

    candidate_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash']
    raw_text = ""

    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = await asyncio.to_thread(model.generate_content, prompt)
            raw_text = response.text if hasattr(response, "text") else ""
            if raw_text and len(raw_text.strip()) > 10:
                break
        except Exception as e:
            print(f"[GEN-PYQ] Model '{model_name}' failed: {e}. Trying next...")

    if not raw_text:
        print(f"[GEN-PYQ] Failed to get response for {subject} - {chapter}")
        return []

    try:
        cleaned = clean_json_string(raw_text)
        data = json.loads(cleaned)
        if isinstance(data, dict) and "questions" in data:
            data = data["questions"]
        if not isinstance(data, list):
            data = [data]
        return data
    except Exception as parse_err:
        print(f"[GEN-PYQ] JSON Parse error for {subject} - {chapter}: {parse_err}")
        return []


def append_to_kb_file(subject: str, chapter: str, items: list):
    """Appends theory concepts to KB_FILE."""
    if not items:
        return
    with open(KB_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for item in items:
            writer.writerow([
                subject,
                chapter,
                item.get("topic", chapter),
                item.get("difficulty_level", "JEE Main"),
                item.get("content_type", "theory"),
                item.get("text", ""),
                json.dumps(item.get("formulas", []), ensure_ascii=False),
                json.dumps(item.get("prerequisites", []), ensure_ascii=False),
                json.dumps(item.get("common_pitfalls", []), ensure_ascii=False),
            ])
    print(f"[KB-FILE] Appended {len(items)} concept(s) to {KB_FILE}")


def append_to_test_file(subject: str, chapter: str, items: list):
    """Appends PYQ questions to TEST_FILE."""
    if not items:
        return
    with open(TEST_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for item in items:
            writer.writerow([
                subject,
                chapter,
                item.get("topic", chapter),
                item.get("difficulty_level", "JEE Advanced"),
                item.get("content_type", "pyq"),
                item.get("question_text", ""),
                json.dumps(item.get("options_json", []), ensure_ascii=False),
                item.get("correct_option", "A"),
                item.get("solution_latex", ""),
            ])
    print(f"[TEST-FILE] Appended {len(items)} PYQ(s) to {TEST_FILE}")


# 5. Main Processing Loop
async def main():
    print("=" * 65)
    print("🚀 Initializing Asynchronous AI Batch Generator for JEE Data")
    print("=" * 65)

    # Initialize CSV files
    init_csv_files()

    # Define syllabus targets
    syllabus_targets = [
        {"subject": "Physics", "chapter": "UNIT 2: Kinematics"},
        {"subject": "Mathematics", "chapter": "UNIT 8: INTEGRAL CALCULAS"},
        {"subject": "Chemistry", "chapter": "UNIT 4: CHEMICAL THERMODYNAMICS"},
    ]

    total_theory = 0
    total_pyqs = 0

    for idx, target in enumerate(syllabus_targets, start=1):
        subj = target["subject"]
        chap = target["chapter"]

        print(f"\n--- [{idx}/{len(syllabus_targets)}] Processing: {subj} -> {chap} ---")

        # 1. Generate Theory Concepts
        try:
            print(f"Generating theory concepts for {chap}...")
            theory_items = await generate_theory(subj, chap)
            append_to_kb_file(subj, chap, theory_items)
            total_theory += len(theory_items)
        except Exception as e:
            print(f"[ERROR] Theory generation failed for {chap}: {e}")

        # Sleep to respect rate limits
        print("Sleeping 10s between calls to respect Gemini API limits...")
        time.sleep(10)

        # 2. Generate PYQ Questions
        try:
            print(f"Generating 5 PYQs for {chap}...")
            pyq_items = await generate_pyqs(subj, chap, count=5)
            append_to_test_file(subj, chap, pyq_items)
            total_pyqs += len(pyq_items)
        except Exception as e:
            print(f"[ERROR] PYQ generation failed for {chap}: {e}")

        # Sleep before next chapter
        if idx < len(syllabus_targets):
            print("Sleeping 10s before next syllabus target...")
            time.sleep(10)

    print("\n" + "=" * 65)
    print("✅ AI Batch Generation Complete!")
    print(f"📊 Total Theory Concepts Appended: {total_theory} -> {KB_FILE}")
    print(f"📊 Total PYQ Questions Appended: {total_pyqs} -> {TEST_FILE}")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
