"""
行为测试（占位）：后端能力与管理端 UI / 端到端路径对齐。

反思（为何未优先做基于 UI 的测试）：
1. 自动化栈以 API + 数据库断言为主，成本低、稳定性高，易忽略「路由 meta、按钮显隐」等纯前端分叉。
2. 同一后端路由可能被多个页面或 axios 实例调用，仅测 200 无法发现「另一页仍用错响应结构」。
3. Playwright 等 E2E 未纳入默认 CI 时，「教师能否看到导入按钮」类问题只能在人工验收或代码审查中发现。

以下用例描述「用户可见路径」与 OpenAPI 契约应对齐；实现与修复留待下轮（当前全部 skip）。
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.skip(reason="UI parity / E2E: implement in next iteration")


def test_teacher_students_page_shows_batch_import_and_template_download():
    """任课教师在学生页应能下载模板并触发批量导入（与 POST /students/batch 一致）。"""


def test_class_teacher_students_page_batch_import_defaults_class_when_class_column_empty():
    """班主任批量导入时「所属班级」列可省略，默认落入当前绑定班级。"""


def test_teacher_can_open_student_create_route_without_admin_only_meta():
    """教师访问 /students/new 应进入表单而非被路由重定向到 dashboard。"""


def test_teacher_student_edit_form_does_not_send_class_id_when_not_admin():
    """非管理员编辑学生时提交体不应包含 class_id（避免误触调班）。"""


def test_subjects_page_teacher_has_sync_enrollments_button():
    """课程列表（教师/管理员）应有「同步选课」并调用 POST /subjects/{id}/sync-enrollments。"""


def test_semesters_page_admin_has_init_defaults_button():
    """学期管理页应有「初始化学期」并调用 POST /semesters/init。"""


def test_points_page_loads_stats_and_ranking_with_unwrapped_json():
    """积分页应用统一 http 客户端，统计与排行数据应渲染非空（非 res.data 二次包装）。"""


def test_points_display_page_loads_stats_and_ranking():
    """积分大屏应正确请求 /points/stats 与 /points/ranking。"""


def test_teacher_points_exchange_and_manual_add_use_correct_response_shape():
    """教师积分发放、兑换、完成兑换列表应与后端响应结构一致。"""


def test_student_batch_import_payload_supports_class_id_per_row_for_teacher():
    """教师批量导入解析结果应可对每行发送 class_id（与所选课程班级一致时）。"""


def test_admin_logs_detail_route_or_drawer_calls_get_log_by_id():
    """操作日志若支持详情，应调用 GET /logs/{id}（若产品不要求则可删此用例）。"""


def test_settings_single_key_put_exposed_when_batch_insufficient():
    """若需单键更新系统设置，管理端应暴露或合并至现有设置页（PUT /settings/{key}）。"""
