import os
import sys
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import uuid
import asyncio
import logging
import traceback
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status, Response
from pydantic import BaseModel, Field

from app.schemas.session import SubjectEnum
from app.schemas.studio import (
    TopicResource,
    ArtifactItem,
    ArtifactType,
    StudioTopicListResponse,
)
from app.core.config import settings
from app.core.security import verify_optional_api_key
from app.services.multi_llm_consensus import get_qdrant_vectorstore
from app.services.key_manager import key_manager

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/studio", tags=["Companion Studio Resources"])


# ---------------------------------------------------------
# Request / Response Schemas for POST /studio/generate
# ---------------------------------------------------------
class StudioGenerateRequest(BaseModel):
    topic: str = Field(..., description="JEE Syllabus Topic name (e.g., Rotational Dynamics, VSEPR Theory)")
    artifact_type: str = Field("formula_sheet", description="Type of artifact: formula_sheet | cheat_sheet | flashcards")
    proficiency: str = Field("JEE Advanced", description="Target proficiency: Foundational | JEE Main | JEE Advanced")
    subject: Optional[str] = Field(None, description="Optional subject: Physics | Chemistry | Mathematics")


class StudioGenerateResponse(BaseModel):
    status: str = "success"
    topic: str
    artifact_type: str
    proficiency: str
    artifact_markdown: str
    rag_context_used: bool = False
    message: str = "Artifact successfully synthesized"


# ---------------------------------------------------------
# Seed Topics and Resources
# ---------------------------------------------------------
JEE_TOPIC_RESOURCES: List[TopicResource] = [
    TopicResource(
        topic_id="phy-rotational",
        topic_name="Rotational Dynamics & Angular Momentum",
        subject=SubjectEnum.PHYSICS,
        subtopics=[
            "Moment of Inertia & Parallel/Perpendicular Axis Theorems",
            "Torque and Angular Acceleration",
            "Rolling Without Slipping on Inclined Planes",
            "Conservation of Angular Momentum",
            "Toppling vs Sliding",
        ],
        jee_weightage="High",
        recommended_pyqs_count=42,
        available_artifacts=[
            ArtifactItem(
                artifact_id="art-phy-rot-01",
                title="Rotational Dynamics Master Formula Sheet",
                subject=SubjectEnum.PHYSICS,
                topic="Rotational Dynamics",
                artifact_type=ArtifactType.FORMULA_SHEET,
                format="markdown",
                description="Consolidated formulas, standard moments of inertia, and rolling kinematics for JEE Advanced.",
                content="""# Rotational Dynamics - JEE Master Formula Sheet

## 1. Moment of Inertia ($I$)
- **Ring / Hollow Cylinder (about symmetry axis)**: $$I = MR^2$$
- **Uniform Disc / Solid Cylinder**: $$I = \\frac{1}{2}MR^2$$
- **Solid Sphere**: $$I = \\frac{2}{5}MR^2$$
- **Hollow Thin Spherical Shell**: $$I = \\frac{2}{3}MR^2$$
- **Uniform Thin Rod (about center)**: $$I = \\frac{1}{12}ML^2$$
- **Uniform Thin Rod (about end)**: $$I = \\frac{1}{3}ML^2$$

## 2. Parallel and Perpendicular Axis Theorems
- **Parallel Axis**: $$I = I_{\\text{cm}} + Md^2$$
- **Perpendicular Axis (Planar Laminas only)**: $$I_z = I_x + I_y$$

## 3. Pure Rolling Dynamics on Incline (Angle $\\theta$)
- **Linear Acceleration**:
  $$a = \\frac{g \\sin\\theta}{1 + \\frac{I_{\\text{cm}}}{MR^2}} = \\frac{g \\sin\\theta}{1 + k^2/R^2}$$
- **Friction Force Required**:
  $$f = \\frac{Mg \\sin\\theta}{1 + \\frac{MR^2}{I_{\\text{cm}}}} \\le \\mu_s N$$
""",
                tags=["Physics", "Mechanics", "JEE Advanced"],
                download_filename="Rotational_Dynamics_Formulas.md",
            )
        ],
    ),
    TopicResource(
        topic_id="chem-thermo",
        topic_name="Chemical Thermodynamics & Energetics",
        subject=SubjectEnum.CHEMISTRY,
        subtopics=[
            "First Law, Work in Reversible/Irreversible Processes",
            "Enthalpy and Heat Capacities (Cp, Cv)",
            "Entropy Changes (System, Surroundings, Universe)",
            "Gibbs Free Energy & Spontaneity Criteria",
            "Born-Haber Cycle & Hess's Law",
        ],
        jee_weightage="High",
        recommended_pyqs_count=36,
        available_artifacts=[
            ArtifactItem(
                artifact_id="art-chem-thermo-01",
                title="Chemical Thermodynamics Fast Revision Cheatsheet",
                subject=SubjectEnum.CHEMISTRY,
                topic="Thermodynamics",
                artifact_type=ArtifactType.REVISION_NOTE,
                format="markdown",
                description="Key criteria for spontaneity, reversible vs irreversible work, and entropy formulas.",
                content="""# Chemical Thermodynamics - High-Yield Review

## 1. Reversible Isothermal Work (Ideal Gas)
$$W_{\\text{rev}} = -nRT \\ln\\left(\\frac{V_2}{V_1}\\right) = -2.303 nRT \\log_{10}\\left(\\frac{P_1}{P_2}\\right)$$

## 2. Reversible Adiabatic Relations
$$T V^{\\gamma - 1} = \\text{constant}, \\quad P V^\\gamma = \\text{constant}, \\quad T^\\gamma P^{1-\\gamma} = \\text{constant}$$
$$W_{\\text{adiabatic}} = \\frac{nR(T_2 - T_1)}{\\gamma - 1} = \\frac{P_2V_2 - P_1V_1}{\\gamma - 1}$$

## 3. Gibbs Helmholtz & Spontaneity
$$\\Delta G = \\Delta H - T\\Delta S$$
- $\\Delta G < 0$: Spontaneous process
- $\\Delta G = 0$: Equilibrium state
- $\\Delta G^\\circ = -RT \\ln K_{\\text{eq}}$$
""",
                tags=["Chemistry", "Physical Chemistry", "JEE Main"],
                download_filename="Chemical_Thermodynamics_Summary.md",
            )
        ],
    ),
    TopicResource(
        topic_id="math-calculus",
        topic_name="Definite Integrals & Differential Equations",
        subject=SubjectEnum.MATHEMATICS,
        subtopics=[
            "King's Property & Periodic Functions Integration",
            "Leibniz Integral Rule for Differentiation under Integral Sign",
            "Definite Integral as Limit of a Sum",
            "Linear Differential Equations & Integrating Factors",
            "Homogeneous & Exact Differential Equations",
        ],
        jee_weightage="High",
        recommended_pyqs_count=50,
        available_artifacts=[
            ArtifactItem(
                artifact_id="art-math-calc-01",
                title="Definite Integrals & Leibniz Rule Master Guide",
                subject=SubjectEnum.MATHEMATICS,
                topic="Definite Integrals",
                artifact_type=ArtifactType.MINDMAP,
                format="markdown",
                description="Core symmetry properties, Leibniz differentiation rule, and limit of sums tricks for JEE Advanced.",
                content="""# Definite Integration & Leibniz Rule Guide

## 1. Essential Definite Integral Properties
- **King's Property**:
  $$\\int_a^b f(x) dx = \\int_a^b f(a + b - x) dx$$
- **Splitting Property**:
  $$\\int_0^{2a} f(x) dx = \\int_0^a f(x) dx + \\int_0^a f(2a - x) dx$$
  $$= \\begin{cases} 2\\int_0^a f(x)dx & \\text{if } f(2a-x) = f(x) \\\\ 0 & \\text{if } f(2a-x) = -f(x) \\end{cases}$$

## 2. Leibniz Integral Rule (Differentiation of Integrals)
$$\\frac{d}{dx}\\left[\\int_{u(x)}^{v(x)} f(t, x) dt\\right] = f(v(x), x)\\cdot v'(x) - f(u(x), x)\\cdot u'(x) + \\int_{u(x)}^{v(x)} \\frac{\\partial f}{\\partial x}(t, x) dt$$

## 3. Limit of a Sum Framework
$$\\lim_{n \\to \\infty} \\frac{1}{n} \\sum_{r=1}^{k n} f\\left(\\frac{r}{n}\\right) = \\int_0^k f(x) dx$$
""",
                tags=["Mathematics", "Calculus", "JEE Advanced"],
                download_filename="Definite_Integrals_Guide.md",
            )
        ],
    ),
]


# ---------------------------------------------------------
# Dynamic Artifact Generation Route (POST /studio/generate)
# ---------------------------------------------------------
@router.post("/generate", response_model=StudioGenerateResponse)
async def generate_studio_artifact(request: StudioGenerateRequest):
    """
    Synthesizes custom JEE study artifacts (formula_sheet, cheat_sheet, flashcards)
    grounded in Qdrant syllabus vector retrieval and generated with gemini-1.5-flash
    using key pool rotation and 429 auto-failover.
    """
    print(f"\n[STUDIO-GENERATE] Ingesting request for topic '{request.topic}' (Type: {request.artifact_type}, Level: {request.proficiency})...")

    # 1. Retrieve RAG context from local Qdrant collection
    rag_context = ""
    try:
        vectorstore = get_qdrant_vectorstore()
        if vectorstore:
            docs = vectorstore.similarity_search(request.topic, k=3)
            if docs:
                rag_context = "\n\n".join([d.page_content for d in docs])
                print(f"[STUDIO-RAG] Retrieved {len(docs)} syllabus chunks from Qdrant.")
    except Exception as rag_err:
        print(f"[STUDIO-RAG] Notice: Qdrant retrieval skipped: {rag_err}")

    # 2. Build tailored artifact instructions
    type_instructions = ""
    clean_type = request.artifact_type.lower().replace(" ", "_")

    if "flashcard" in clean_type:
        type_instructions = (
            "Format the document as an intensive set of 6-8 High-Yield JEE Flashcards in Markdown.\n"
            "For each flashcard, use this structure:\n"
            "### Card [Number]: [Concept Title]\n"
            "- **Front (Core Question / Challenge)**: Concise prompt or tricky conceptual question.\n"
            "- **Back (Formula & Key Insight)**: Exact LaTeX formula ($...$, $$...$$), limiting cases, and the underlying JEE trap.\n"
        )
    elif "cheat" in clean_type:
        type_instructions = (
            "Format the document as an ultra-compact, high-yield JEE Exam Cheatsheet in Markdown.\n"
            "Structure into sections:\n"
            "1. **Core Governing Laws & Master Relations** (with boxed LaTeX equations $$...$$).\n"
            "2. **Critical Problem Roadmaps & Standard Coordinates**.\n"
            "3. **JEE Traps, Common Pitfalls & Sign Conventions**.\n"
            "4. **Quick Shortcut Formulas & Limiting Dimension Checks**.\n"
        )
    else:  # formula_sheet
        type_instructions = (
            "Format the document as a comprehensive, master JEE Formula Sheet in Markdown.\n"
            "Structure into clean sections with tables and display math blocks:\n"
            "1. **Primary Formulas & Definitions** (heavy LaTeX $$...$$ equations with variable explanations).\n"
            "2. **Standard Values, Constants & Geometric Geometries**.\n"
            "3. **Key Boundary Conditions & Derivation Milestones**.\n"
            "4. **Related JEE Advanced Variants & Corner Cases**.\n"
        )

    # 3. Invoke Gemini with Key Pool Rotation & Auto-Failover
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an elite JEE Main & Advanced Master Academician and Pedagogical Author. "
            "Your task is to synthesize an authoritative, structured, and beautiful Markdown study artifact. "
            "Rules:\n"
            "- Adhere strictly to the official JEE syllabus scope.\n"
            "- Utilize heavy, flawless LaTeX notation ($...$ for inline, $$...$$ for display equations).\n"
            "- Tailor mathematical depth specifically to the requested proficiency level ({proficiency}).\n"
            "- Ground your formulas and rules in the provided syllabus context when available.\n\n"
            "{type_instructions}"
        ),
        (
            "human",
            "Topic: {topic}\n"
            "Artifact Type: {artifact_type}\n"
            "Target Proficiency: {proficiency}\n\n"
            "<JEE_SYLLABUS_CONTEXT>\n{rag_context}\n</JEE_SYLLABUS_CONTEXT>\n\n"
            "Please generate the complete, pristine Markdown study artifact now."
        )
    ])

    # 1. Resolve Gemini model name and verify API key availability
    gemini_model = getattr(settings, "GEMINI_MODEL", os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
    active_key = (
        key_manager.get_active_key()
        or getattr(settings, "GEMINI_API_KEY", None)
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )
    if not active_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gemini API Key is not configured. Please set GEMINI_API_KEY or GOOGLE_API_KEY in your environment.",
        )

    async def _invoke(llm: ChatGoogleGenerativeAI) -> str:
        chain = prompt | llm | StrOutputParser()
        return await chain.ainvoke({
            "topic": request.topic,
            "artifact_type": request.artifact_type,
            "proficiency": request.proficiency,
            "rag_context": rag_context or "Standard JEE Curriculum Domain",
            "type_instructions": type_instructions,
        })

    try:
        artifact_md = await key_manager.execute_with_failover(
            _invoke,
            model=gemini_model,
            temperature=0.2
        )

        print(f"[STUDIO-GENERATE] Successfully synthesized {len(artifact_md)} characters of Markdown artifact for '{request.topic}'.")

        return StudioGenerateResponse(
            status="success",
            topic=request.topic,
            artifact_type=request.artifact_type,
            proficiency=request.proficiency,
            artifact_markdown=artifact_md,
            rag_context_used=bool(rag_context),
            message=f"Successfully generated {request.proficiency} {request.artifact_type} for {request.topic}."
        )

    except Exception as exc:
        print(f"[STUDIO-GENERATE] Generation failed: {exc.__class__.__name__}: {str(exc)}")
        print(traceback.format_exc())
        error_msg = str(exc)
        if "API_KEY_INVALID" in error_msg or "PERMISSION_DENIED" in error_msg or "UNAUTHENTICATED" in error_msg:
            error_msg = "Gemini API key is invalid or unauthorized. Please verify your GEMINI_API_KEY configuration."
        elif "ResourceExhausted" in error_msg or "429" in error_msg:
            error_msg = "Gemini API rate limit reached across all keys in pool. Please wait 30 seconds and retry."
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Studio artifact generation failed: {error_msg}"
        )


# ---------------------------------------------------------
# Static Topic & Artifact Endpoints
# ---------------------------------------------------------
@router.get("/topics", response_model=StudioTopicListResponse)
async def list_studio_topics(
    subject: Optional[SubjectEnum] = None,
    user: str = Depends(verify_optional_api_key),
):
    """Lists JEE syllabus topics and study resources."""
    if subject:
        filtered = [t for t in JEE_TOPIC_RESOURCES if t.subject == subject]
        return StudioTopicListResponse(subject=subject, topics=filtered)
    return StudioTopicListResponse(subject=None, topics=JEE_TOPIC_RESOURCES)


@router.get("/artifacts", response_model=List[ArtifactItem])
async def list_all_artifacts(
    subject: Optional[SubjectEnum] = None,
    user: str = Depends(verify_optional_api_key),
):
    """Retrieves all pre-built and companion study artifacts."""
    all_artifacts = []
    for topic in JEE_TOPIC_RESOURCES:
        if subject is None or topic.subject == subject:
            all_artifacts.extend(topic.available_artifacts)
    return all_artifacts


@router.get("/download/{artifact_id}")
async def download_artifact(
    artifact_id: str,
    user: str = Depends(verify_optional_api_key),
):
    """Downloads artifact as markdown/LaTeX document."""
    for topic in JEE_TOPIC_RESOURCES:
        for art in topic.available_artifacts:
            if art.artifact_id == artifact_id:
                return Response(
                    content=art.content,
                    media_type="text/markdown",
                    headers={
                        "Content-Disposition": f"attachment; filename={art.download_filename}"
                    },
                )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Artifact {artifact_id} not found.",
    )
