from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UserRole(str, Enum):
    ADMIN = "admin"
    CLASS_TEACHER = "class_teacher"
    TEACHER = "teacher"
    STUDENT = "student"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    LEAVE = "leave"


class UserBase(BaseModel):
    username: str
    real_name: str
    role: str = UserRole.TEACHER.value
    class_id: Optional[int] = None

    @field_validator("role", mode="before")
    @classmethod
    def convert_role(cls, value):
        if isinstance(value, UserRole):
            return value.value
        return value


class UserCreate(UserBase):
    password: str

    @model_validator(mode="after")
    def _require_class_for_students(self):
        r = (self.role or "").strip()
        if r in (UserRole.STUDENT.value,):
            if self.class_id is None:
                raise ValueError("class_id is required for student accounts.")
        return self


class UserUpdate(BaseModel):
    username: Optional[str] = None
    real_name: Optional[str] = None
    role: Optional[str] = None
    class_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    class_id: Optional[int] = None

    class Config:
        from_attributes = True


class StudentUserBatchCreateRequest(BaseModel):
    student_ids: List[int]


class StudentUserBatchCreateError(BaseModel):
    student_id: Optional[int] = None
    student_name: Optional[str] = None
    student_no: Optional[str] = None
    reason: str


class StudentUserBatchCreateResponse(BaseModel):
    total: int
    success: int
    failed: int
    created_users: List[str]
    errors: List[StudentUserBatchCreateError]


class StudentRosterUpsertFromUsersRequest(BaseModel):
    user_ids: List[int]


class StudentRosterUpsertFromUsersError(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    reason: str


class StudentRosterUpsertFromUsersResponse(BaseModel):
    total: int
    created: int
    updated: int
    skipped: int
    errors: List[StudentRosterUpsertFromUsersError]


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class MessageResponse(BaseModel):
    message: str


class AttachmentUploadResponse(BaseModel):
    attachment_name: str
    attachment_url: str
    content_type: Optional[str] = None
    size: int


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        encoded = value.encode("utf-8")
        if len(encoded) < 8:
            raise ValueError("New password must be at least 8 characters.")
        if len(encoded) > 72:
            raise ValueError("New password must be 72 bytes or fewer.")
        return value

    @model_validator(mode="after")
    def validate_password_confirmation(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Password confirmation does not match.")
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from current password.")
        return self


class ClassCreate(BaseModel):
    name: str
    grade: int


class ClassUpdate(BaseModel):
    name: Optional[str] = None
    grade: Optional[int] = None


class ClassResponse(BaseModel):
    id: int
    name: str
    grade: int
    created_at: datetime
    student_count: int = 0

    class Config:
        from_attributes = True


class StudentBase(BaseModel):
    name: str
    student_no: str
    gender: Gender
    phone: Optional[str] = None
    parent_phone: Optional[str] = None
    address: Optional[str] = None
    class_id: int


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    student_no: Optional[str] = None
    gender: Optional[Gender] = None
    phone: Optional[str] = None
    parent_phone: Optional[str] = None
    address: Optional[str] = None
    class_id: Optional[int] = None


class StudentResponse(StudentBase):
    id: int
    teacher_id: Optional[int] = None
    created_at: datetime
    class_name: Optional[str] = None
    parent_code: Optional[str] = None
    has_user: bool = False

    class Config:
        from_attributes = True


class StudentListResponse(BaseModel):
    total: int
    data: List[StudentResponse]


class CourseTimeItem(BaseModel):
    weekly_schedule: str
    course_start_at: datetime
    course_end_at: datetime

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.course_end_at < self.course_start_at:
            raise ValueError("Course end time must be later than start time.")
        return self


class SubjectCreate(BaseModel):
    name: str
    teacher_id: Optional[int] = None
    class_id: Optional[int] = None
    class_name: Optional[str] = None
    semester_id: Optional[int] = None
    course_type: str = "required"
    status: str = "active"
    semester: Optional[str] = None
    weekly_schedule: Optional[str] = None
    course_start_at: Optional[datetime] = None
    course_end_at: Optional[datetime] = None
    course_times: Optional[List[CourseTimeItem]] = None
    description: Optional[str] = None
    students: Optional[List["CourseRosterStudentInput"]] = None


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    teacher_id: Optional[int] = None
    class_id: Optional[int] = None
    semester_id: Optional[int] = None
    course_type: Optional[str] = None
    status: Optional[str] = None
    semester: Optional[str] = None
    weekly_schedule: Optional[str] = None
    course_start_at: Optional[datetime] = None
    course_end_at: Optional[datetime] = None
    course_times: Optional[List[CourseTimeItem]] = None
    description: Optional[str] = None


class SubjectResponse(BaseModel):
    id: int
    name: str
    teacher_id: Optional[int] = None
    class_id: Optional[int] = None
    semester_id: Optional[int] = None
    course_type: str = "required"
    status: str = "active"
    semester: Optional[str] = None
    weekly_schedule: Optional[str] = None
    course_start_at: Optional[datetime] = None
    course_end_at: Optional[datetime] = None
    course_times: List[CourseTimeItem] = Field(default_factory=list)
    description: Optional[str] = None
    teacher_name: Optional[str] = None
    class_name: Optional[str] = None
    student_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class CourseEnrollmentResponse(BaseModel):
    id: int
    subject_id: int
    student_id: int
    class_id: int
    enrollment_type: str = "required"
    can_remove: bool
    created_at: datetime
    student_name: Optional[str] = None
    student_no: Optional[str] = None
    class_name: Optional[str] = None

    class Config:
        from_attributes = True


class CourseRosterStudentInput(BaseModel):
    name: str
    student_no: str
    gender: Optional[Gender] = None
    enrollment_type: Optional[str] = None
    phone: Optional[str] = None
    parent_phone: Optional[str] = None
    address: Optional[str] = None


class CourseEnrollmentTypeUpdate(BaseModel):
    enrollment_type: str


class SubjectRosterEnrollRequest(BaseModel):
    """Add enrollments only for students already on the course class roster (same class_id)."""

    student_ids: List[int] = Field(default_factory=list)


class SubjectRosterEnrollResult(BaseModel):
    created: int = 0
    skipped_already_enrolled: int = 0
    skipped_not_in_class_roster: int = 0
    skipped_not_found: int = 0


class StudentElectiveSelfEnrollResult(BaseModel):
    """Student voluntarily joined an elective course."""

    subject_id: int
    created: bool = False
    already_enrolled: bool = False


class StudentElectiveSelfDropResult(BaseModel):
    subject_id: int
    removed: bool = False


class StudentLLMQuotaUsageResponse(BaseModel):
    subject_id: int
    usage_date: str
    quota_timezone: str
    """Effective per-student daily cap (all courses share one pool under quota_timezone)."""
    daily_student_token_limit: Optional[int] = None
    global_default_daily_student_tokens: Optional[int] = None
    uses_personal_override: bool = False
    student_used_tokens_today: Optional[int] = None
    student_remaining_tokens_today: Optional[int] = None


class LLMGlobalQuotaPolicyResponse(BaseModel):
    id: int
    default_daily_student_tokens: int
    quota_timezone: str
    max_parallel_grading_tasks: int = 3


class LLMGlobalQuotaPolicyUpdate(BaseModel):
    default_daily_student_tokens: Optional[int] = Field(default=None, ge=1)
    quota_timezone: Optional[str] = None
    max_parallel_grading_tasks: Optional[int] = Field(default=None, ge=1, le=64)


class LLMQuotaBulkOverrideRequest(BaseModel):
    """Apply the same per-student daily cap to everyone in scope (or clear overrides)."""

    scope: str = Field(..., description="one of: all, class, subject")
    class_id: Optional[int] = None
    subject_id: Optional[int] = None
    daily_tokens: Optional[int] = Field(default=None, ge=1)
    clear_override: bool = False

    @model_validator(mode="after")
    def _validate_scope(self) -> "LLMQuotaBulkOverrideRequest":
        s = (self.scope or "").strip().lower()
        if s not in {"all", "class", "subject"}:
            raise ValueError("scope must be all, class, or subject")
        object.__setattr__(self, "scope", s)
        if s == "class" and not self.class_id:
            raise ValueError("class_id is required when scope is class")
        if s == "subject" and not self.subject_id:
            raise ValueError("subject_id is required when scope is subject")
        if not self.clear_override and self.daily_tokens is None:
            raise ValueError("daily_tokens is required unless clear_override is true")
        if self.clear_override and self.daily_tokens is not None:
            raise ValueError("clear_override cannot be combined with daily_tokens")
        return self


class LLMQuotaBulkOverrideResponse(BaseModel):
    affected_students: int
    default_daily_student_tokens: Optional[int] = None


class LLMStudentQuotaOverrideUpsert(BaseModel):
    daily_tokens: Optional[int] = Field(default=None, ge=1)
    clear_override: bool = False

    @model_validator(mode="after")
    def _xor(self) -> "LLMStudentQuotaOverrideUpsert":
        if self.clear_override and self.daily_tokens is not None:
            raise ValueError("clear_override cannot be combined with daily_tokens")
        if not self.clear_override and self.daily_tokens is None:
            raise ValueError("Provide daily_tokens or set clear_override to true")
        return self


class UserBatchSetClassRequest(BaseModel):
    user_ids: List[int] = Field(default_factory=list)
    class_id: int


class UserBatchSetClassError(BaseModel):
    user_id: int
    reason: str


class UserBatchSetClassResponse(BaseModel):
    updated: int = 0
    errors: List[UserBatchSetClassError] = Field(default_factory=list)


SubjectCreate.model_rebuild()


class SemesterCreate(BaseModel):
    name: str
    year: int
    is_current: bool = False


class SemesterUpdate(BaseModel):
    name: Optional[str] = None
    year: Optional[int] = None
    is_current: Optional[bool] = None


class SemesterResponse(BaseModel):
    id: int
    name: str
    year: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ScoreBase(BaseModel):
    student_id: int
    subject_id: int
    class_id: int
    semester: str
    exam_type: str
    score: float
    exam_date: Optional[str] = None


class ScoreCreate(ScoreBase):
    pass


class ScoreUpdate(BaseModel):
    score: Optional[float] = None
    exam_type: Optional[str] = None
    exam_date: Optional[str] = None
    semester: Optional[str] = None


class ScoreResponse(ScoreBase):
    id: int
    student_name: Optional[str] = None
    subject_name: Optional[str] = None
    class_name: Optional[str] = None
    exam_date: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScoreListResponse(BaseModel):
    total: int
    data: List[ScoreResponse]


class CourseExamWeightItem(BaseModel):
    exam_type: str
    weight: float


class CourseExamWeightResponse(CourseExamWeightItem):
    id: int
    subject_id: int

    class Config:
        from_attributes = True


class CourseExamWeightUpdateRequest(BaseModel):
    items: List[CourseExamWeightItem]


class AttendanceBase(BaseModel):
    student_id: int
    class_id: int
    subject_id: Optional[int] = None
    date: str
    status: AttendanceStatus
    remark: Optional[str] = None


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceUpdate(BaseModel):
    status: Optional[AttendanceStatus] = None
    remark: Optional[str] = None


class AttendanceResponse(AttendanceBase):
    id: int
    student_name: Optional[str] = None
    class_name: Optional[str] = None
    subject_name: Optional[str] = None
    date: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AttendanceListResponse(BaseModel):
    total: int
    data: List[AttendanceResponse]


class ClassRanking(BaseModel):
    class_id: int
    class_name: str
    avg_score: float
    rank: int


class DashboardStats(BaseModel):
    total_students: int
    total_classes: int
    total_scores: int = 0
    avg_score: float
    attendance_rate: float = 0.0
    recent_scores: List[ScoreResponse] = []
    class_rankings: List[ClassRanking] = []


class StudentRanking(BaseModel):
    student_id: int
    student_name: str
    class_name: str
    avg_score: float
    rank: int


class OperationLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    action: str
    target_type: str
    target_id: Optional[int] = None
    target_name: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    result: str
    created_at: datetime

    class Config:
        from_attributes = True


class OperationLogListResponse(BaseModel):
    total: int
    data: List[OperationLogResponse]


class PointRuleBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    points: int
    condition_type: str
    condition_value: Optional[str] = None


class PointRuleCreate(PointRuleBase):
    pass


class PointRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    points: Optional[int] = None
    condition_type: Optional[str] = None
    condition_value: Optional[str] = None
    is_active: Optional[bool] = None


class PointRuleResponse(PointRuleBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class StudentPointResponse(BaseModel):
    id: int
    student_id: int
    total_points: int
    available_points: int
    total_earned: int
    total_spent: int
    student_name: Optional[str] = None
    class_name: Optional[str] = None

    class Config:
        from_attributes = True


class PointRecordResponse(BaseModel):
    id: int
    student_id: int
    rule_id: Optional[int] = None
    points: int
    balance_after: int
    source_type: str
    source_id: Optional[int] = None
    description: Optional[str] = None
    operator_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PointRecordListResponse(BaseModel):
    total: int
    data: List[PointRecordResponse]


class PointItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    item_type: str
    points_cost: int
    stock: int = -1
    image_url: Optional[str] = None


class PointItemCreate(PointItemBase):
    pass


class PointItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    item_type: Optional[str] = None
    points_cost: Optional[int] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class PointItemResponse(PointItemBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PointExchangeResponse(BaseModel):
    id: int
    student_id: int
    item_id: int
    points_spent: int
    quantity: int
    status: str
    exchange_time: datetime
    pickup_time: Optional[datetime] = None
    operator_name: Optional[str] = None
    remark: Optional[str] = None
    student_name: Optional[str] = None
    item_name: Optional[str] = None

    class Config:
        from_attributes = True


class PointExchangeListResponse(BaseModel):
    total: int
    data: List[PointExchangeResponse]


class PointAddRequest(BaseModel):
    student_id: int
    points: int
    description: str
    source_type: str = "manual"
    source_id: Optional[int] = None
    rule_id: Optional[int] = None


class PointExchangeRequest(BaseModel):
    item_id: int
    quantity: int = 1
    student_id: Optional[int] = None


class PointRankingResponse(BaseModel):
    student_id: int
    student_name: str
    class_name: str
    total_points: int
    rank: int


class PointStatsResponse(BaseModel):
    total_students: int
    active_students: int
    total_points_distributed: int
    total_points_exchanged: int
    top_students: List[PointRankingResponse]


class SystemSettingResponse(BaseModel):
    id: int
    setting_key: str
    setting_value: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SystemSettingUpdate(BaseModel):
    setting_value: str


class SystemSettingsResponse(BaseModel):
    system_name: str
    login_background: str
    system_logo: str
    system_intro: str
    copyright: str
    use_bing_background: bool


class HomeworkBase(BaseModel):
    title: str
    content: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None
    class_id: int
    subject_id: Optional[int] = None
    due_date: Optional[datetime] = None
    max_score: float = Field(default=100, gt=0)
    grade_precision: str = "integer"
    auto_grading_enabled: bool = False
    rubric_text: Optional[str] = None
    reference_answer: Optional[str] = None
    response_language: Optional[str] = None
    allow_late_submission: bool = True
    late_submission_affects_score: bool = False
    max_submissions: Optional[int] = Field(
        default=None,
        description="Maximum submission attempts per student; null means unlimited.",
    )
    llm_routing_spec: Optional[dict[str, Any]] = Field(
        default=None,
        description="Per-homework LLM routing override: mode limit_to_preset_ids or latest_passing_validated.",
    )

    @field_validator("max_submissions")
    @classmethod
    def validate_max_submissions(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        if int(value) < 1:
            raise ValueError("max_submissions must be at least 1 when set.")
        if int(value) > 200:
            raise ValueError("max_submissions cannot exceed 200.")
        return int(value)

    @field_validator("grade_precision")
    @classmethod
    def validate_grade_precision(cls, value: str) -> str:
        normalized = (value or "integer").strip()
        if normalized not in {"integer", "decimal_1"}:
            raise ValueError("grade_precision must be integer or decimal_1.")
        return normalized


class HomeworkCreate(HomeworkBase):
    pass


class HomeworkUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None
    remove_attachment: bool = False
    subject_id: Optional[int] = None
    due_date: Optional[datetime] = None
    max_score: Optional[float] = Field(default=None, gt=0)
    grade_precision: Optional[str] = None
    auto_grading_enabled: Optional[bool] = None
    rubric_text: Optional[str] = None
    reference_answer: Optional[str] = None
    response_language: Optional[str] = None
    allow_late_submission: Optional[bool] = None
    late_submission_affects_score: Optional[bool] = None
    max_submissions: Optional[int] = None
    llm_routing_spec: Optional[dict[str, Any]] = None

    @field_validator("max_submissions")
    @classmethod
    def validate_max_submissions_update(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        if int(value) < 1:
            raise ValueError("max_submissions must be at least 1 when set.")
        if int(value) > 200:
            raise ValueError("max_submissions cannot exceed 200.")
        return int(value)

    @field_validator("grade_precision")
    @classmethod
    def validate_optional_grade_precision(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip()
        if normalized not in {"integer", "decimal_1"}:
            raise ValueError("grade_precision must be integer or decimal_1.")
        return normalized


class HomeworkResponse(HomeworkBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    class_name: Optional[str] = None
    subject_name: Optional[str] = None
    creator_name: Optional[str] = None
    review_score: Optional[float] = None
    review_comment: Optional[str] = None
    task_status: Optional[str] = None
    task_error: Optional[str] = None
    attempt_count: int = 0
    submissions_remaining: Optional[int] = None
    latest_submission_is_late: Optional[bool] = None
    grading_rule_hint: Optional[str] = None
    llm_routing_spec: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True


class HomeworkBatchLateSubmissionUpdate(BaseModel):
    """批量更新多份作业的迟交策略（用于截止后统一允许补交等场景）。"""

    homework_ids: list[int] = Field(default_factory=list, min_length=1)
    allow_late_submission: Optional[bool] = None
    late_submission_affects_score: Optional[bool] = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "HomeworkBatchLateSubmissionUpdate":
        if self.allow_late_submission is None and self.late_submission_affects_score is None:
            raise ValueError("至少需要设置 allow_late_submission 或 late_submission_affects_score 之一。")
        return self


class HomeworkBatchRegradeRequest(BaseModel):
    """对某作业下多条学生提交批量入队 LLM 重评（仅 latest attempt）。"""

    submission_ids: Optional[list[int]] = None
    only_latest_attempt: bool = True


class HomeworkBatchRegradeItemResult(BaseModel):
    submission_id: int
    status: str  # "queued" | "skipped"
    reason: Optional[str] = None


class HomeworkBatchRegradeResponse(BaseModel):
    queued: int
    skipped: int
    results: list[HomeworkBatchRegradeItemResult] = Field(default_factory=list)


class HomeworkListResponse(BaseModel):
    total: int
    data: List[HomeworkResponse]


class HomeworkSubmissionCreate(BaseModel):
    content: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None
    remove_attachment: bool = False

    @model_validator(mode="after")
    def validate_submission_payload(self):
        self.content = self.content.strip() if isinstance(self.content, str) else self.content
        if not self.content:
            self.content = None
        if not self.remove_attachment and not (self.content or self.attachment_url):
            raise ValueError("Please provide submission content or an attachment.")
        return self


class HomeworkSubmissionResponse(BaseModel):
    id: int
    homework_id: int
    student_id: int
    subject_id: Optional[int] = None
    class_id: int
    content: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None
    submitted_at: datetime
    updated_at: datetime
    student_name: Optional[str] = None
    student_no: Optional[str] = None
    review_score: Optional[float] = None
    review_comment: Optional[str] = None
    latest_attempt_id: Optional[int] = None
    latest_task_status: Optional[str] = None
    latest_task_error: Optional[str] = None
    latest_task_error_code: Optional[str] = None
    latest_task_log: Optional[list[dict[str, Any]]] = None

    class Config:
        from_attributes = True


class HomeworkAttemptResponse(BaseModel):
    id: int
    homework_id: int
    student_id: int
    subject_id: Optional[int] = None
    class_id: int
    submission_summary_id: Optional[int] = None
    content: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None
    is_late: bool = False
    counts_toward_final_score: bool = True
    submitted_at: datetime
    updated_at: Optional[datetime] = None
    review_score: Optional[float] = None
    review_comment: Optional[str] = None
    task_status: Optional[str] = None
    task_error: Optional[str] = None
    task_error_code: Optional[str] = None
    task_log: Optional[list[dict[str, Any]]] = None
    score_source: Optional[str] = None

    class Config:
        from_attributes = True


class HomeworkSubmissionHistoryResponse(BaseModel):
    summary: Optional[HomeworkSubmissionResponse] = None
    attempts: List[HomeworkAttemptResponse] = Field(default_factory=list)


class HomeworkSubmissionReviewUpdate(BaseModel):
    attempt_id: Optional[int] = None
    review_score: float = Field(..., ge=0)
    review_comment: Optional[str] = None

    @model_validator(mode="after")
    def normalize_review_payload(self):
        if isinstance(self.review_comment, str):
            self.review_comment = self.review_comment.strip() or None
        return self


class HomeworkSubmissionStatusResponse(BaseModel):
    student_id: int
    student_name: Optional[str] = None
    student_no: Optional[str] = None
    class_name: Optional[str] = None
    submission_id: Optional[int] = None
    status: str
    submitted_at: Optional[datetime] = None
    content: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None
    review_score: Optional[float] = None
    review_comment: Optional[str] = None
    latest_attempt_id: Optional[int] = None
    latest_attempt_is_late: Optional[bool] = None
    latest_task_status: Optional[str] = None
    latest_task_error: Optional[str] = None
    latest_task_error_code: Optional[str] = None
    latest_task_log: Optional[list[dict[str, Any]]] = None
    attempt_count: int = 0


class HomeworkSubmissionStatusListResponse(BaseModel):
    total: int
    data: List[HomeworkSubmissionStatusResponse]


class HomeworkSubmissionDownloadRequest(BaseModel):
    submission_ids: List[int]


class HomeworkRegradeRequest(BaseModel):
    attempt_id: Optional[int] = None


class LLMEndpointPresetBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str
    base_url: str = "https://api.openai.com/v1/"
    api_key: str = ""
    model_name: str = "gpt-4o-mini"
    connect_timeout_seconds: int = Field(default=10, ge=1, le=300)
    read_timeout_seconds: int = Field(default=120, ge=1, le=600)
    max_retries: int = Field(default=2, ge=0, le=10)
    initial_backoff_seconds: int = Field(default=2, ge=1, le=120)
    is_active: bool = True


class LLMEndpointPresetCreate(LLMEndpointPresetBase):
    pass


class LLMEndpointPresetUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    connect_timeout_seconds: Optional[int] = Field(default=None, ge=1, le=300)
    read_timeout_seconds: Optional[int] = Field(default=None, ge=1, le=600)
    max_retries: Optional[int] = Field(default=None, ge=0, le=10)
    initial_backoff_seconds: Optional[int] = Field(default=None, ge=1, le=120)
    is_active: Optional[bool] = None


class LLMEndpointPresetResponse(BaseModel):
    id: int
    name: str
    base_url: str
    model_name: str
    connect_timeout_seconds: int
    read_timeout_seconds: int
    max_retries: int
    initial_backoff_seconds: int
    is_active: bool
    supports_vision: bool
    validation_status: str
    validation_message: Optional[str] = None
    text_validation_status: Optional[str] = None
    text_validation_message: Optional[str] = None
    vision_validation_status: Optional[str] = None
    vision_validation_message: Optional[str] = None
    validated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CourseLLMConfigEndpointSelection(BaseModel):
    preset_id: int
    priority: int = Field(default=1, ge=1)


class LLMGroupMemberSelection(BaseModel):
    preset_id: int
    priority: int = Field(default=1, ge=1)


class LLMGroupSelection(BaseModel):
    priority: int = Field(default=1, ge=1)
    name: Optional[str] = None
    members: List[LLMGroupMemberSelection] = Field(default_factory=list)


class CourseLLMConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    is_enabled: bool = False
    response_language: Optional[str] = None
    estimated_chars_per_token: float = Field(default=4.0, gt=0)
    estimated_image_tokens: int = Field(default=850, ge=1)
    max_input_tokens: int = Field(default=16000, ge=1000)
    max_output_tokens: int = Field(default=1200, ge=1)
    quota_timezone: str = "Asia/Shanghai"
    system_prompt: Optional[str] = None
    teacher_prompt: Optional[str] = None
    endpoints: List[CourseLLMConfigEndpointSelection] = Field(default_factory=list)
    groups: List[LLMGroupSelection] = Field(default_factory=list)
    # When the client sends only flat "endpoints" and empty "groups" (e.g. teacher UI), do not wipe an
    # existing group-based routing that was set via API/DB. Set true to force flat rebind and drop groups.
    replace_group_routing_with_flat_endpoints: bool = False


class CourseLLMConfigEndpointResponse(BaseModel):
    id: int
    preset_id: int
    priority: int
    group_id: Optional[int] = None
    preset_name: Optional[str] = None
    model_name: Optional[str] = None
    validation_status: Optional[str] = None
    supports_vision: Optional[bool] = None


class LLMGroupResponse(BaseModel):
    id: int
    priority: int
    name: Optional[str] = None
    members: List[CourseLLMConfigEndpointResponse] = Field(default_factory=list)


class CourseLLMConfigResponse(BaseModel):
    id: Optional[int] = None
    subject_id: int
    is_enabled: bool = False
    response_language: Optional[str] = None
    estimated_chars_per_token: float = 4.0
    estimated_image_tokens: int = 850
    max_input_tokens: int = 16000
    max_output_tokens: int = 1200
    quota_timezone: str = "Asia/Shanghai"
    system_prompt: Optional[str] = None
    teacher_prompt: Optional[str] = None
    endpoints: List[CourseLLMConfigEndpointResponse] = Field(default_factory=list)
    groups: List[LLMGroupResponse] = Field(default_factory=list)
    visual_validation_notice: str
    quota_usage: Optional[dict] = None


class NotificationBase(BaseModel):
    title: str
    content: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None
    priority: str = "normal"
    is_pinned: bool = False
    class_id: Optional[int] = None
    subject_id: Optional[int] = None


class NotificationCreate(NotificationBase):
    pass


class NotificationUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None
    remove_attachment: bool = False
    priority: Optional[str] = None
    is_pinned: Optional[bool] = None
    class_id: Optional[int] = None
    subject_id: Optional[int] = None


class NotificationResponse(NotificationBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    creator_name: Optional[str] = None
    class_name: Optional[str] = None
    subject_name: Optional[str] = None
    is_read: Optional[bool] = False

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    total: int
    unread_count: int
    data: List[NotificationResponse]


class CourseMaterialBase(BaseModel):
    title: str
    content: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None
    class_id: int
    subject_id: Optional[int] = None


class CourseMaterialCreate(CourseMaterialBase):
    pass


class CourseMaterialResponse(CourseMaterialBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    class_name: Optional[str] = None
    subject_name: Optional[str] = None
    creator_name: Optional[str] = None

    class Config:
        from_attributes = True


class CourseMaterialListResponse(BaseModel):
    total: int
    data: List[CourseMaterialResponse]
