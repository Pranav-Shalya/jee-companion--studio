import os
import sys
from pathlib import Path

# Add backend root to sys.path
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.analytics_engine import (
    init_analytics_db,
    calculate_memory_strength,
    calculate_retention,
    log_test_event,
    get_student_dashboard,
    analytics_engine_service,
)

def run_tests():
    test_db = str(BACKEND_ROOT / "data" / "test_analytics.db")
    if os.path.exists(test_db):
        os.remove(test_db)

    print(f"Connecting to test db: {test_db}")
    conn = init_analytics_db(test_db)
    print("DB initialized successfully.")

    # 1. Math Functions
    s = calculate_memory_strength(85.0, 1.2, 2)
    print(f"Memory Strength (85.0, 1.2, 2): {s}")
    assert s == (85.0 * 1.2 + 0.5 * 2)

    s_min = calculate_memory_strength(0.0, 0.0, 0)
    print(f"Min Memory Strength: {s_min}")
    assert s_min == 0.1

    r0 = calculate_retention(s, 0)
    print(f"Retention at t=0: {r0}")
    assert r0 == 1.0

    # R at target review date (R = 0.70)
    days_to_r70 = -s * (-0.35667494393873245) # -s * ln(0.70)
    r_target = calculate_retention(s, days_to_r70)
    print(f"Retention at review date: {r_target}")
    assert abs(r_target - 0.70) < 0.001

    # 2. Event Logging
    ev1 = log_test_event("student_001", "Physics", "Rotational Dynamics", 80.0, 1.0, test_db)
    assert ev1["previous_attempts"] == 0
    assert ev1["memory_strength"] == 80.0

    ev2 = log_test_event("student_001", "Physics", "Rotational Dynamics", 90.0, 1.0, test_db)
    assert ev2["previous_attempts"] == 1
    assert ev2["memory_strength"] == 90.5

    ev3 = log_test_event("student_001", "Chemistry", "Chemical Equilibrium", 70.0, 1.0, test_db)
    ev4 = log_test_event("student_001", "Mathematics", "Definite Integrals", 85.0, 1.0, test_db)
    ev5 = log_test_event("student_001", "Mathematics", "Definite Integrals", 95.0, 1.0, test_db)

    # 3. Dashboard Aggregation
    dash = get_student_dashboard("student_001", test_db)
    print("Dashboard Data:")
    print(f" - Total tests: {dash['total_tests_taken']}")
    print(f" - Moving average (last 5): {dash['moving_average']}")
    print(f" - Action queue count: {dash['action_queue_count']}")

    assert dash["total_tests_taken"]["Physics"] == 2
    assert dash["total_tests_taken"]["Chemistry"] == 1
    assert dash["total_tests_taken"]["Mathematics"] == 2
    assert dash["total_tests_taken"]["total"] == 5
    assert dash["moving_average"] == round((80.0 + 90.0 + 70.0 + 85.0 + 95.0) / 5, 2)

    # 4. Service Class Wrapper
    service_dash = analytics_engine_service.get_dashboard("student_001")
    assert service_dash is not None

    conn.close()
    if os.path.exists(test_db):
        os.remove(test_db)

    print("\n[SUCCESS] All Analytics Engine calculations and database interactions verified successfully!")

if __name__ == "__main__":
    run_tests()
