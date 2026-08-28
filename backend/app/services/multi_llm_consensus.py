import os
import sys
from dotenv import load_dotenv, find_dotenv

# 1. Load environment variables at the very top
load_dotenv(find_dotenv())

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import asyncio
import logging
import re
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field

from qdrant_client import QdrantClient
try:
    from langchain_qdrant import QdrantVectorStore
except ImportError:
    from langchain_community.vectorstores import Qdrant as QdrantVectorStore

from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings
from app.schemas.hints import HintEscalation, HintContent
from app.schemas.session import SubjectEnum
from app.services.key_manager import key_manager, KeyManager

logger = logging.getLogger(__name__)

# Path to persistent local Qdrant database
QDRANT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "qdrant_db"


def build_human_message(text_prompt: str, image: Optional[str] = None) -> HumanMessage:
    """
    Constructs a LangChain HumanMessage. If a base64 image is provided,
    formats as a multimodal list of content blocks; otherwise returns text-only content.
    """
    if image and isinstance(image, str) and image.strip():
        return HumanMessage(
            content=[
                {"type": "text", "text": text_prompt},
                {"type": "image_url", "image_url": {"url": image.strip()}},
            ]
        )
    return HumanMessage(content=text_prompt)


# ---------------------------------------------------------
# Strict Pydantic Model for Pedagogical Critic Structured Output
# ---------------------------------------------------------
class PedagogicalCriticOutput(BaseModel):
    """Structured 3-tier progressive hint schema enforced via with_structured_output."""
    hint_1_concept: str = Field(
        ...,
        description="Tier 1 Conceptual Nudge: Identifies core physical/mathematical laws, fundamental definitions, governing equations in LaTeX ($...$, $$...$$), and asks a reflective leading question. Absolutely NO numerical calculations or problem-specific answers."
    )
    hint_2_structure: str = Field(
        ...,
        description="Tier 2 Structural Strategy & Roadmap: Detailed equation setup, coordinate axes / Free Body Diagram guidance, step-by-step roadmap, and common JEE traps/sign mistakes. NO final arithmetic or algebraic solution."
    )
    hint_3_calculation: str = Field(
        ...,
        description="Tier 3 Detailed Walkthrough: 80-90% of the intermediate algebraic manipulation and mathematical substitutions, leaving only the final concluding computation for the student to solve."
    )


class StudentAttemptEvaluation(BaseModel):
    """Structured schema for active Socratic student step evaluation."""
    is_correct: bool = Field(
        ...,
        description="Whether the student's mathematical step, formula setup, or reasoning is correct according to the master derivation."
    )
    feedback: str = Field(
        ...,
        description="Concise Socratic feedback pointing out specific misconceptions or algebraic errors without revealing the complete solution or final answer."
    )


# ---------------------------------------------------------
# Global Singleton Qdrant & Embeddings Cache
# ---------------------------------------------------------
_qdrant_client_instance: Optional[QdrantClient] = None
_embeddings_instance: Optional[FastEmbedEmbeddings] = None
_vectorstore_instance: Optional[Any] = None


def get_qdrant_vectorstore() -> Optional[Any]:
    """
    Returns a cached singleton QdrantVectorStore instance with FastEmbedEmbeddings
    to prevent repeated file locking on the local directory during concurrent requests.
    """
    global _qdrant_client_instance, _embeddings_instance, _vectorstore_instance

    if _vectorstore_instance is not None:
        return _vectorstore_instance

    try:
        if _embeddings_instance is None:
            _embeddings_instance = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

        if _qdrant_client_instance is None:
            if settings.QDRANT_URL:
                _qdrant_client_instance = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY,
                )
            else:
                try:
                    _qdrant_client_instance = QdrantClient(
                        host=settings.QDRANT_HOST,
                        port=settings.QDRANT_PORT,
                        api_key=settings.QDRANT_API_KEY,
                        timeout=10.0,
                    )
                except Exception:
                    if QDRANT_DB_PATH.exists():
                        _qdrant_client_instance = QdrantClient(path=str(QDRANT_DB_PATH))
                    else:
                        return None

        try:
            _vectorstore_instance = QdrantVectorStore(
                client=_qdrant_client_instance,
                collection_name="jee_syllabus",
                embedding=_embeddings_instance,
            )
        except TypeError:
            _vectorstore_instance = QdrantVectorStore(
                client=_qdrant_client_instance,
                collection_name="jee_syllabus",
                embeddings=_embeddings_instance,
            )

        return _vectorstore_instance
    except Exception as e:
        print(f"[QDRANT-SINGLETON] Notice: Qdrant vectorstore initialization skipped: {e}")
        return None


class MultiLLMConsensusService:
    """
    Coordinates JEE doubt resolution, RAG vector retrieval from Qdrant,
    and Multi-LLM Consensus with Multimodal Image Support.
    - Router: Strictly text prompt to Groq (openai/gpt-oss-120b).
    - Model A (Math Proof): Gemini (gemini-2.5-flash / KeyManager) with full multimodal visual OCR & proof derivation.
    - Model B (Pedagogical Critic): Strictly text prompt to Groq (openai/gpt-oss-120b) with math proof and json_mode structured output.
    - Synthesizer: Synthesizes live outputs into a Pydantic HintEscalation schema.
    """

    def __init__(self):
        self.groq_router_model = os.getenv("GROQ_ROUTER_MODEL", "openai/gpt-oss-120b")
        self.groq_critic_model = os.getenv("GROQ_CRITIC_MODEL", "openai/gpt-oss-120b")
        self.math_model_name = os.getenv("GEMINI_MATH_MODEL") or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # ---------------------------------------------------------
    # 0. Qdrant RAG Context Retrieval (Singleton & Resilient)
    # ---------------------------------------------------------
    def _retrieve_rag_context(self, query: str, k: int = 2) -> str:
        """Retrieves top-k syllabus knowledge chunks using singleton Qdrant client."""
        try:
            vectorstore = get_qdrant_vectorstore()
            if vectorstore is None:
                return ""

            docs = vectorstore.similarity_search(query, k=k)
            if docs:
                retrieved_texts = [d.page_content for d in docs]
                return "\n\n".join(retrieved_texts)
            return ""
        except Exception as rag_err:
            print(f"[RAG-RETRIEVAL] Notice: Qdrant retrieval skipped: {rag_err}")
            return ""

    # ---------------------------------------------------------
    # 1. Tier-1 Intent Router (_execute_intent_router) - Strictly Text
    # ---------------------------------------------------------
    async def _execute_intent_router(
        self, user_query: str, subject: SubjectEnum, rag_context: str = ""
    ) -> Dict[str, str]:
        """
        Classifies doubt complexity and extracts core JEE topic using Groq (openai/gpt-oss-120b).
        STRICTLY TEXT ONLY: Does NOT pass multimodal image blocks to Groq.
        """
        print(f"\n[AI-ROUTER] Calling Groq ({self.groq_router_model}) intent router for subject {subject.value} (Strict Text)...")
        system_prompt = (
            "You are an expert JEE Main & Advanced curriculum analyzer.\n"
            "Analyze the user's doubt statement and output EXACTLY two lines in this format:\n"
            "TOPIC: <Specific JEE Topic/Law Name>\n"
            "COMPLEXITY: <Foundational | JEE Main | JEE Advanced | Multi-Concept>"
        )
        human_text = (
            f"Subject: {subject.value}\n"
            f"<JEE_SYLLABUS_CONTEXT>\n{rag_context or 'Standard JEE Curriculum Specifications'}\n</JEE_SYLLABUS_CONTEXT>\n\n"
            f"Doubt Statement: {user_query or 'Analyze the physics/chemistry/math doubt'}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_text),  # Strict text-only HumanMessage
        ]

        groq_api_key = os.getenv("GROQ_API_KEY")
        if groq_api_key:
            for model_name in [self.groq_router_model, "openai/gpt-oss-120b", "openai/gpt-oss-20b"]:
                try:
                    groq_llm = ChatGroq(
                        model=model_name,
                        api_key=groq_api_key,
                        temperature=0.1,
                    )
                    chain = groq_llm | StrOutputParser()
                    response = await chain.ainvoke(messages)

                    topic = f"{subject.value} Concept"
                    complexity = "JEE Main"
                    for line in response.strip().split("\n"):
                        clean = line.strip()
                        if clean.upper().startswith("TOPIC:"):
                            topic = clean.split(":", 1)[1].strip()
                        elif clean.upper().startswith("COMPLEXITY:"):
                            complexity = clean.split(":", 1)[1].strip()

                    print(f"[AI-ROUTER] Groq Intent Router Classified -> Topic: '{topic}', Complexity: '{complexity}'")
                    return {"core_topic": topic, "complexity_level": complexity}
                except Exception as groq_err:
                    print(f"[AI-ROUTER] Groq Router model '{model_name}' failed ({groq_err}). Trying fallback...")
                    continue

        return {"core_topic": f"{subject.value} Problem", "complexity_level": "JEE Main"}

    # Alias for backward compatibility
    route_intent = _execute_intent_router

    # ---------------------------------------------------------
    # 2. Model A: Math Proof & Visual OCR (_execute_math_proof) - Multimodal
    # ---------------------------------------------------------
    async def _execute_math_proof(
        self, user_query: str, subject: SubjectEnum, rag_context: str, image: Optional[str] = None
    ) -> str:
        """
        Model A (Math Proof): Uses Gemini (gemini-2.5-flash) with KeyManager rotation
        and multimodal image diagram OCR for rigorous mathematical proof and complete derivation.
        """
        print(f"\n[AI-MATH] Calling Gemini ({self.math_model_name}) for mathematical proof (Multimodal Image: {bool(image)})...")
        system_prompt = (
            "You are an elite JEE Advanced Master Physicist/Chemist/Mathematician.\n"
            "Provide an exact, rigorous step-by-step mathematical proof and complete derivation for the problem.\n"
            "If an image/diagram is attached, inspect all geometry, vectors, free-body forces, and labeled values carefully.\n"
            "Format all formulas using standard LaTeX ($...$ inline, $$...$$ block).\n"
            "Identify all equations, vector definitions, boundary conditions, and the final numerical/algebraic result.\n"
            "You must ground your pedagogical hints and mathematical derivation strictly in the provided syllabus context. Do not use concepts outside of this scope."
        )
        human_text = (
            f"Subject: {subject.value}\n\n"
            f"<JEE_SYLLABUS_CONTEXT>\n{rag_context or 'Standard JEE Syllabus Formulation'}\n</JEE_SYLLABUS_CONTEXT>\n\n"
            f"Problem to solve completely:\n{user_query or 'Analyze attached diagram and problem'}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            build_human_message(human_text, image),
        ]

        # 1. Attempt Gemini invocation with KeyManager rotation
        last_gemini_exc = None
        max_retries = max(key_manager.get_keys_count() * 2, 4)

        for attempt in range(max_retries):
            try:
                current_key = key_manager.get_next_key()
                gemini_model_name = os.getenv("GEMINI_MATH_MODEL", "gemini-3.6-flash")
                if "2.5" in gemini_model_name:
                    gemini_model_name = "gemini-3.6-flash"
                llm = ChatGoogleGenerativeAI(
                    model=gemini_model_name,
                    google_api_key=current_key,
                    temperature=0.1,
                    max_retries=1,
                )
                chain = llm | StrOutputParser()
                result = await chain.ainvoke(messages)
                print(f"[AI-MATH] Gemini ({gemini_model_name}) Proof Generated successfully ({len(result)} characters).")
                return result

            except Exception as exc:
                last_gemini_exc = exc
                err_str = str(exc).lower()
                is_429 = "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str or "rate limit" in err_str
                if is_429:
                    try:
                        masked = f"{current_key[:6]}...{current_key[-4:]}" if len(current_key) > 10 else "***"
                        print(f"[AI-MATH] Key {masked} hit 429 rate limit. Blacklisting for 60s and retrying...")
                        key_manager.blacklist_key(current_key)
                    except Exception:
                        pass
                    await asyncio.sleep(0.2)
                    continue
                else:
                    print(f"[AI-MATH] Gemini Math Proof attempt failed: {exc.__class__.__name__}: {str(exc)}")
                    break

        # 2. Automatic Groq Fallover on Gemini Key Exhaustion
        print("\n[MATH-SOLVER] All Gemini keys exhausted. Automatically falling back to Groq...")
        groq_api_key = os.getenv("GROQ_API_KEY")
        if groq_api_key:
            # Strictly text fallback prompt (stripping image payload)
            groq_messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_text),
            ]
            for model_name in ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
                try:
                    groq_llm = ChatGroq(
                        model=model_name,
                        api_key=groq_api_key,
                        temperature=0.1,
                    )
                    chain = groq_llm | StrOutputParser()
                    result = await chain.ainvoke(groq_messages)
                    print(f"[AI-MATH] Groq ({model_name}) Fallback Proof Generated successfully ({len(result)} characters).")
                    return result
                except Exception as groq_err:
                    print(f"[AI-MATH] Groq model '{model_name}' fallback notice: {groq_err}. Trying next...")
                    continue

        raise last_gemini_exc or RuntimeError("All models and keys exhausted during math proof.")

    # ---------------------------------------------------------
    # 3. Model B: Pedagogical Critic (_execute_pedagogical_critic) - Strictly Text
    # ---------------------------------------------------------
    async def _execute_pedagogical_critic(
        self,
        user_query: str,
        subject: SubjectEnum,
        rag_context: str,
        math_proof: str = "",
        student_attempt: Optional[str] = None,
    ) -> PedagogicalCriticOutput:
        """
        Model B (Pedagogical Critic): Crafts 3-tier progressive hints using Groq (openai/gpt-oss-120b).
        STRICTLY TEXT ONLY: Receives user_query, RAG context, and the math_proof derived by Gemini/Model A.
        Enforces schema separation via json_mode without hallucination.
        """
        print(f"\n[AI-CRITIC] Calling Groq ({self.groq_critic_model}) for pedagogical 3-tier hint scaffolding (Strict Text)...")
        attempt_info = f"\nStudent previous attempt: {student_attempt}" if student_attempt else ""
        proof_section = f"\n\n<VERIFIED_MATHEMATICAL_PROOF>\n{math_proof}\n</VERIFIED_MATHEMATICAL_PROOF>" if math_proof else ""

        system_prompt = (
            "You are a strict JEE Pedagogical Coach. Under NO circumstances reveal the final answer number or option.\n"
            "Generate a structured 3-tier scaffolding plan for the student's doubt using the provided syllabus context and verified math proof.\n\n"
            "Tier 1 (Conceptual Nudge):\n"
            "Identify fundamental laws, governing principles, and LaTeX definitions ($...$, $$...$$). Ask a reflective leading question.\n\n"
            "Tier 2 (Structural Strategy & Roadmap):\n"
            "Step-by-step setup equations, coordinate axes or Free Body Diagram descriptions, roadmap, and common JEE traps.\n\n"
            "Tier 3 (Detailed Walkthrough):\n"
            "Provide 80-90% of the intermediate algebraic manipulation, leaving the final computation step for the student to solve.\n\n"
            "CRITICAL: You MUST distribute your response exactly into the JSON keys: hint_1_concept, hint_2_structure, hint_3_calculation. "
            "Do NOT combine the tiers into a single field. The conceptual nudge goes ONLY in hint_1_concept. "
            "The roadmap goes ONLY in hint_2_structure. The calculation steps go ONLY in hint_3_calculation. "
            "Do NOT include labels like \"Tier 1:\" or \"Tier 2:\" inside the text values yourself.\n\n"
            "You must ground your pedagogical hints strictly in the provided syllabus context. Do not use concepts outside of this scope."
        )
        human_text = (
            f"Subject: {subject.value}\n"
            f"<JEE_SYLLABUS_CONTEXT>\n{rag_context or 'Standard JEE Syllabus Domain'}\n</JEE_SYLLABUS_CONTEXT>"
            f"{proof_section}{attempt_info}\n\n"
            f"Doubt Statement:\n{user_query or 'Analyze the physics/chemistry/math doubt'}\n\n"
            "Please return valid JSON with keys: hint_1_concept, hint_2_structure, hint_3_calculation."
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_text),  # Strict text-only HumanMessage
        ]

        groq_api_key = os.getenv("GROQ_API_KEY")
        if groq_api_key:
            for model_name in [self.groq_critic_model, "openai/gpt-oss-120b", "openai/gpt-oss-20b"]:
                try:
                    groq_llm = ChatGroq(
                        model=model_name,
                        api_key=groq_api_key,
                        temperature=0.2,
                    )
                    structured_groq = groq_llm.with_structured_output(
                        PedagogicalCriticOutput, method="json_mode"
                    )
                    result: PedagogicalCriticOutput = await structured_groq.ainvoke(messages)

                    print(
                        f"[AI-CRITIC] Groq ({model_name}) Pedagogical Hints Generated via Structured Output "
                        f"(Tier 1: {len(result.hint_1_concept)} chars, Tier 2: {len(result.hint_2_structure)} chars, Tier 3: {len(result.hint_3_calculation)} chars)."
                    )
                    return result
                except Exception as groq_err:
                    print(f"[AI-CRITIC] Groq model '{model_name}' json_mode failed ({groq_err}). Trying fallback...")
                    continue

        raise RuntimeError("Groq Pedagogical Critic was unable to generate hints. Check GROQ_API_KEY.")

    # ---------------------------------------------------------
    # 4. The Synthesizer & Pydantic HintEscalation Chain
    # ---------------------------------------------------------
    async def generate_hint_escalation(
        self,
        query: str,
        subject: SubjectEnum,
        context_chunks: Optional[List[Dict[str, Any]]] = None,
        student_previous_attempt: Optional[str] = None,
        image: Optional[str] = None,
    ) -> HintEscalation:
        """
        Retrieves syllabus context from cached Qdrant Vector Database, runs Intent Router (Groq text)
        and Math Proof (Gemini multimodal), feeds proof to Pedagogical Critic (Groq text),
        and synthesizes live outputs into HintEscalation.
        """
        clean_query = query.strip() if query else ""
        print("\n" + "=" * 75)
        print(f"[AI-ENGINE] Ingesting Dynamic Doubt for Subject: {subject.value} (Multimodal Image: {bool(image)})")
        print(f"[USER QUESTION]: '{clean_query}'")
        print("=" * 75)

        # 1. Resilient RAG Vector Retrieval from Qdrant
        rag_context = self._retrieve_rag_context(clean_query or subject.value, k=2)
        if not rag_context and context_chunks:
            rag_context = "\n".join([str(c) for c in context_chunks])

        # Terminal logging for live database lookup monitoring
        print(f"\n--- RAG RETRIEVED CONTEXT ---\n{rag_context}\n---------------------------")

        print(f"[AI-ENGINE] Executing Intent Router (Groq text) and Math Proof (Gemini multimodal)...")
        intent_task = self._execute_intent_router(clean_query, subject, rag_context)
        proof_task = self._execute_math_proof(clean_query, subject, rag_context, image=image)

        try:
            intent_res, math_proof = await asyncio.gather(intent_task, proof_task)
        except Exception as exc:
            print(f"[AI-ENGINE] Intent/Proof pipeline halted: {exc.__class__.__name__}: {str(exc)}")
            raise exc

        core_topic = intent_res.get("core_topic", f"{subject.value} Problem Solving")
        complexity = intent_res.get("complexity_level", "JEE Main & Advanced")

        print(f"[AI-ENGINE] Executing Pedagogical Critic (Groq text) with verified Math Proof...")
        critic_output = await self._execute_pedagogical_critic(
            user_query=clean_query,
            subject=subject,
            rag_context=rag_context,
            math_proof=math_proof,
            student_attempt=student_previous_attempt,
        )

        print(f"\n[AI-ENGINE] Synthesizing consensus outputs into HintEscalation schema for '{core_topic}'...")

        escalation = self._synthesize_to_schema(
            core_topic=core_topic,
            complexity_level=complexity,
            math_proof=math_proof,
            critic_output=critic_output,
            user_query=clean_query,
            subject=subject,
        )

        print(f"[AI-ENGINE] Successfully synthesized HintEscalation (Tier 1, Tier 2, Tier 3, Master Proof)")
        print("=" * 75 + "\n")
        return escalation

    def _synthesize_to_schema(
        self,
        core_topic: str,
        complexity_level: str,
        math_proof: str,
        critic_output: Union[PedagogicalCriticOutput, str],
        user_query: str,
        subject: SubjectEnum,
    ) -> HintEscalation:
        """Extracts and formats the 3 tiers and proof dynamically into HintEscalation."""
        # 1. Direct assignment from structured Pydantic object
        if isinstance(critic_output, PedagogicalCriticOutput):
            return HintEscalation(
                core_topic=core_topic,
                complexity_level=complexity_level,
                hint_1_concept=critic_output.hint_1_concept.strip(),
                hint_2_structure=critic_output.hint_2_structure.strip(),
                hint_3_calculation=critic_output.hint_3_calculation.strip(),
                master_solution=math_proof,
            )

        # 2. Fallback parsing for raw strings
        tier1 = ""
        tier2 = ""
        tier3 = ""

        tier_pattern = r"(?im)^\s*(?:#+\s*)?Tier\s*([123])\s*[\:\-\–\—\.]*.*$"
        tier_splits = re.split(tier_pattern, str(critic_output))
        if len(tier_splits) >= 7:
            for i in range(1, len(tier_splits), 2):
                num = tier_splits[i].strip()
                content = tier_splits[i + 1].strip()
                if num == "1":
                    tier1 = content
                elif num == "2":
                    tier2 = content
                elif num == "3":
                    tier3 = content

        if not tier1 or not tier2:
            paragraphs = [p.strip() for p in str(critic_output).split("\n\n") if p.strip()]
            if len(paragraphs) >= 3:
                tier1 = paragraphs[0]
                tier2 = paragraphs[1]
                tier3 = "\n\n".join(paragraphs[2:])
            elif len(paragraphs) == 2:
                tier1 = paragraphs[0]
                tier2 = paragraphs[1]
                tier3 = "Work through the algebraic substitutions using the Tier 2 equations."
            else:
                tier1 = str(critic_output)
                tier2 = "Set up the primary algebraic relations and solve for the unknown."
                tier3 = "Carry out the final numerical/algebraic evaluation."

        return HintEscalation(
            core_topic=core_topic,
            complexity_level=complexity_level,
            hint_1_concept=tier1,
            hint_2_structure=tier2,
            hint_3_calculation=tier3,
            master_solution=math_proof,
        )

    # ---------------------------------------------------------
    # 5. Public Progressive Hint Endpoint Adapter
    # ---------------------------------------------------------
    async def generate_progressive_hint(
        self,
        query: str,
        subject: SubjectEnum,
        target_tier: int,
        context_chunks: Optional[List[Dict[str, Any]]] = None,
        student_previous_attempt: Optional[str] = None,
        image: Optional[str] = None,
    ) -> HintContent:
        """Adapts synthesized HintEscalation into structured HintContent for the active tier."""
        escalation = await self.generate_hint_escalation(
            query=query,
            subject=subject,
            context_chunks=context_chunks,
            student_previous_attempt=student_previous_attempt,
            image=image,
        )

        if target_tier == 1:
            return HintContent(
                tier=1,
                tier_name="Tier 1: Conceptual Nudge",
                concept_summary=f"Topic: {escalation.core_topic} ({escalation.complexity_level})",
                governing_formulas=[],
                hint_content=escalation.hint_1_concept,
                probing_question="What are the governing principles and coordinate conventions for this setup?",
                latex_math_blocks=[],
                pitfall_warning=f"Ensure you identify the core physics/chemistry laws of {escalation.core_topic} before jumping to calculations.",
                next_tier_available=True,
            )
        elif target_tier == 2:
            return HintContent(
                tier=2,
                tier_name="Tier 2: Structural Strategy & Roadmap",
                concept_summary=f"Equation Setup for {escalation.core_topic}",
                governing_formulas=[],
                hint_content=escalation.hint_2_structure,
                probing_question="Can you set up the governing equations without plugging in final numerical answers?",
                latex_math_blocks=[],
                pitfall_warning="Double check algebraic signs and boundary conditions.",
                next_tier_available=True,
            )
        else:
            return HintContent(
                tier=3,
                tier_name="Tier 3: Detailed Walkthrough",
                concept_summary=f"Intermediate Evaluation for {escalation.core_topic}",
                governing_formulas=[],
                hint_content=escalation.hint_3_calculation,
                probing_question="Verify dimensions and sanity-check the limiting cases.",
                latex_math_blocks=[],
                pitfall_warning="Ensure correct units and final algebraic reduction.",
                next_tier_available=False,
            )

    async def evaluate_student_attempt(
        self,
        attempt: str,
        current_tier: int,
        master_proof: str,
        rag_context: str = "",
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates a student's intermediate mathematical step against the master proof using ChatGroq.
        Outputs JSON with strictly two keys: is_correct (boolean) and feedback (string).
        If incorrect, points out the error without revealing the full solution.
        """
        try:
            clean_attempt = (attempt or "").strip()
            print(f"\n[AI-EVALUATOR] Evaluating Student Attempt at Tier {current_tier}: '{clean_attempt[:80]}...'")

            if not clean_attempt or any(k in clean_attempt.lower() for k in ["stuck", "i am stuck", "help", "need hint", "next"]):
                return {
                    "is_correct": True,
                    "feedback": "Step acknowledged. Escalating to the next progressive hint tier.",
                }

            system_prompt = (
                "You are an expert Socratic JEE physics, chemistry, and mathematics tutor.\n"
                "Evaluate the student's mathematical step or conceptual setup against the master derivation.\n"
                "Output JSON with strictly two keys:\n"
                "{\n"
                '  "is_correct": boolean,\n'
                '  "feedback": string\n'
                "}\n"
                "Rules:\n"
                "1. is_correct must be true if the student's formula setup, vector relation, or algebraic step is mathematically sound; false if there is an error, wrong sign, incorrect formula, or misconception.\n"
                "2. If incorrect, feedback must point out the specific error without revealing the full solution or final answer.\n"
                "3. Format formulas in standard LaTeX ($...$ inline, $$...$$ block)."
            )

            human_text = (
                f"<MASTER_PROOF_REFERENCE>\n{master_proof or 'Standard JEE Derivation'}\n</MASTER_PROOF_REFERENCE>\n\n"
                f"<JEE_SYLLABUS_CONTEXT>\n{rag_context or 'Standard JEE Scope'}\n</JEE_SYLLABUS_CONTEXT>\n\n"
                f"Current Progress Tier: Tier {current_tier}\n"
                f"Student Attempt:\n{clean_attempt}"
            )

            groq_api_key = os.getenv("GROQ_API_KEY")
            groq_llm = ChatGroq(
                model=os.getenv("GROQ_CRITIC_MODEL", "openai/gpt-oss-120b"),
                api_key=groq_api_key,
                temperature=0.1,
            )

            structured_llm = groq_llm.with_structured_output(StudentAttemptEvaluation, method="json_mode")
            eval_res: StudentAttemptEvaluation = await structured_llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_text),
            ])

            print(f"[AI-EVALUATOR] Socratic Evaluation: is_correct={eval_res.is_correct} | feedback='{eval_res.feedback[:100]}...'")
            return {
                "is_correct": eval_res.is_correct,
                "feedback": eval_res.feedback,
            }

        except Exception as e:
            print(f"[AI-EVALUATOR] Socratic evaluation notice: {e}. Using fallback evaluator...")
            try:
                raw_chain = groq_llm | StrOutputParser()
                raw_res = await raw_chain.ainvoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=human_text),
                ])
                json_match = re.search(r"\{[\s\S]*\}", raw_res)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    return {
                        "is_correct": bool(parsed.get("is_correct", True)),
                        "feedback": str(parsed.get("feedback", "Step reviewed.")),
                    }
            except Exception:
                pass

            return {
                "is_correct": True,
                "feedback": "Step reviewed. Escalating to the next hint.",
            }

    # ---------------------------------------------------------
    # 6. Resolve with Mentor Test Handoff Prompt Execution
    # ---------------------------------------------------------
    async def generate_test_handoff_mentor_response(
        self,
        question_text: str,
        student_option: str,
        correct_option: str,
        solution_latex: str,
        subject: Union[SubjectEnum, str],
    ) -> str:
        """
        Executes the custom Active Mentor handoff prompt for a student transitioning
        from the Test Series after missing/reviewing an MCQ.
        Constructs a 2-3 sentence Tier-1 Socratic response without revealing the full solution.
        """
        subject_name = subject.value if isinstance(subject, SubjectEnum) else str(subject)
        mentor_prompt = (
            f"You are the Active Mentor. The student just took a test and selected {student_option} "
            f"instead of the correct answer {correct_option} for the following {subject_name} question: {question_text}. "
            f"The official solution is: {solution_latex}. In 2-3 sentences, greet the student, acknowledge the "
            f"specific question they missed, and ask a Tier-1 Socratic probing question to help them realize why "
            f"their chosen option was mathematically or conceptually incorrect. Do not reveal the full solution yet."
        )

        system_msg = SystemMessage(
            content=(
                "You are an expert Socratic JEE Mentor. "
                "Format all mathematical equations with standard LaTeX ($...$ inline, $$...$$ block). "
                "Guide the student through conceptual probing without revealing the final answer or complete solution."
            )
        )
        human_msg = HumanMessage(content=mentor_prompt)

        print(f"\n[AI-HANDOFF] Generating Active Mentor Test Handoff response for {subject_name}...")

        # 1. Attempt Gemini with KeyManager rotation
        max_retries = max(key_manager.get_keys_count() * 2, 4)
        for attempt in range(max_retries):
            try:
                current_key = key_manager.get_next_key()
                gemini_model_name = os.getenv("GEMINI_MATH_MODEL", "gemini-3.6-flash")
                if "2.5" in gemini_model_name:
                    gemini_model_name = "gemini-3.6-flash"
                llm = ChatGoogleGenerativeAI(
                    model=gemini_model_name,
                    google_api_key=current_key,
                    temperature=0.3,
                    max_retries=1,
                )
                chain = llm | StrOutputParser()
                result = await chain.ainvoke([system_msg, human_msg])
                if result and result.strip():
                    print(f"[AI-HANDOFF] Gemini generated handoff mentor response ({len(result)} chars).")
                    return result.strip()
            except Exception as exc:
                err_str = str(exc).lower()
                if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str or "rate limit" in err_str:
                    try:
                        key_manager.blacklist_key(current_key)
                    except Exception:
                        pass
                    await asyncio.sleep(0.2)
                    continue
                else:
                    break

        # 2. Automatic Groq Fallback
        groq_api_key = os.getenv("GROQ_API_KEY")
        if groq_api_key:
            for model_name in [self.groq_critic_model, "openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
                try:
                    groq_llm = ChatGroq(
                        model=model_name,
                        api_key=groq_api_key,
                        temperature=0.3,
                    )
                    chain = groq_llm | StrOutputParser()
                    result = await chain.ainvoke([system_msg, human_msg])
                    if result and result.strip():
                        print(f"[AI-HANDOFF] Groq ({model_name}) generated handoff mentor response ({len(result)} chars).")
                        return result.strip()
                except Exception as groq_err:
                    print(f"[AI-HANDOFF] Groq fallback notice: {groq_err}. Trying next...")
                    continue

        # 3. Rule-based graceful fallback
        return (
            f"Hello! I see you selected option ({student_option}) on this {subject_name} question. "
            f"Let's look at the underlying physical or mathematical principles: what core formula connects the given parameters, "
            f"and what condition might you have overlooked when calculating or comparing with ({correct_option})?"
        )


multi_llm_consensus_service = MultiLLMConsensusService()
