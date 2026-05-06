"""Direct-call dashboard stats against configured DATABASE_URL (no HTTP).

Run from repository root so `app` resolves:

    cd <REPO_ROOT>
    python3 scripts/dev_smoke/manual_dashboard_direct_db.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.database import get_db
from app.models import Student, User
from app.routers.classes import get_accessible_class_ids
from app.routers.dashboard import get_dashboard_stats


def main() -> None:
    db = next(get_db())
    try:
        test_user = db.query(User).filter(User.username == "admin").first()
        if not test_user:
            print("未找到 admin 用户")
            sys.exit(1)

        print(f"测试用户: {test_user.username}, 角色: {test_user.role}")

        class_ids = get_accessible_class_ids(test_user, db)
        print(f"可访问的班级ID: {class_ids}")

        if class_ids:
            students_count = db.query(Student).filter(Student.class_id.in_(class_ids)).count()
            print(f"学生总数: {students_count}")
        else:
            print("警告: 没有可访问的班级")

        try:
            result = get_dashboard_stats(semester="", db=db, current_user=test_user)
            print(f"Dashboard API 调用成功: {result.total_students} 学生")
        except Exception as e:
            print(f"Dashboard API 调用失败: {e}")
            import traceback

            traceback.print_exc()

    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
