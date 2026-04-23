"""
反思：为何最初那类「能看课 / 不能交作业 / 教师人数为 0」未在行为测试里暴露

1. 测试数据多为「理想全套」：同时造好 User（学生）、同班 Student（学号=用户名）、
   CourseEnrollment 或显式调用 sync，缺少「只满足其中一部分」的状态。
2. 缺少对「运营顺序」的覆盖：例如先建课再在班级里补人、先改用户班级再补花名册等，
   这些才会触发同步是否遗漏的问题。
3. 未把「课程可见性规则」与「作业提交 / 选课表」拆成独立断言：若只断言 HTTP 200
   或列表非空，不会发现两套规则分叉。
4. 未覆盖「用户名与学号不一致」「花名册在别班」「仅有账号无花名册」等边界。
5. 教师端人数、作业提交名单、学生课程列表若分属不同用例文件且各自造数，
   难以发现跨接口不一致。

以下用例描述上述缺口场景；实现与断言交给下一轮（当前全部 skip）。
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.skip(reason="下一轮：实现数据准备与断言，并驱动修复验证")


def test_student_sees_course_only_when_rules_satisfied():
    """学生课程列表与 ensure_course_access / 交作业前提一致，无不一致窗口。"""


def test_homework_submit_after_course_created_then_roster_added():
    """先建课并挂班，后仅通过学生 API 加花名册；提交作业前应自动具备 CourseEnrollment。"""


def test_teacher_student_count_matches_course_enrollment_rows():
    """GET /subjects 的 student_count 与 GET /subjects/{id}/students 条数一致。"""


def test_student_username_mismatch_student_no_cannot_submit():
    """学号与登录用户名不一致时：错误信息可区分且不应静默 500。"""


def test_student_user_class_set_but_no_roster_row():
    """仅有学生账号与 class_id，无 Student 行：课程列表与作业提交行为符合产品约定。"""


def test_duplicate_student_no_across_classes_prepare_does_not_move_roster():
    """同一学号两条花名册不同班：调用户班级不得误迁错误一条。"""


def test_homework_class_id_differs_from_student_roster_class():
    """作业挂在班级 A，花名册在班 B：提交应失败且提示与班级/作业一致。"""


def test_admin_user_class_change_triggers_enrollment_sync_for_student():
    """管理员修改学生用户 class_id 后，选课与花名册/作业仍一致。"""


def test_student_removed_from_course_enrollment_cannot_submit_linked_homework():
    """教师移除选课后，学生不应再能提交该课关联作业（若产品如此约定）。"""


def test_batch_import_students_existing_course_all_get_enrollment():
    """课已存在时批量导入进班：每人生成对应 CourseEnrollment。"""


def test_public_register_student_then_roster_same_username_gets_enrollments():
    """公开注册学生后补同用户名花名册：登录或拉课表后选课完整。"""


def test_get_homework_list_for_student_needs_matching_submissions_map():
    """跨班级作业列表 + 学生提交映射：花名册班级与作业 class_id 组合下行为正确。"""
