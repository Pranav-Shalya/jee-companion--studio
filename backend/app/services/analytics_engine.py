"""
Analytics Engine Service for JEE Test Series
Implements Ebbinghaus Forgetting Curve Spaced Repetition, Memory Strength,
Retention Projections, and Time Series Dashboard Analytics.
"""

import os
import math
import uuid
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default path for the analytics SQLite database
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "analytics.db"


def _get_db_path(custom_path: Optional[str] = None) -> Path:
    if custom_path:
        p = Path(custom_path)
    else:
        p = DEFAULT_DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# 1. Database Setup
# ---------------------------------------------------------------------------
def init_analytics_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Initializes the SQLite analytics database and creates the test_events table
    if it does not exist.
    """
    target_path = _get_db_path(db_path)
    conn = sqlite3.connect(str(target_path))
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS test_events (
            event_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            score_percentage REAL NOT NULL,
            difficulty_multiplier REAL NOT NULL,
            completed_at TIMESTAMP NOT NULL,
            next_review_date TIMESTAMP NOT NULL
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_events_user_topic ON test_events(user_id, topic)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_events_user_review ON test_events(user_id, next_review_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_events_user_completed ON test_events(user_id, completed_at)")

    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# 2. Math Functions (Ebbinghaus Forgetting Curve & Memory Strength)
# ---------------------------------------------------------------------------
def calculate_memory_strength(score: float, difficulty: float, previous_attempts: int) -> float:
    """
    Calculates the memory stability/strength S based on test score, question difficulty,
    and cumulative repetition count.
    
    Formula: (score * difficulty) + (0.5 * previous_attempts)
    Guarantees a minimum return value of 0.1 to avoid division by zero.
    """
    raw_strength = (float(score) * float(difficulty)) + (0.5 * float(previous_attempts))
    return max(0.1, float(raw_strength))


def calculate_retention(memory_strength: float, days_elapsed: float) -> float:
    """
    Calculates the current memory retention probability R(t) using the Ebbinghaus exponential model.
    
    Formula: R = exp(-days_elapsed / memory_strength)
    """
    strength = max(0.1, float(memory_strength))
    days = max(0.0, float(days_elapsed))
    return math.exp(-days / strength)


# ---------------------------------------------------------------------------
# 3. Logging Function
# ---------------------------------------------------------------------------
def log_test_event(
    user_id: str,
    subject: str,
    topic: str,
    score: float,
    difficulty: float = 1.0,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Logs a completed test attempt, calculates memory strength, derives the next review
    date targeting retention threshold R = 0.70, and inserts the record into test_events.
    """
    conn = init_analytics_db(db_path)
    cursor = conn.cursor()

    try:
        # Count previous test attempts for this user and topic
        cursor.execute(
            "SELECT COUNT(*) FROM test_events WHERE user_id = ? AND topic = ?",
            (user_id, topic),
        )
        previous_attempts = cursor.fetchone()[0]

        # Calculate memory strength S
        memory_strength = calculate_memory_strength(score, difficulty, previous_attempts)

        # Solve Ebbinghaus equation for R = 0.70:
        # R = exp(-t / S) => ln(0.70) = -t / S => t = -S * ln(0.70)
        days_until_review = -memory_strength * math.log(0.70)

        # Standardize UTC timestamps
        now_utc = datetime.now(timezone.utc)
        next_review_dt = now_utc + timedelta(days=days_until_review)

        event_id = str(uuid.uuid4())
        completed_at_str = now_utc.isoformat()
        next_review_str = next_review_dt.isoformat()

        cursor.execute(
            """
            INSERT INTO test_events (
                event_id, user_id, subject, topic, score_percentage,
                difficulty_multiplier, completed_at, next_review_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                user_id,
                subject,
                topic,
                float(score),
                float(difficulty),
                completed_at_str,
                next_review_str,
            ),
        )
        conn.commit()

        logger.info(
            f"[ANALYTICS] Logged test event {event_id} for user={user_id}, topic='{topic}', "
            f"score={score}, S={memory_strength:.2f}, next_review in {days_until_review:.2f} days."
        )

        return {
            "event_id": event_id,
            "user_id": user_id,
            "subject": subject,
            "topic": topic,
            "score_percentage": float(score),
            "difficulty_multiplier": float(difficulty),
            "previous_attempts": previous_attempts,
            "memory_strength": round(memory_strength, 4),
            "days_until_review": round(days_until_review, 4),
            "completed_at": completed_at_str,
            "next_review_date": next_review_str,
        }

    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 4. Dashboard Aggregation
# ---------------------------------------------------------------------------
def get_student_dashboard(
    user_id: str, db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Aggregates test performance, momentum moving averages, and the spaced repetition
    action queue for a given student.
    
    Returns:
    - total_tests_taken: Tests count grouped by subject.
    - moving_average: Average score percentage of the last 5 tests.
    - action_queue: Topics where next_review_date <= current time, ordered by most overdue.
    """
    conn = init_analytics_db(db_path)
    cursor = conn.cursor()

    try:
        # 1. Total tests taken grouped by subject
        cursor.execute(
            """
            SELECT subject, COUNT(*) 
            FROM test_events 
            WHERE user_id = ? 
            GROUP BY subject
            """,
            (user_id,),
        )
        subject_counts_raw = cursor.fetchall()
        total_tests_taken = {subj: count for subj, count in subject_counts_raw}
        total_tests_taken["total"] = sum(total_tests_taken.values())

        # 2. Moving average of the last 5 tests overall
        cursor.execute(
            """
            SELECT score_percentage 
            FROM test_events 
            WHERE user_id = ? 
            ORDER BY completed_at DESC 
            LIMIT 5
            """,
            (user_id,),
        )
        recent_scores_rows = cursor.fetchall()
        if recent_scores_rows:
            scores_list = [row[0] for row in recent_scores_rows]
            moving_avg = sum(scores_list) / len(scores_list)
        else:
            moving_avg = 0.0

        # 3. Action queue: topics where next_review_date <= current time, ordered by most overdue
        now_utc = datetime.now(timezone.utc)
        now_utc_str = now_utc.isoformat()

        cursor.execute(
            """
            SELECT 
                event_id, subject, topic, score_percentage, 
                difficulty_multiplier, completed_at, next_review_date
            FROM test_events
            WHERE user_id = ? AND next_review_date <= ?
            ORDER BY next_review_date ASC
            """,
            (user_id, now_utc_str),
        )
        overdue_rows = cursor.fetchall()

        # Deduplicate to most recent overdue event per topic
        seen_topics = set()
        action_queue = []

        for row in overdue_rows:
            e_id, subj, top, sc, diff, comp_at, nxt_rev = row
            if top in seen_topics:
                continue
            seen_topics.add(top)

            # Calculate days overdue and estimated current retention
            try:
                nxt_dt = datetime.fromisoformat(nxt_rev)
                comp_dt = datetime.fromisoformat(comp_at)
                days_since_completed = max(0.0, (now_utc - comp_dt).total_seconds() / 86400.0)
                days_overdue = max(0.0, (now_utc - nxt_dt).total_seconds() / 86400.0)
            except Exception:
                days_since_completed = 0.0
                days_overdue = 0.0

            cursor.execute(
                "SELECT COUNT(*) FROM test_events WHERE user_id = ? AND topic = ?",
                (user_id, top),
            )
            prev_att = cursor.fetchone()[0]
            mem_str = calculate_memory_strength(sc, diff, max(0, prev_att - 1))
            current_retention = calculate_retention(mem_str, days_since_completed)

            action_queue.append({
                "event_id": e_id,
                "subject": subj,
                "topic": top,
                "last_score_percentage": float(sc),
                "difficulty_multiplier": float(diff),
                "completed_at": comp_at,
                "next_review_date": nxt_rev,
                "days_overdue": round(days_overdue, 2),
                "current_retention_estimate": round(current_retention, 4),
            })

        # 4. Topic Mastery Matrix: fetch all test events for the user
        cursor.execute(
            """
            SELECT 
                subject, topic, score_percentage, difficulty_multiplier, completed_at
            FROM test_events
            WHERE user_id = ?
            ORDER BY completed_at DESC
            """,
            (user_id,),
        )
        all_user_events = cursor.fetchall()

        # Group by topic (preserving most recent event data)
        topic_groups = {}
        for row in all_user_events:
            subj, top, sc, diff, comp_at = row
            if top not in topic_groups:
                topic_groups[top] = {
                    "subject": subj,
                    "topic": top,
                    "scores": [],
                    "most_recent_score": sc,
                    "most_recent_diff": diff,
                    "most_recent_completed_at": comp_at,
                    "total_tests": 0,
                }
            topic_groups[top]["scores"].append(sc)
            topic_groups[top]["total_tests"] += 1

        mastery_matrix = []
        for top, data in topic_groups.items():
            total_tests = data["total_tests"]
            last_score_raw = data["most_recent_score"]
            last_score_norm = last_score_raw / 100.0 if last_score_raw > 1.0 else last_score_raw
            
            diff = data["most_recent_diff"]
            comp_at_str = data["most_recent_completed_at"]

            # Calculate days elapsed since most recent test
            try:
                comp_dt = datetime.fromisoformat(comp_at_str)
                days_elapsed = max(0.0, (now_utc - comp_dt).total_seconds() / 86400.0)
            except Exception:
                days_elapsed = 0.0

            # Calculate memory strength S based on (score * diff) + (0.5 * previous_attempts)
            mem_strength = calculate_memory_strength(last_score_norm, diff, max(0, total_tests - 1))
            current_ret = calculate_retention(mem_strength, days_elapsed)

            # Determine status string
            if current_ret < 0.60:
                status_str = "Critical"
            elif current_ret < 0.80:
                status_str = "Decaying"
            else:
                status_str = "Mastered"

            mastery_matrix.append({
                "topic": top,
                "subject": data["subject"],
                "total_tests": total_tests,
                "last_score": round(float(last_score_norm), 4),
                "last_score_percentage": round(float(last_score_raw), 2),
                "current_retention": round(float(current_ret), 4),
                "memory_strength": round(float(mem_strength), 4),
                "days_elapsed": round(float(days_elapsed), 2),
                "status": status_str,
            })

        # Sort mastery matrix by retention ascending (critical first)
        mastery_matrix.sort(key=lambda x: x["current_retention"])

        return {
            "user_id": user_id,
            "total_tests_taken": total_tests_taken,
            "moving_average": round(float(moving_avg), 2),
            "recent_scores_sample": [round(float(s), 2) for s in (scores_list if recent_scores_rows else [])],
            "action_queue": action_queue,
            "action_queue_count": len(action_queue),
            "mastery_matrix": mastery_matrix,
            "generated_at": now_utc_str,
        }

    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 5. Service Class Wrapper
# ---------------------------------------------------------------------------
class AnalyticsEngineService:
    """Service wrapper for Forgetting Curve & Spaced Repetition calculations."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def init_db(self) -> sqlite3.Connection:
        return init_analytics_db(self.db_path)

    def calculate_memory_strength(self, score: float, difficulty: float, previous_attempts: int) -> float:
        return calculate_memory_strength(score, difficulty, previous_attempts)

    def calculate_retention(self, memory_strength: float, days_elapsed: float) -> float:
        return calculate_retention(memory_strength, days_elapsed)

    def log_event(
        self,
        user_id: str,
        subject: str,
        topic: str,
        score: float,
        difficulty: float = 1.0,
    ) -> Dict[str, Any]:
        return log_test_event(user_id, subject, topic, score, difficulty, self.db_path)

    def get_dashboard(self, user_id: str) -> Dict[str, Any]:
        return get_student_dashboard(user_id, self.db_path)


analytics_engine_service = AnalyticsEngineService()
