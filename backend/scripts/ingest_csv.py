#!/usr/bin/env python3
"""
Bulk CSV Ingestion Script for JEE Datasets into Qdrant using Local CPU Embeddings.

Features:
- SentenceTransformer('all-MiniLM-L6-v2') local CPU embeddings (dimension: 384).
- Automatic Qdrant collection creation with Cosine distance.
- Robust column detection & combination for JEE question/solution datasets.
- Clean batching with progress tracking and payload serialization.
"""

import os
import sys
import uuid
import time
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ingest_csv")


def clean_metadata_value(val: Any) -> Any:
    """Sanitizes Pandas values to be JSON-serializable for Qdrant payload."""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float, str, bool)):
        return val
    return str(val)


def build_text_representation(row: pd.Series) -> str:
    """
    Combines relevant text columns (e.g. question_text, solution_latex, topic, subject)
    into a structured text string for dense semantic embedding.
    """
    parts = []

    # Subject / Topic / Chapter Context
    for col in ["subject", "Subject", "SUBJECT"]:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            parts.append(f"Subject: {row[col]}")
            break

    for col in ["topic", "Topic", "TOPIC", "chapter", "Chapter"]:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            parts.append(f"Topic: {row[col]}")
            break

    for col in ["difficulty", "Difficulty", "tier", "Tier", "exam_type"]:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            parts.append(f"Exam Level: {row[col]}")
            break

    # Problem Statement / Question
    question_found = False
    for col in ["question_text", "question", "problem", "Question", "Problem", "query", "text"]:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            parts.append(f"Question: {str(row[col]).strip()}")
            question_found = True
            break

    # Options (if MCQ)
    options = []
    for opt_key in ["option_a", "option_b", "option_c", "option_d", "opt_a", "opt_b", "opt_c", "opt_d"]:
        if opt_key in row and pd.notna(row[opt_key]):
            options.append(f"({opt_key[-1].upper()}) {row[opt_key]}")
    if options:
        parts.append("Options:\n" + "\n".join(options))

    # Solution / Mathematical Derivation
    solution_found = False
    for col in ["solution_latex", "solution", "explanation", "Solution", "Explanation", "proof", "master_solution"]:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            parts.append(f"Solution & Derivation:\n{str(row[col]).strip()}")
            solution_found = True
            break

    # Fallback: If standard columns are not detected, concatenate all non-empty fields
    if not (question_found or solution_found):
        for col_name, val in row.items():
            if pd.notna(val) and str(val).strip():
                parts.append(f"{col_name}: {str(val).strip()}")

    return "\n\n".join(parts)


def ensure_collection(client: QdrantClient, collection_name: str, vector_size: int = 384, recreate: bool = False):
    """Checks if the Qdrant collection exists; creates or recreates it with Cosine metric."""
    try:
        collections = client.get_collections().collections
        existing_names = [c.name for c in collections]
    except Exception as e:
        logger.warning("Could not fetch collections list via API (%s). Attempting direct check...", e)
        existing_names = []

    if collection_name in existing_names:
        if recreate:
            logger.info("Recreate flag enabled. Deleting existing collection '%s'...", collection_name)
            client.delete_collection(collection_name=collection_name)
            logger.info("Creating fresh collection '%s' (vector size: %d, distance: Cosine)...", collection_name, vector_size)
            client.create_collection(
                collection_name=collection_name,
                vectors_config=qmodels.VectorParams(
                    size=vector_size,
                    distance=qmodels.Distance.COSINE,
                ),
            )
        else:
            logger.info("Collection '%s' already exists. Appending vectors...", collection_name)
    else:
        logger.info("Collection '%s' not found. Creating new collection (size: %d, distance: Cosine)...", collection_name, vector_size)
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(
                size=vector_size,
                distance=qmodels.Distance.COSINE,
            ),
        )


def ingest_csv(
    file_path: str,
    collection_name: str = "jee_knowledge_base",
    batch_size: int = 64,
    qdrant_url: str = "http://localhost:6333",
    qdrant_path: str = None,
    recreate: bool = False,
):
    """
    Main ingestion pipeline for bulk embedding and storing JEE CSV rows into Qdrant.
    """
    start_time = time.time()
    csv_file = Path(file_path).resolve()
    if not csv_file.exists():
        logger.error("CSV file not found at: %s", csv_file)
        sys.exit(1)

    logger.info("Loading CSV dataset from: %s", csv_file)
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        logger.error("Failed to read CSV: %s", e)
        sys.exit(1)

    total_rows = len(df)
    logger.info("Loaded %d rows with columns: %s", total_rows, list(df.columns))

    # 1. Initialize FastEmbed model on CPU
    logger.info("Initializing FastEmbedEmbeddings('BAAI/bge-small-en-v1.5') on local CPU...")
    model = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    vector_size = 384
    logger.info("Embedding model loaded successfully (Vector Dimension: %d).", vector_size)

    # 2. Connect to Qdrant
    if qdrant_path:
        logger.info("Connecting to embedded local Qdrant at directory: %s", qdrant_path)
        client = QdrantClient(path=qdrant_path)
    else:
        qdrant_api_key = os.getenv("QDRANT_API_KEY", None)
        logger.info("Connecting to Qdrant server at: %s", qdrant_url)
        try:
            client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=30.0)
        except Exception:
            fallback_dir = Path(__file__).resolve().parent.parent / "qdrant_db"
            logger.warning("Could not connect to Qdrant URL. Falling back to local storage at %s", fallback_dir)
            client = QdrantClient(path=str(fallback_dir))

    # 3. Ensure collection exists
    ensure_collection(client, collection_name, vector_size=vector_size, recreate=recreate)

    # 4. Process and embed in batches
    logger.info("Starting batch processing (Batch size: %d, Total items: %d)...", batch_size, total_rows)
    total_upserted = 0

    for i in range(0, total_rows, batch_size):
        batch_df = df.iloc[i : i + batch_size]
        batch_texts = []
        batch_payloads = []
        batch_ids = []

        for idx, row in batch_df.iterrows():
            text_repr = build_text_representation(row)
            batch_texts.append(text_repr)

            # Metadata payload
            payload = {
                str(k): clean_metadata_value(v)
                for k, v in row.to_dict().items()
            }
            payload["combined_text"] = text_repr
            payload["source_file"] = csv_file.name
            payload["row_index"] = int(idx)
            batch_payloads.append(payload)

            # Unique deterministic Point ID via UUID5 namespace hashing
            row_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, text_repr))
            batch_ids.append(row_id)

        # Generate dense FastEmbed embeddings
        embeddings = model.embed_documents(batch_texts)

        # Build Qdrant points
        points = [
            qmodels.PointStruct(
                id=batch_ids[j],
                vector=embeddings[j],
                payload=batch_payloads[j],
            )
            for j in range(len(batch_texts))
        ]

        # Upsert into Qdrant
        client.upsert(
            collection_name=collection_name,
            points=points,
        )

        total_upserted += len(points)
        progress_pct = (total_upserted / total_rows) * 100
        elapsed = time.time() - start_time
        speed = total_upserted / elapsed if elapsed > 0 else 0
        logger.info(
            "Progress: [%d/%d] (%.1f%%) | Upserted batch %d-%d | Speed: %.1f items/sec",
            total_upserted,
            total_rows,
            progress_pct,
            i + 1,
            min(i + batch_size, total_rows),
            speed,
        )

    total_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info("Successfully ingested %d points into Qdrant collection '%s' in %.2f seconds.", total_upserted, collection_name, total_time)
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Bulk ingest JEE question & formula CSV datasets into Qdrant with local CPU MiniLM embeddings."
    )
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        required=True,
        help="Path to the input CSV file containing JEE questions, formulas, or concepts.",
    )
    parser.add_argument(
        "--collection",
        "-c",
        type=str,
        default="jee_knowledge_base",
        help="Name of the target Qdrant collection (default: 'jee_knowledge_base').",
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=64,
        help="Batch size for embedding generation and Qdrant upserts (default: 64).",
    )
    parser.add_argument(
        "--qdrant-url",
        type=str,
        default=os.getenv("QDRANT_URL", "http://localhost:6333"),
        help="URL of the running Qdrant instance (default: 'http://localhost:6333').",
    )
    parser.add_argument(
        "--qdrant-path",
        type=str,
        default=None,
        help="Optional local path for embedded Qdrant storage.",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="If set, drops and recreates the collection before ingestion.",
    )

    args = parser.parse_args()
    ingest_csv(
        file_path=args.file,
        collection_name=args.collection,
        batch_size=args.batch_size,
        qdrant_url=args.qdrant_url,
        qdrant_path=args.qdrant_path,
        recreate=args.recreate,
    )


if __name__ == "__main__":
    main()
