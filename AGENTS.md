# Agent Guidelines: JEE Doubt Solver

This document defines core constraints, pedagogical rules, and architectural standards for all AI agents generating code or prompts in this repository.

---

## 1. Core Principles

1. **Pedagogical Goal**: Foster active problem-solving and critical thinking rather than passive solution copying.
2. **Syllabus Integrity**: Strictly stay within the official JEE Main & JEE Advanced boundaries.
3. **Progressive Scaffolding**: Guide the student step-by-step using a 3-tier progressive hint framework.

---

## 2. JEE Main & Advanced Syllabus Boundaries

All agent-generated prompts, validation logic, problem databases, and AI-assisted responses must strictly adhere to the official syllabus specifications for JEE Main and JEE Advanced:

### Scope Constraints
- **Physics**: Classical Mechanics, Thermodynamics & Thermal Physics, Electromagnetism, Optics, Modern Physics, Waves & Sound, and Experimental Skills specified in the official JEE syllabus. Avoid university-level formalisms (e.g., Lagrangian/Hamiltonian mechanics, relativistic electrodynamics, general relativity).
- **Chemistry**:
  - **Physical Chemistry**: Atomic structure, chemical bonding, thermodynamics, chemical and ionic equilibrium, electrochemistry, chemical kinetics, solid state, solutions, surface chemistry.
  - **Inorganic Chemistry**: Periodic properties, coordination compounds, p-block, d-block, f-block, metallurgy, qualitative salt analysis within NCERT & JEE Advanced scope.
  - **Organic Chemistry**: Reaction mechanisms, stereochemistry, aliphatic and aromatic hydrocarbons, functional groups, polymers, biomolecules, and organic synthesis within standard JEE scope. Out-of-syllabus esoteric synthetic reagents must not be introduced.
- **Mathematics**: Algebra, Trigonometry, Analytical Geometry (2D & 3D), Differential Calculus, Integral Calculus, Vectors, Statistics, and Probability. Exclude multivariable calculus, abstract algebra, or advanced linear algebra beyond standard matrices and determinants.

### Out-of-Syllabus Handling
- If a user query falls outside the JEE syllabus, the backend/agent must politely flag that the topic is outside the JEE domain and offer either:
  1. A constrained JEE-applicable perspective/simplification, or
  2. Guidance directing the student back to relevant JEE topics.

---

## 3. 3-Tier Progressive Hint Enforcement

**Crucial Requirement**: The backend and AI generation pipelines must **never** output direct answers or complete end-to-end solutions in the initial response. All solution paths must be gated behind a 3-tier progressive hint system.

```
                  ┌────────────────────────────────────────┐
                  │              User Doubt                │
                  └──────────────────┬─────────────────────┘
                                     ▼
                  ┌────────────────────────────────────────┐
                  │      Tier 1: Conceptual Nudge          │
                  │ (Core concept, principles & formulas)  │
                  └──────────────────┬─────────────────────┘
                                     ▼ (if student needs more)
                  ┌────────────────────────────────────────┐
                  │      Tier 2: Structural Strategy       │
                  │ (Equation setup, workflow & roadmap)   │
                  └──────────────────┬─────────────────────┘
                                     ▼ (if student needs more)
                  ┌────────────────────────────────────────┐
                  │      Tier 3: Detailed Walkthrough      │
                  │ (Intermediate steps; student evaluates)│
                  └────────────────────────────────────────┘
```

### Hint Breakdown

| Tier | Level Name | Purpose & Content | What is NOT Allowed |
| :--- | :--- | :--- | :--- |
| **Tier 1** | **Conceptual Nudge** | • Identifies the core concept, key law, or theorem (e.g., Conservation of Angular Momentum, Le Chatelier's Principle, Rolle's Theorem).<br>• Reminds the student of relevant governing formulas and definitions.<br>• Asks a reflective leading question. | No numerical calculations, no problem-specific equation setups, no final answers. |
| **Tier 2** | **Structural Guidance & Setup** | • Breaks the problem into actionable sub-steps.<br>• Provides the setup equations, coordinate conventions, or free-body diagram descriptions.<br>• Highlights potential pitfalls or edge cases (e.g., pseudo forces, standard states, domain restrictions). | No final arithmetic evaluations, no direct algebraic substitution yielding the final numerical answer. |
| **Tier 3** | **Detailed Walkthrough (Near-Solution)** | • Details intermediate mathematical substitutions and algebraic manipulations.<br>• Walks through 80–90% of the solution path.<br>• Leaves the final computation, value substitution, or concluding deduction for the student to verify. | Complete verbatim revelation of the final answer option/number without requiring the student's active step. |

---

## 4. Backend Implementation Guidelines

When implementing backend services (APIs, LLM chains, state machines, or orchestrators):

1. **Stateful Hint Progression**:
   - Maintain conversation state tracking the current hint tier for each active doubt/question session (`tier_1`, `tier_2`, `tier_3`).
   - Allow students to request the next tier only when needed or after attempting to answer.

2. **System Prompt Guardrails**:
   - Every system prompt generated for LLM doubt resolution must include explicit constraints forbidding direct answer revelation and enforcing the active hint tier structure.

3. **Response Schema Enforcement**:
   - Use structured response schemas (e.g., Pydantic models / JSON schemas) that clearly distinguish `concept_summary`, `hint_tier`, `hint_content`, `probing_question`, and `latex_math_blocks`.

4. **Mathematical and Chemical Notation**:
   - Format all mathematical equations in standard LaTeX (`$...$` for inline, `$$...$$` for block).
   - Format chemical reactions and structures with proper IUPAC/LaTeX chemical notation.
