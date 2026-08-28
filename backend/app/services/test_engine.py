import json
import logging
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client import models
from sentence_transformers import SentenceTransformer
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import settings
from app.services.key_manager import key_manager

logger = logging.getLogger(__name__)

# Default path for persistent local Qdrant database
QDRANT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "qdrant_db"

# Lazy-loaded singleton embedding model on CPU
_embedding_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    """
    Initializes and caches SentenceTransformer('all-MiniLM-L6-v2') on local CPU.
    """
    global _embedding_model
    if _embedding_model is None:
        logger.info("Initializing SentenceTransformer('all-MiniLM-L6-v2') on CPU...")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    return _embedding_model


def get_qdrant_client() -> QdrantClient:
    """
    Initializes and returns a QdrantClient connected to Qdrant Cloud or local server/storage.
    """
    if settings.QDRANT_URL:
        return QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
    else:
        try:
            return QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                api_key=settings.QDRANT_API_KEY,
                timeout=10.0,
            )
        except Exception:
            return QdrantClient(path=str(QDRANT_DB_PATH))


async def generate_llm_questions(
    subject: str,
    topic: Optional[str],
    missing_count: int,
    exam_type: str = "JEE Mains",
) -> List[Dict[str, Any]]:
    """
    Dynamically generates multiple-choice JEE questions using LLM (Groq / Gemini)
    with strict JSON array formatting.
    """
    topic_str = topic.strip() if topic and topic.strip() else f"core {subject} curriculum"
    prompt = (
        f"You are a JEE expert. Generate {missing_count} {exam_type} level multiple-choice questions "
        f"for {subject} on {topic_str}. You MUST output ONLY a valid JSON array of objects with the "
        f"exact keys: question_text (string with LaTeX), options_json (array of 4 strings), "
        f"correct_option (string A/B/C/D), and solution_latex (string with step-by-step math). "
        f"Do not include markdown code blocks, just raw JSON."
    )

    logger.info("Generating %d synthetic questions via LLM for topic: %s", missing_count, topic_str)
    raw_response = ""

    # 1. Attempt generation with Groq
    groq_api_key = settings.GROQ_API_KEY
    if groq_api_key:
        groq_candidates = [
            settings.GROQ_MODEL,
            "llama-3.3-70b-versatile",
            "openai/gpt-oss-120b",
            "llama-3.1-8b-instant",
        ]
        for model_name in groq_candidates:
            try:
                llm = ChatGroq(
                    model=model_name,
                    api_key=groq_api_key,
                    temperature=0.3,
                    max_tokens=4096,
                )
                response = await llm.ainvoke([HumanMessage(content=prompt)])
                raw_response = response.content if hasattr(response, "content") else str(response)
                if raw_response and len(raw_response.strip()) > 10:
                    break
            except Exception as e:
                logger.warning("Groq model '%s' failed for test generation: %s", model_name, e)

    # 2. Fallback to Gemini with rotated keys if Groq failed or unconfigured
    if not raw_response:
        gemini_key = key_manager.get_active_key()
        if gemini_key:
            try:
                gemini_llm = ChatGoogleGenerativeAI(
                    model=settings.GEMINI_MODEL,
                    google_api_key=gemini_key,
                    temperature=0.3,
                    max_output_tokens=4096,
                )
                response = await gemini_llm.ainvoke([HumanMessage(content=prompt)])
                raw_response = response.content if hasattr(response, "content") else str(response)
            except Exception as e:
                logger.error("Gemini fallback test generation failed: %s", e)

    if not raw_response:
        logger.warning("All LLMs failed to return response for test generation.")
        return []

    # 3. Parse and sanitize JSON array
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    generated_items = []
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "questions" in data:
            data = data["questions"]
        if isinstance(data, list):
            for item in data:
                doc_id = f"gen-{uuid.uuid4().hex[:8]}"
                q_text = item.get("question_text") or item.get("text") or ""
                options = item.get("options_json") or item.get("options") or []
                solution = item.get("solution_latex") or item.get("solution") or ""
                correct = item.get("correct_option") or "A"

                generated_items.append({
                    "doc_id": doc_id,
                    "subject": subject,
                    "chapter": topic_str,
                    "topic": topic_str,
                    "difficulty_level": exam_type,
                    "content_type": "generated_mcq",
                    "text": q_text,
                    "options_json": options,
                    "correct_option": correct,
                    "solution_latex": solution,
                    "formulas": [],
                    "prerequisites": [],
                    "common_pitfalls": [],
                })
    except Exception as parse_err:
        logger.error("Failed to parse JSON response from LLM: %s. Raw was:\n%s", parse_err, raw_response[:300])

    return generated_items


async def generate_test_paper(
    subject: str,
    topic: Optional[str] = None,
    count: int = 5,
    difficulty: Optional[str] = None,
    exam_type: str = "JEE Mains",
) -> List[Dict[str, Any]]:
    """
    Semantic Vector Search + Hybrid LLM Test Generation:
    1. Encodes search query f"{subject} {topic}" using SentenceTransformer('all-MiniLM-L6-v2').
    2. Builds subject pre-filter and calls client.query_points() / client.search() on 'jee_test_series'.
    3. Normalizes payload questions and checks deficit (count - len(retrieved)).
    4. Dynamically generates missing questions via strict JSON LLM prompting.
    5. Returns merged question set.
    """
    client = get_qdrant_client()
    embedding_model = get_embedding_model()

    # 1. Build search query text and generate dense embedding vector
    query_text = f"{subject} {topic or ''}".strip()
    query_vector = embedding_model.encode(query_text).tolist()

    # 2. Subject Pre-Filter
    subject_clean = subject.strip()
    subject_filter = None
    if subject_clean:
        subject_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="subject",
                    match=models.MatchValue(value=subject_clean.capitalize()),
                )
            ]
        )

    logger.info(
        "Semantic Vector Test Generation -> Query: '%s', Subject: '%s', Count: %d, Exam: '%s'",
        query_text,
        subject_clean,
        count,
        exam_type,
    )

    seen_questions = set()
    retrieved_questions: List[Dict[str, Any]] = []

    # 3. Vector Search on 'jee_test_series' with relevance score threshold
    score_threshold = 0.35
    try:
        search_hits = []
        if hasattr(client, "query_points"):
            res = client.query_points(
                collection_name="jee_test_series",
                query=query_vector,
                query_filter=subject_filter,
                score_threshold=score_threshold,
                limit=count * 2,
                with_payload=True,
                with_vectors=False,
            )
            search_hits = getattr(res, "points", [])
        elif hasattr(client, "search"):
            search_hits = client.search(
                collection_name="jee_test_series",
                query_vector=query_vector,
                query_filter=subject_filter,
                score_threshold=score_threshold,
                limit=count * 2,
                with_payload=True,
                with_vectors=False,
            )

        for hit in search_hits:
            hit_score = getattr(hit, "score", None)
            if hit_score is not None and hit_score < score_threshold:
                logger.debug("Skipping hit below score threshold: score=%.3f < %.2f", hit_score, score_threshold)
                continue

            payload = hit.payload or {}
            q_text = (payload.get("text") or payload.get("question_text") or "").strip()
            if not q_text or q_text in seen_questions:
                continue

            seen_questions.add(q_text)
            retrieved_questions.append({
                "doc_id": payload.get("doc_id") or str(hit.id),
                "subject": payload.get("subject") or subject,
                "chapter": payload.get("chapter"),
                "topic": payload.get("topic") or topic,
                "difficulty_level": payload.get("difficulty_level") or difficulty or exam_type,
                "content_type": payload.get("content_type", "pyq"),
                "text": q_text,
                "options_json": payload.get("options_json", []),
                "correct_option": payload.get("correct_option", "A"),
                "solution_latex": payload.get("solution_latex", ""),
                "formulas": payload.get("formulas", []),
                "prerequisites": payload.get("prerequisites", []),
                "common_pitfalls": payload.get("common_pitfalls", []),
            })
            if len(retrieved_questions) >= count:
                break
    except Exception as search_err:
        logger.warning("Vector search on 'jee_test_series' note: %s", search_err)

    # 4. Fallback Deficit Generation via LLM with Deduplication
    missing_count = count - len(retrieved_questions)
    if missing_count > 0:
        logger.info(
            "Semantic Vector Search retrieved %d/%d questions. Generating deficit of %d questions via LLM...",
            len(retrieved_questions),
            count,
            missing_count,
        )
        llm_questions = await generate_llm_questions(
            subject=subject,
            topic=topic,
            missing_count=missing_count,
            exam_type=difficulty or exam_type,
        )
        for lq in llm_questions:
            lq_text = (lq.get("text") or "").strip()
            if lq_text and lq_text not in seen_questions:
                seen_questions.add(lq_text)
                retrieved_questions.append(lq)

    final_questions = retrieved_questions[:count]
    logger.info("Total test questions compiled: %d", len(final_questions))
    return final_questions
