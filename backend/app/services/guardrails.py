import re
import logging
from typing import Tuple, List
from app.schemas.session import SubjectEnum
from app.schemas.doubts import SyllabusValidationResult
from app.schemas.hints import HintContent

logger = logging.getLogger(__name__)

# Disallowed out-of-syllabus topics for JEE Main/Advanced
OUT_OF_SYLLABUS_KEYWORDS = {
    SubjectEnum.PHYSICS: [
        "lagrangian", "hamiltonian", "general relativity", "schrodinger equation",
        "quantum electrodynamics", "string theory", "feynman diagram", "lorentz transformation",
        "tensors", "curved spacetime", "quarks and gluons"
    ],
    SubjectEnum.CHEMISTRY: [
        "organocuprate cross-coupling outside ncert", "pericyclic reactions beyond diels-alder basics",
        "spectroscopy nmr 2d", "supramolecular chemistry", "advanced bioinorganic crystal structures"
    ],
    SubjectEnum.MATHEMATICS: [
        "multivariable line integral", "stokes theorem", "green theorem in 3d",
        "abstract algebra", "galois theory", "complex contour integration",
        "lebesgue integral", "topology", "manifold"
    ],
}


class GuardrailsService:
    """Enforces JEE syllabus boundaries and prevents direct answer leaks."""

    @classmethod
    def validate_syllabus(cls, query: str, subject: SubjectEnum) -> SyllabusValidationResult:
        query_lower = query.lower()
        forbidden_list = OUT_OF_SYLLABUS_KEYWORDS.get(subject, [])

        for forbidden in forbidden_list:
            if forbidden in query_lower:
                logger.warning("Query contains out-of-syllabus term: %s", forbidden)
                return SyllabusValidationResult(
                    is_valid_jee=False,
                    subject=subject,
                    topic="Out-of-Syllabus / Advanced Topic",
                    syllabus_tier="University Level / Excluded",
                    flagged_reasons=f"Topic involves '{forbidden}', which is outside the official JEE Main & Advanced syllabus.",
                    jee_redirection_advice=(
                        f"For JEE, focus instead on standard {subject.value} concepts such as Newtonian Mechanics, "
                        "Calculus, or Standard NCERT Chemical Reactions."
                    ),
                )

        return SyllabusValidationResult(
            is_valid_jee=True,
            subject=subject,
            topic="JEE Main & Advanced Core",
            syllabus_tier="JEE Main / Advanced",
            flagged_reasons=None,
            jee_redirection_advice=None,
        )

    @classmethod
    def enforce_hint_tier_guardrails(cls, hint: HintContent) -> HintContent:
        """
        Ensures Tier 1 and Tier 2 never accidentally disclose the complete answer number or option.
        """
        if hint.tier in [1, 2]:
            # Replace accidental direct declarations like "The final answer is X" or "Option (B)"
            cleaned_content = re.sub(
                r"(?i)(the final answer is|therefore the option is|correct option is)\s*[A-D0-9\.\-]+",
                "[Guarded: Work through the formula to deduce the value]",
                hint.hint_content,
            )
            hint.hint_content = cleaned_content
        return hint


guardrails_service = GuardrailsService()
