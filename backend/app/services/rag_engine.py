import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient
from qdrant_client import models as qmodels

from app.core.config import settings
from app.schemas.session import SubjectEnum

logger = logging.getLogger(__name__)

# Default persistent directory for embedded Qdrant
QDRANT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "qdrant_db"


class RAGEngineService:
    """
    Retrieval Augmented Generation service for JEE knowledge base and PYQs
    equipped with dense vector search and Cross-Encoder reranking.
    """

    def __init__(self):
        self.qdrant_host = settings.QDRANT_HOST
        self.qdrant_port = settings.QDRANT_PORT
        self.collection_name = settings.QDRANT_COLLECTION_NAME or "jee_knowledge_base"
        self._is_connected = False
        self.client = None

        # Model singletons on CPU (lazy initialized or explicit)
        self._embedding_model: Optional[SentenceTransformer] = None
        self._reranker: Optional[CrossEncoder] = None

    @property
    def reranker(self) -> CrossEncoder:
        """Initializes and returns CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2') on local CPU."""
        if self._reranker is None:
            logger.info("Initializing CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2') on CPU...")
            self._reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device="cpu")
        return self._reranker

    @reranker.setter
    def reranker(self, value: Optional[CrossEncoder]):
        self._reranker = value

    @property
    def embedding_model(self) -> SentenceTransformer:
        """Initializes and returns SentenceTransformer('all-MiniLM-L6-v2') on local CPU."""
        if self._embedding_model is None:
            logger.info("Initializing SentenceTransformer('all-MiniLM-L6-v2') on CPU...")
            self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        return self._embedding_model

    @embedding_model.setter
    def embedding_model(self, value: Optional[SentenceTransformer]):
        self._embedding_model = value

    def get_embedding_model(self) -> SentenceTransformer:
        """Helper method returning the initialized SentenceTransformer instance."""
        return self.embedding_model

    def get_reranker(self) -> CrossEncoder:
        """Helper method returning the initialized CrossEncoder instance."""
        return self.reranker

    def get_qdrant_client(self) -> QdrantClient:
        """Returns a connected QdrantClient instance."""
        try:
            return QdrantClient(path=str(QDRANT_DB_PATH))
        except Exception as lock_err:
            logger.warning("Local Qdrant directory locked (%s). Connecting to %s:%s...", lock_err, self.qdrant_host, self.qdrant_port)
            try:
                return QdrantClient(url=f"http://{self.qdrant_host}:{self.qdrant_port}", timeout=10.0)
            except Exception:
                return QdrantClient(path=str(QDRANT_DB_PATH))

    async def initialize_client(self):
        try:
            from qdrant_client import AsyncQdrantClient
            self.client = AsyncQdrantClient(host=self.qdrant_host, port=self.qdrant_port)
            self._is_connected = True
            logger.info("Connected to Qdrant vector database at %s:%s", self.qdrant_host, self.qdrant_port)
        except Exception as e:
            logger.warning("Could not initialize async Qdrant client (%s). Using local Qdrant fallback.", e)
            self._is_connected = False

    async def retrieve_context(
        self,
        query: str,
        subject: Optional[Union[SubjectEnum, str]] = None,
        top_k: int = 3,
        overfetch_limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves relevant conceptual chunks, formulas, and pitfalls using a Cross-Encoder Reranking pipeline:
        Step A: Over-fetch by querying Qdrant for the top limit=15 or 20 results using dense vector search.
        Step B: Extract the text content from the hit.payload of those results.
        Step C: Create a list of pairs for the reranker: pairs = [[user_query, doc_text] for doc_text in extracted_texts].
        Step D: Score the pairs: scores = self.reranker.predict(pairs).
        Step E: Zip the scores with the original payloads, sort them descending by score, and return top_k (top 3 or 5).
        Fallback: If the reranker fails, gracefully falls back to the original Qdrant sorting or curated knowledge bank.
        """
        subject_name = subject.value if isinstance(subject, SubjectEnum) else (str(subject) if subject else "")
        logger.info("Retrieving RAG knowledge context for query in [%s]: '%s'", subject_name, query[:60])

        candidate_payloads: List[Dict[str, Any]] = []
        extracted_texts: List[str] = []

        try:
            client = self.get_qdrant_client()
            search_query = f"{subject_name} {query}".strip() if subject_name else query
            query_vector = self.embedding_model.encode(search_query).tolist()

            subject_filter = (
                qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="subject",
                            match=qmodels.MatchValue(value=subject_name),
                        )
                    ]
                )
                if subject_name
                else None
            )

            # Step A: Over-fetch by querying Qdrant for the top limit=15 or 20 results using the existing dense vector search
            search_hits = []
            if hasattr(client, "query_points"):
                res = client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    query_filter=subject_filter,
                    limit=overfetch_limit,
                    with_payload=True,
                    with_vectors=False,
                )
                search_hits = getattr(res, "points", [])
            elif hasattr(client, "search"):
                search_hits = client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    query_filter=subject_filter,
                    limit=overfetch_limit,
                    with_payload=True,
                    with_vectors=False,
                )

            # Step B: Extract the text content from the hit.payload of those 20 results
            for hit in search_hits:
                payload = hit.payload or {}
                doc_text = (
                    payload.get("text")
                    or payload.get("combined_text")
                    or payload.get("concept")
                    or payload.get("question_text")
                    or ""
                ).strip()

                # Parse formulas/pitfalls JSON if serialized
                formulas = payload.get("formulas") or []
                if isinstance(formulas, str):
                    try:
                        formulas = json.loads(formulas)
                    except Exception:
                        formulas = [formulas]

                pitfalls = payload.get("common_pitfalls") or payload.get("pitfalls") or ""
                if isinstance(pitfalls, list):
                    pitfalls = "; ".join(str(p) for p in pitfalls)

                normalized_item = {
                    "concept": payload.get("topic") or payload.get("concept") or payload.get("chapter") or "Core JEE Concept",
                    "text": doc_text,
                    "formulas": formulas,
                    "pitfalls": pitfalls,
                    "syllabus_tier": payload.get("difficulty_level") or payload.get("syllabus_tier") or "JEE Main & Advanced",
                }

                candidate_payloads.append(normalized_item)
                extracted_texts.append(doc_text or normalized_item["concept"])

            logger.info("Qdrant dense vector search over-fetched %d candidate chunks.", len(candidate_payloads))

        except Exception as qdrant_err:
            logger.warning("Qdrant candidate retrieval encountered error: %s. Using knowledge bank fallback.", qdrant_err)

        # Cross-Encoder Reranking Pipeline
        if candidate_payloads and extracted_texts:
            try:
                # Step C: Create a list of pairs for the reranker: pairs = [[user_query, doc_text] for doc_text in extracted_texts]
                pairs = [[query, doc_text] for doc_text in extracted_texts]

                # Step D: Score the pairs: scores = self.reranker.predict(pairs)
                scores = self.reranker.predict(pairs)

                # Step E: Zip the scores with the original payloads, sort them descending by score, and return only the top 3 or 5 payloads
                scored_results = list(zip(scores, candidate_payloads))
                scored_results.sort(key=lambda item: float(item[0]), reverse=True)

                top_reranked = [payload for _, payload in scored_results[:top_k]]
                logger.info(
                    "Cross-Encoder successfully reranked %d candidates. Returning top %d (Top Score: %.4f).",
                    len(scored_results),
                    len(top_reranked),
                    float(scored_results[0][0]) if scored_results else 0.0,
                )
                return top_reranked

            except Exception as rerank_err:
                # Graceful fallback to original Qdrant sorting if reranker fails
                logger.warning("Cross-Encoder reranker failed (%s). Gracefully falling back to original Qdrant sorting.", rerank_err)
                return candidate_payloads[:top_k]

        # In-memory Curated JEE knowledge mapping fallback
        logger.info("Using curated in-memory knowledge bank fallback for [%s].", subject_name)
        topic_knowledge_bank = {
            SubjectEnum.PHYSICS: [
                {
                    "concept": "Kinematics & Circular Motion",
                    "formulas": [
                        r"\vec{a}_{\text{avg}} = \frac{\Delta \vec{v}}{\Delta t}",
                        r"a_c = \frac{v^2}{R} = \omega^2 R",
                        r"a_t = \frac{dv}{dt} = \alpha R",
                    ],
                    "pitfalls": "Confusion between instantaneous radial acceleration and vector average acceleration over a finite interval.",
                    "syllabus_tier": "JEE Main & Advanced",
                },
                {
                    "concept": "Rotational Dynamics & Angular Momentum",
                    "formulas": [
                        r"\vec{\tau}_{\text{ext}} = \frac{d\vec{L}}{dt}",
                        r"L = I\omega + (\vec{r}_{\text{cm}} \times m\vec{v}_{\text{cm}})",
                        r"K_{\text{total}} = \frac{1}{2}mv_{\text{cm}}^2 + \frac{1}{2}I_{\text{cm}}\omega^2",
                    ],
                    "pitfalls": "Choosing an unaccelerated reference point or failing to account for pseudo-torque when computing about non-inertial points.",
                    "syllabus_tier": "JEE Advanced",
                },
            ],
            SubjectEnum.CHEMISTRY: [
                {
                    "concept": "Chemical Equilibrium & Le Chatelier Principle",
                    "formulas": [
                        r"\Delta G^\circ = -RT \ln K_{\text{eq}}",
                        r"Q_c = \frac{\prod [P]^{p_i}}{\prod [R]^{r_i}}",
                    ],
                    "pitfalls": "Ignoring solid state activities (pure solids and liquids have activity = 1).",
                    "syllabus_tier": "JEE Main & Advanced",
                },
                {
                    "concept": "Aldol and Cannizzaro Carbonyl Reactions",
                    "formulas": [
                        r"\text{Enolate Formation: } R\text{-}CH_2\text{-}CHO + OH^- \rightleftharpoons [R\text{-}CH\text{-}CHO]^- + H_2O",
                    ],
                    "pitfalls": "Failing to check for alpha-hydrogen presence to distinguish Aldol from Cannizzaro pathways.",
                    "syllabus_tier": "JEE Main & Advanced",
                },
            ],
            SubjectEnum.MATHEMATICS: [
                {
                    "concept": "Definite Integrals & King's Property",
                    "formulas": [
                        r"\int_a^b f(x) dx = \int_a^b f(a + b - x) dx",
                        r"\int_0^{2a} f(x) dx = \int_0^a f(x) dx + \int_0^a f(2a - x) dx",
                    ],
                    "pitfalls": "Applying properties across non-continuous points or discontinuous fractional-part functions without partitioning.",
                    "syllabus_tier": "JEE Main & Advanced",
                },
            ],
        }

        # Resolve subject key for in-memory bank
        enum_subject = None
        if isinstance(subject, SubjectEnum):
            enum_subject = subject
        elif subject_name:
            for s in SubjectEnum:
                if s.value.lower() == subject_name.lower():
                    enum_subject = s
                    break

        return topic_knowledge_bank.get(enum_subject, []) if enum_subject else []


rag_engine_service = RAGEngineService()
