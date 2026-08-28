from typing import List, Optional
from pydantic import BaseModel, Field


class HintEscalation(BaseModel):
    """Pydantic schema containing multi-tier progressive hints and the internal master proof."""
    core_topic: str = Field(..., description="Extracted core JEE topic/concept name")
    complexity_level: str = Field(..., description="Complexity classification (e.g. Foundational, JEE Main, JEE Advanced)")
    hint_1_concept: str = Field(..., description="Tier 1: Core concept, laws, and governing equations without numerical values")
    hint_2_structure: str = Field(..., description="Tier 2: Structural roadmap, equation setup, and pitfall warnings")
    hint_3_calculation: str = Field(..., description="Tier 3: Detailed walkthrough with intermediate calculations (near-solution)")
    master_solution: str = Field(..., description="Internal mathematical proof and full verification from Model A")


class HintContent(BaseModel):
    tier: int = Field(..., description="Active hint tier: 1 (Conceptual), 2 (Structural), 3 (Walkthrough)")
    tier_name: str = Field(..., description="Display title of the tier")
    concept_summary: str = Field(..., description="Core underlying concept, law, or theorem")
    governing_formulas: List[str] = Field(default_factory=list, description="LaTeX formatted formulas")
    hint_content: str = Field(..., description="Main pedagogical guidance text")
    probing_question: str = Field(..., description="Reflective question to prompt student's next step")
    latex_math_blocks: List[str] = Field(default_factory=list, description="Step equations and LaTeX blocks")
    pitfall_warning: Optional[str] = Field(None, description="Common mistakes, sign errors, or domain restrictions")
    next_tier_available: bool = Field(True, description="Whether higher hint tiers can be unlocked")


class ProgressiveHintRequest(BaseModel):
    session_id: str
    target_tier: int = Field(..., ge=1, le=3, description="Target hint level requested by student")
    student_notes: Optional[str] = Field(None, description="Optional intermediate steps attempted by student")


class ProgressiveHintResponse(BaseModel):
    session_id: str
    hint: HintContent
    session_resolved: bool = False
    message: str = "Hint generated successfully"


class StudentAttemptRequest(BaseModel):
    session_id: str
    student_attempt_text: str = Field(..., min_length=1, description="Student's work or answer attempt")


class StudentAttemptResponse(BaseModel):
    session_id: str
    is_on_track: bool
    feedback: str
    socratic_guidance: str
    recommended_action: str  # 'continue_current_tier', 'proceed_to_next_tier', 'verified_solution'
