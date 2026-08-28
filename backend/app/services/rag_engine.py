import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
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
    equipped with FastEmbed dense vector search.
    """

    def __init__(self):
        self.qdrant_host = settings.QDRANT_HOST
        self.qdrant_port = settings.QDRANT_PORT
        self.collection_name = settings.QDRANT_COLLECTION_NAME or "jee_knowledge_base"
        self._is_connected = False
        self.client = None

        # Model singletons on CPU (lazy initialized or explicit)
        self._embedding_model: Optional[FastEmbedEmbeddings] = None

    @property
    def embedding_model(self) -> FastEmbedEmbeddings:
        """Initializes and returns FastEmbedEmbeddings('BAAI/bge-small-en-v1.5')."""
        if self._embedding_model is None:
            logger.info("Initializing FastEmbedEmbeddings('BAAI/bge-small-en-v1.5')...")
            self._embedding_model = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
        return self._embedding_model

    @embedding_model.setter
    def embedding_model(self, value: Optional[FastEmbedEmbeddings]):
        self._embedding_model = value

    def get_embedding_model(self) -> FastEmbedEmbeddings:
        """Helper method returning the initialized FastEmbedEmbeddings instance."""
        return self.embedding_model

    def get_qdrant_client(self) -> QdrantClient:
        """Returns a connected QdrantClient instance supporting Qdrant Cloud and local storage."""
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

    async def initialize_client(self):
        try:
            from qdrant_client import AsyncQdrantClient
            if settings.QDRANT_URL:
                self.client = AsyncQdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY,
                )
            else:
                self.client = AsyncQdrantClient(
                    host=settings.QDRANT_HOST,
                    port=settings.QDRANT_PORT,
                    api_key=settings.QDRANT_API_KEY,
                )
            self._is_connected = True
            logger.info("Connected to Qdrant vector database.")
        except Exception as e:
            logger.warning("Could not initialize async Qdrant client (%s). Using local Qdrant fallback.", e)
            self._is_connected = False

    async def retrieve_context(
        self,
        query: str,
        subject: Optional[Union[SubjectEnum, str]] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves relevant conceptual chunks, formulas, and pitfalls using dense vector search.
        Performs direct query embedding and Qdrant vector search, returning top results immediately.
        Fallback: If Qdrant retrieval fails or returns no points, gracefully falls back to the curated knowledge bank.
        """
        subject_name = subject.value if isinstance(subject, SubjectEnum) else (str(subject) if subject else "")
        logger.info("Retrieving RAG knowledge context for query in [%s]: '%s'", subject_name, query[:60])

        candidate_payloads: List[Dict[str, Any]] = []

        try:
            client = self.get_qdrant_client()
            search_query = f"{subject_name} {query}".strip() if subject_name else query
            query_vector = self.embedding_model.embed_query(search_query)

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

            # Direct dense vector search for top_k results
            search_hits = []
            if hasattr(client, "query_points"):
                res = client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    query_filter=subject_filter,
                    limit=top_k,
                    with_payload=True,
                    with_vectors=False,
                )
                search_hits = getattr(res, "points", [])
            elif hasattr(client, "search"):
                search_hits = client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    query_filter=subject_filter,
                    limit=top_k,
                    with_payload=True,
                    with_vectors=False,
                )

            # Extract and normalize payloads
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

            if candidate_payloads:
                logger.info("Qdrant dense vector search returned %d candidate chunks.", len(candidate_payloads))
                return candidate_payloads

        except Exception as qdrant_err:
            logger.warning("Qdrant candidate retrieval encountered error: %s. Using knowledge bank fallback.", qdrant_err)

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
