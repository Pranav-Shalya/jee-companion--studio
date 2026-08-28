#!/usr/bin/env python3
"""
Automated Evaluation Suite for JEE RAG & Hint Generation Engine
Evaluates Retrieval-Augmented Generation quality, Keyword Recall, and Semantic Cosine Similarity.
"""

import os
import sys
import time
import json
import asyncio
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend root to sys.path
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import httpx
import numpy as np
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# 1. Standard JEE Benchmark Evaluation Dataset
# ---------------------------------------------------------------------------
EVALUATION_DATASET: List[Dict[str, Any]] = [
    {
        "id": "TC-PHY-01",
        "subject": "Physics",
        "topic": "Rotational Dynamics & Pure Rolling",
        "query": "A solid sphere of mass M and radius R rolls without slipping down an inclined plane of angle theta. Find its linear acceleration.",
        "ground_truth_keywords": [
            "rolling",
            "friction",
            "torque",
            "moment of inertia",
            "acceleration",
            "sin",
            "2/5",
        ],
        "ground_truth_reference": (
            "A solid sphere rolling without slipping down an incline of angle theta experiences gravity Mg sin(theta) "
            "and static friction f providing torque about its center of mass. Using torque = I*alpha with I = (2/5)MR^2 "
            "and a = alpha*R, Newton's second law Mg sin(theta) - f = Ma yields an acceleration of a = (5/7)g sin(theta)."
        ),
    },
    {
        "id": "TC-PHY-02",
        "subject": "Physics",
        "topic": "Electromagnetism & Cyclotron Motion",
        "query": "A particle of mass m and charge q enters a uniform magnetic field B with velocity v perpendicular to the field. Determine the radius of the circular path and cyclotron frequency.",
        "ground_truth_keywords": [
            "magnetic",
            "Lorentz",
            "centripetal",
            "radius",
            "cyclotron",
            "frequency",
            "q",
            "B",
        ],
        "ground_truth_reference": (
            "When a charge q enters perpendicular to a uniform magnetic field B, the magnetic Lorentz force F = qvB "
            "acts as the centripetal force mv^2/r. The orbital radius is r = mv/(qB) and the cyclotron frequency "
            "is f = qB/(2*pi*m), independent of velocity and radius."
        ),
    },
    {
        "id": "TC-CHEM-01",
        "subject": "Chemistry",
        "topic": "Chemical Equilibrium & Le Chatelier",
        "query": "For the Haber synthesis of ammonia N2(g) + 3H2(g) <=> 2NH3(g) with Delta H < 0, explain the effect of increasing pressure and temperature on the equilibrium yield according to Le Chatelier's principle.",
        "ground_truth_keywords": [
            "Le Chatelier",
            "equilibrium",
            "pressure",
            "temperature",
            "exothermic",
            "forward",
            "moles",
        ],
        "ground_truth_reference": (
            "The Haber ammonia synthesis is an exothermic reaction (Delta H < 0) accompanied by a decrease in gaseous moles "
            "(4 moles reactant to 2 moles product). According to Le Chatelier's principle, increasing pressure shifts equilibrium "
            "forward to increase ammonia yield, while increasing temperature shifts equilibrium in the reverse endothermic direction."
        ),
    },
    {
        "id": "TC-CHEM-02",
        "subject": "Chemistry",
        "topic": "Organic Carbonyl Mechanisms (Aldol vs Cannizzaro)",
        "query": "Explain the structural requirement that differentiates aldehydes undergoing Aldol condensation from those undergoing the Cannizzaro reaction in the presence of strong base.",
        "ground_truth_keywords": [
            "alpha-hydrogen",
            "Aldol",
            "Cannizzaro",
            "enolate",
            "disproportionation",
            "carbonyl",
            "base",
        ],
        "ground_truth_reference": (
            "Aldol condensation requires aldehydes or ketones with at least one alpha-hydrogen capable of forming a resonance-stabilized "
            "enolate nucleophile upon deprotonation by base. Aldehydes lacking alpha-hydrogens (such as formaldehyde or benzaldehyde) "
            "cannot form enolates and instead undergo the Cannizzaro self-oxidation-reduction (disproportionation) reaction."
        ),
    },
    {
        "id": "TC-MATH-01",
        "subject": "Mathematics",
        "topic": "Definite Integrals & King's Symmetry Rule",
        "query": "Evaluate the definite integral I = \\int_0^{\\pi/2} \\frac{\\sqrt{\\sin x}}{\\sqrt{\\sin x} + \\sqrt{\\cos x}} dx using King's symmetry property.",
        "ground_truth_keywords": [
            "King",
            "definite integral",
            "symmetry",
            "pi/4",
            "f(a+b-x)",
            "cos",
            "sin",
        ],
        "ground_truth_reference": (
            "Applying King's property of definite integrals int_a^b f(x)dx = int_a^b f(a+b-x)dx, replacing x with (pi/2 - x) "
            "swaps sin(x) and cos(x). Adding the original and transformed integrals gives 2I = int_0^(pi/2) 1 dx = pi/2, "
            "yielding the final result I = pi/4."
        ),
    },
]


# ---------------------------------------------------------------------------
# 2. Metric Computation Helpers
# ---------------------------------------------------------------------------
def compute_keyword_recall(
    generated_text: str, keywords: List[str]
) -> Tuple[float, List[str], List[str]]:
    """
    Computes Keyword Recall percentage against ground-truth keywords.
    Matches normalized tokens (case-insensitive, ignoring special punctuation).
    """
    if not keywords:
        return 100.0, [], []

    norm_text = generated_text.lower().replace("$", "").replace("\\", " ")
    matched = []
    missed = []

    for kw in keywords:
        norm_kw = kw.lower().replace("$", "").replace("\\", " ").strip()
        # Substring or token check
        if norm_kw in norm_text:
            matched.append(kw)
        else:
            # Check individual alphanumeric tokens for multi-word formulas
            tokens = [t for t in norm_kw.split() if len(t) > 1]
            if tokens and all(t in norm_text for t in tokens):
                matched.append(kw)
            else:
                missed.append(kw)

    recall_pct = (len(matched) / len(keywords)) * 100.0
    return recall_pct, matched, missed


def compute_semantic_similarity(
    model: SentenceTransformer, generated_text: str, ground_truth_text: str
) -> float:
    """
    Computes Cosine Semantic Similarity between generated response and ground truth reference.
    """
    if not generated_text or not ground_truth_text:
        return 0.0

    emb_gen = model.encode(generated_text, convert_to_numpy=True, normalize_embeddings=True)
    emb_gt = model.encode(ground_truth_text, convert_to_numpy=True, normalize_embeddings=True)

    similarity = float(np.dot(emb_gen, emb_gt))
    return max(0.0, min(1.0, similarity))


# ---------------------------------------------------------------------------
# 3. Execution Engines (HTTP Client & In-Process Direct Fallback)
# ---------------------------------------------------------------------------
async def execute_via_http(
    base_url: str, test_case: Dict[str, Any]
) -> Dict[str, Any]:
    """Sends async request to local FastAPI backend."""
    url = f"{base_url.rstrip('/')}/api/v1/doubts/intake"
    payload = {
        "subject": test_case["subject"],
        "query_text": test_case["query"],
        "topic_hint": test_case["topic"],
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        res = await client.post(url, json=payload)
        res.raise_for_status()
        data = res.json()

        hint_obj = data.get("initial_hint") or {}
        hint_content = hint_obj.get("hint_content") or ""
        concept_summary = hint_obj.get("concept_summary") or ""
        formulas = " ".join(hint_obj.get("governing_formulas") or [])
        pitfalls = hint_obj.get("pitfall_warning") or ""

        combined_response = f"{concept_summary}\n{hint_content}\n{formulas}\n{pitfalls}".strip()

        return {
            "status": "success",
            "source": "http_api",
            "session_id": data.get("session_id"),
            "topic": data.get("topic"),
            "response_text": combined_response,
            "retrieved_context": concept_summary,
        }


async def execute_in_process(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Direct in-process invocation of RAGEngineService and MultiLLMConsensusService."""
    from app.schemas.session import SubjectEnum
    from app.services.rag_engine import rag_engine_service
    from app.services.multi_llm_consensus import multi_llm_consensus_service

    subject_val = SubjectEnum(test_case["subject"])
    query = test_case["query"]

    # 1. RAG Retrieval with Cross-Encoder Reranking
    context_chunks = await rag_engine_service.retrieve_context(
        query=query, subject=subject_val, top_k=3
    )
    context_text = "\n".join([c.get("text", "") or c.get("concept", "") for c in context_chunks])

    # 2. Multi-LLM Progressive Hint Generation
    escalation = await multi_llm_consensus_service.generate_hint_escalation(
        query=query,
        subject=subject_val,
        context_chunks=context_chunks,
    )

    combined_response = (
        f"Topic: {escalation.core_topic} ({escalation.complexity_level})\n\n"
        f"Tier 1 Conceptual Nudge:\n{escalation.hint_1_concept}\n\n"
        f"Tier 2 Structural Strategy:\n{escalation.hint_2_structure}\n\n"
        f"Tier 3 Calculation Roadmap:\n{escalation.hint_3_calculation}\n\n"
        f"Master Proof:\n{escalation.master_solution}"
    )

    return {
        "status": "success",
        "source": "in_process_service",
        "topic": escalation.core_topic,
        "response_text": combined_response,
        "retrieved_context": context_text,
        "chunks_count": len(context_chunks),
    }


# ---------------------------------------------------------------------------
# 4. Main Evaluation Runner
# ---------------------------------------------------------------------------
async def run_rag_evaluation(
    base_url: str = "http://localhost:8000",
    force_direct: bool = False,
    save_report: Optional[str] = None,
) -> Dict[str, Any]:
    print("=" * 82)
    print("      [EVAL] JEE PROGRESSIVE RAG ENGINE - AUTOMATED EVALUATION SUITE")
    print("=" * 82)
    print(f"Target Backend: {base_url} (Direct Fallback: Enabled)")
    print(f"Embedding Model: sentence-transformers/all-MiniLM-L6-v2 (CPU)")
    print(f"Total Benchmark Test Cases: {len(EVALUATION_DATASET)}")
    print("-" * 82)

    # Initialize SentenceTransformer
    print("\nLoading local evaluation embedding model...")
    eval_embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    print("[OK] Model loaded successfully.\n")

    results = []
    overall_start_time = time.time()

    for idx, tc in enumerate(EVALUATION_DATASET, start=1):
        tc_id = tc["id"]
        subj = tc["subject"]
        topic = tc["topic"]
        query = tc["query"]
        keywords = tc["ground_truth_keywords"]
        gt_ref = tc["ground_truth_reference"]

        print(f"[{idx}/{len(EVALUATION_DATASET)}] Evaluating {tc_id} ({subj} - {topic})...")
        t0 = time.time()

        exec_res = None
        if not force_direct:
            try:
                exec_res = await execute_via_http(base_url, tc)
            except Exception as http_err:
                print(f"   [INFO] HTTP API unreachable ({http_err.__class__.__name__}). Using in-process RAG engine fallback...")

        if exec_res is None:
            try:
                exec_res = await execute_in_process(tc)
            except Exception as proc_err:
                print(f"   [ERROR] Execution failed: {proc_err}")
                exec_res = {
                    "status": "error",
                    "source": "failed",
                    "response_text": "",
                    "retrieved_context": "",
                }

        latency = time.time() - t0
        resp_text = exec_res.get("response_text", "")
        retrieved_text = exec_res.get("retrieved_context", "")

        # Unified text for recall inspection
        corpus = f"{retrieved_text}\n{resp_text}"

        # 1. Keyword Recall
        recall_pct, matched_kws, missed_kws = compute_keyword_recall(corpus, keywords)

        # 2. Semantic Cosine Similarity
        similarity = compute_semantic_similarity(eval_embedding_model, resp_text, gt_ref)

        # 3. Composite RAG Score (40% Keyword Recall + 60% Semantic Similarity)
        composite_score = round(0.4 * recall_pct + 0.6 * (similarity * 100.0), 2)

        is_passed = composite_score >= 65.0

        res_entry = {
            "index": idx,
            "id": tc_id,
            "subject": subj,
            "topic": topic,
            "query": query,
            "keyword_recall_pct": round(recall_pct, 1),
            "matched_keywords": matched_kws,
            "missed_keywords": missed_kws,
            "semantic_similarity": round(similarity, 4),
            "composite_score": composite_score,
            "latency_sec": round(latency, 2),
            "passed": is_passed,
            "execution_source": exec_res.get("source"),
            "response_preview": resp_text[:180] + "..." if len(resp_text) > 180 else resp_text,
        }
        results.append(res_entry)

        status_tag = "PASS" if is_passed else "REVIEW"
        print(
            f"   -> Result: [{status_tag}] Recall: {recall_pct:.1f}% | "
            f"Semantic Sim: {similarity:.4f} | Composite: {composite_score:.1f}% | Time: {latency:.2f}s"
        )
        if missed_kws:
            print(f"      Missed Keywords: {missed_kws}")
        print()

    total_duration = time.time() - overall_start_time

    # ---------------------------------------------------------------------------
    # 5. Formatted Terminal Summary Report
    # ---------------------------------------------------------------------------
    avg_recall = np.mean([r["keyword_recall_pct"] for r in results])
    avg_similarity = np.mean([r["semantic_similarity"] for r in results])
    avg_composite = np.mean([r["composite_score"] for r in results])
    pass_count = sum(1 for r in results if r["passed"])

    print("=" * 82)
    print("                      [REPORT] RAG EVALUATION BENCHMARK")
    print("=" * 82)
    print(
        f"{'ID':<12} | {'Subject':<11} | {'Recall':<9} | {'Semantic Sim':<13} | {'Composite':<10} | {'Status':<6} | {'Time'}"
    )
    print("-" * 82)
    for r in results:
        status_str = "PASS" if r["passed"] else "FAIL"
        print(
            f"{r['id']:<12} | {r['subject']:<11} | {r['keyword_recall_pct']:>6.1f}%  | {r['semantic_similarity']:>12.4f}  | {r['composite_score']:>8.1f}%  | {status_str:<6} | {r['latency_sec']:.2f}s"
        )
    print("-" * 82)
    print(
        f"{'AVERAGE':<12} | {'All Subj':<11} | {avg_recall:>6.1f}%  | {avg_similarity:>12.4f}  | {avg_composite:>8.1f}%  | {pass_count}/{len(results)} Passed"
    )
    print("=" * 82)

    overall_system_status = "PASSED (Production Ready)" if avg_composite >= 70.0 else "NEEDS REVIEW"
    print(f"\n[SUMMARY] Overall RAG Engine Status: {overall_system_status}")
    print(f"[TIME] Total Evaluation Duration: {total_duration:.2f}s\n")

    summary_payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_test_cases": len(results),
        "passed_count": pass_count,
        "average_keyword_recall_pct": round(float(avg_recall), 2),
        "average_semantic_similarity": round(float(avg_similarity), 4),
        "overall_system_rag_score": round(float(avg_composite), 2),
        "overall_status": overall_system_status,
        "results": results,
    }

    if save_report:
        report_path = Path(save_report).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(summary_payload, f, indent=2)
        print(f"📁 Evaluation report saved to: {report_path}")

    return summary_payload


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate JEE RAG & Hint Generation Pipeline")
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000",
        help="Base URL of local FastAPI server (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Force direct in-process execution without HTTP API requests",
    )
    parser.add_argument(
        "--save-report",
        type=str,
        default=None,
        help="Optional path to write JSON evaluation report",
    )

    args = parser.parse_args()
    asyncio.run(
        run_rag_evaluation(
            base_url=args.base_url,
            force_direct=args.direct,
            save_report=args.save_report,
        )
    )
