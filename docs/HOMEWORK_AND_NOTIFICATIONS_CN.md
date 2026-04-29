# 作业批改、学生通知与花名册同步

本文说明**作业评分完成后如何提醒学生**、通知与数据的一致性，以及与学生账号、花名册相关的边界行为，便于教务与二次开发对照代码排查。

## 1. 学生如何收到「作业已批改」提醒

系统在以下时机向学生写入一条 **站内通知**（与普通通知共用 `Notification` 表及 `GET /api/notifications`）：

| 场景 | 说明 |
|------|------|
| **教师保存评分** | 调用 `PUT /api/homeworks/{id}/submissions/{submission_id}/review` 成功后 |
| **自动评分成功** | LLM 任务状态变为 `success` 且汇总分数已刷新后 |
| **自动评分跳过 LLM** | 该次提交已有教师分时，任务直接成功且不调用模型，仍会发一条说明来源的通知 |

**不会**在以下情况发「批改完成」类通知（避免重复与骚扰）：

- 自动评分任务处于 **失败** 后的自动重试排队阶段（可能多次失败）
- 与上一条**同标题、同发布者、同班级、同课程、正文完全一致**的记录（幂等去重）

### 1.1 谁能收到

通知写入逻辑在 `app/homework_notifications.py`，由 `app/routers/homework.py`（教师批改）与 `app/llm_grading.py`（自动批改成功）调用。

学生端必须能匹配到 **学生用户账号**：

- 花名册 `Student.student_no` **等于** 学生用户 `User.username`
- 学生用户 `User.role` 为学生
- 花名册 `Student.class_id` 与作业班级一致（与提交校验一致）

若学号未绑定登录用户或用户名不一致，**不会报错**，只是**不生成**该生的系统通知；学生仍可通过作业列表与提交页查看分数。

### 1.2 通知内容与可见范围

- **标题**：`作业已批改：{作业标题}`
- **正文**：课程名（若有）、当前**展示分**/满分、评语（若有）、来源（如「教师批改」「自动评分」等）
- **范围字段**：`class_id` 为作业班级，`subject_id` 为作业关联课程（若有），与学生端通知列表按课程筛选一致

创建者 `created_by` 为**布置作业的教师**（`homework.created_by`），以便与教师手动发布的通知在权限模型上保持一致；学生仅通过「可见班级/课程」阅读，不能代发。

## 2. 展示分与「最新一次提交」规则

汇总行 `HomeworkSubmission` 上的 `review_score` / `review_comment` 来自 `refresh_submission_summary`：在**当前最新一次提交（`latest_attempt_id`）**上，在教师候选分与自动候选分之间取规则内的最优展示结果。

因此：

- 教师对**历史某次提交**单独打分，若该次不是最新提交，汇总展示分仍可能以最新一次上的候选分为准（与既有测试 `test_new_attempt_auto_visible_when_teacher_scored_only_previous_attempt` 一致）。
- 教师批改接口在写入 `HomeworkScoreCandidate` 后会 **`flush` 再 `refresh_submission_summary`**，保证通知正文中的分数与数据库汇总一致。

## 3. 教师端「学生提交」界面

保存评分后，前端会先用 **PUT review 的响应体** 更新当前表格行的分数与任务相关字段，再重新拉取列表，减少「当前展示分」短暂滞后。

实现位置：`frontend/src/views/HomeworkSubmissions.vue`、`frontend/src/api/index.js`（`reviewSubmission` 使用 `returnFullResponse`）。

## 4. 花名册与学生用户班级

### 4.1 管理员修改学生用户的班级

当管理员通过 `PUT /api/users/{id}` 修改**学生**用户的 `class_id` 时，后端会尝试将花名册中 `student_no == username` 且仍指向**旧班级**的 `Student` 记录**迁到新班级**，并调用 `sync_student_course_enrollments`，以便新班级的必修课选课与作业班级一致。

详见 `app/routers/users.py` 中班级变更分支。

### 4.2 手动创建花名册：同班学号冲突

`POST /api/students` 在**同班、同学号**已存在时：

- 若请求中的**姓名**与已有记录一致：视为幂等更新（更新字段并同步选课等）。
- 若**姓名不同**：返回 **400**（「该班级中学号已存在」），避免两条不同学生共用同一学号。

## 5. 相关测试

- `tests/test_homework_grade_notifications.py`：教师批改通知、自动评分通知、同内容去重
- 作业与 LLM 行为：`tests/test_homework_llm_grading.py`、`tests/test_llm_concurrency_scenarios.py` 等

## 6. 扩展建议（未实现）

当前为 **站内通知**，依赖学生登录 Web 端查看「通知中心」。若需邮件/企业微信/短信，可在 `notify_student_homework_graded` 同类扩展点增加异步渠道，注意频率与失败重试策略。
