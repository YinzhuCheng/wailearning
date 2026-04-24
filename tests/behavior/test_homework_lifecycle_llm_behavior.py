"""
H1–H3: Homework lifecycle interleaved with LLM grading queue.

Execution deferred — see tests/behavior/conftest.py.
"""


def test_h1_disable_auto_grading_with_queued_tasks() -> None:
    """
    H1: Turn off homework.auto_grading_enabled while tasks queued → tasks fail or skip per product rule.
    """


def test_h2_delete_homework_or_regrade_creates_clean_task_graph() -> None:
    """
    H2: Delete homework with queued tasks (cleanup); teacher regrade creates new task; usage logs linkage.
    """


def test_h3_multiple_attempts_accumulate_student_daily_pool() -> None:
    """
    H3: Same student multiple attempts → multiple tasks; usage sums against one student daily pool;
    UI shows latest attempt status.
    """
