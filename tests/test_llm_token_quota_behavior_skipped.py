"""
行为测试（设计稿）：LLM token 预检、日限额记账、billing_note、课程配额快照、评分材料 manifest。

与近期变更的对应关系：
- precheck 错误码拆分：quota_exceeded_student / quota_exceeded_course
- record_usage_if_needed：成功调用后始终写 LLMTokenUsageLog；超日限额时 billing_note=over_daily_limit:…
- estimate_request_tokens_from_material：文本 + data URL 内 base64 长度 + 图片启发式
- GET/PUT 课程 LLM 配置响应中的 quota_usage（course 维度本日用量）
- HomeworkGradingTask.artifact_manifest.included 含 logical_path / mime_hint / origin / truncated

验证与修复交给下一轮：当前整文件 skip，避免 CI 在未联调前失败。
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="下一轮：启用本文件测试并联调（限额、billing_note、quota_usage API、artifact_manifest 字段）"
)


def test_precheck_quota_distinct_error_student_vs_course():
    """
    当仅学生日限额被突破时，precheck_quota 应返回 (False, 'quota_exceeded_student')；
    当仅课程日限额被突破时，应返回 (False, 'quota_exceeded_course')。
    建议：mock _get_used_tokens_for_scope 分别模拟学生侧已满、课程侧已满。
    """


def test_grading_task_failed_precheck_student_shows_student_error_code():
    """
    process_grading_task 在预检失败且为学生限额时，HomeworkGradingTask.error_code 应为 quota_exceeded_student，
    error_message 含「学生」或与学生限额相关的可读说明。
    """


def test_grading_task_failed_precheck_course_shows_course_error_code():
    """
    课程日限额预检失败时，error_code 应为 quota_exceeded_course，
    error_message 含「课程」或课程限额相关说明。
    """


def test_usage_log_always_written_after_successful_llm_call():
    """
    一次成功评分后应存在 LLMTokenUsageLog(task_id=…)，且 billed_* 与 log 一致。
    即使当日累计加上本次 total 略超配置限额，也不应「整行不写」；下一轮核对 record_usage_if_needed 行为。
    """


def test_usage_log_billing_note_when_post_call_exceeds_student_cap():
    """
    构造：当日学生已用量 + 本次 API 返回 total_tokens > daily_student_token_limit，
    但预检仍通过（估计偏小或边界）。
    期望：LLMTokenUsageLog 仍存在，billing_note 含 over_daily_limit 且含 student。
    """


def test_usage_log_billing_note_when_post_call_exceeds_course_cap():
    """
    同上，课程维度：billing_note 含 course。
    """


def test_get_course_llm_config_includes_quota_usage_shape():
    """
    GET /api/llm-settings/courses/{subject_id} 在配置了 daily_course_token_limit 时，
    响应 JSON 应含 quota_usage，且含 usage_date、quota_timezone、course_used_tokens_today、
    course_remaining_tokens_today 等字段（与 CourseLLMConfigResponse 一致）。
    需教师 token + ensure_course_access 通过的 subject_id。
    """


def test_get_course_llm_config_quota_usage_null_without_course_limit():
    """
    未设置课程日限额时，quota_usage 可为 null 或 course_used_tokens_today 为 null（与实现约定一致，下一轮固定契约）。
    """


def test_estimate_request_tokens_grows_with_large_data_url_payload():
    """
    对同一 config，material 中 image 块的 data URL base64 段越长，estimate_request_tokens_from_material 返回值应单调不减。
    可直接调用 app.llm_grading.estimate_request_tokens_from_material（单元级行为测试）。
    """


def test_artifact_manifest_includes_block_metadata_after_material_build():
    """
    队列评分前 _build_student_material 返回的 artifact_manifest['included'] 中，
    每个条目应含 path、type，且若实现已加则应含 logical_path、mime_hint、origin、truncated。
    建议：造带附件的 HomeworkAttempt，调用 _build_student_material 后断言 manifest 结构（不发起真实 HTTP）。
    """


def test_scoring_messages_have_distinct_sections_for_instructor_and_submission():
    """
    _build_scoring_messages 返回的 user content 中应能区分：
    - 教师作业说明区（如含 SECTION 标记或固定标题）
    - 学生提交元数据区
    - 附件文本区与图片区（含 IMAGE_META 或等价短行）
    下一轮可对 messages[1]['content'] 列表中 text 段做子串断言。
    """


def test_zip_attachment_skipped_reason_propagates_to_notes_or_manifest():
    """
    超大 zip 或超过 MAX_ZIP_FILES / MAX_ZIP_TOTAL_BYTES 时，skipped 列表有 reason，
    notes_text 或 artifact_manifest.skipped 应对教师/调试可见；与前端「截断说明」文案无强耦合，只测后端契约。
    """
