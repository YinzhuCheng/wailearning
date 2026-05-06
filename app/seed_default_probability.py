"""
Default seed: elementary probability elective (one chapter + homework + partial enroll/submit).

Loaded only when INIT_DEFAULT_DATA is true (see app.bootstrap.bootstrap).
Uses UTF-8 Chinese + Markdown/LaTeX-style formulas ($...$, $$...$$) for course text.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.auth import get_password_hash
from app.llm_grading import get_latest_validated_vision_preset, queue_grading_task
from app.models import (
    Class,
    CourseEnrollment,
    CourseMaterial,
    Homework,
    HomeworkAttempt,
    HomeworkSubmission,
    Semester,
    Student,
    Subject,
    User,
    UserRole,
)

PROB_SEED_CLASS_NAME = "2026\u7ea7\u7406\u5de5\u9009\u4fee\u8bd5\u70b9\u73ed"
PROB_COURSE_NAME = "\u521d\u7b49\u6982\u7387\u8bba\uff08\u516c\u5171\u9009\u4fee\u00b72026\u6625\uff09"
TEACHER_PRO_USERNAME = "teacher_pro"
TEACHER_PRO_PASSWORD = "teacher_pro"

PROB_STUDENTS = [
    ("\u9648\u5c0f\u5a01", "prob-2026-001", "prob_stu_001", "ProbStu001!"),
    ("\u6797\u5c0f\u6714", "prob-2026-002", "prob_stu_002", "ProbStu002!"),
    ("\u738b\u5c0f\u5ddd", "prob-2026-003", "prob_stu_003", "ProbStu003!"),
    ("\u8d75\u5c0f\u5cb3", "prob-2026-004", "prob_stu_004", "ProbStu004!"),
]

PROB_CHAPTER_MARKDOWN = r"""# 第1章 概率空间与公理化（初等概率论）

> **课程定位**：公共选修，面向已具备微积分与朴素集合论基础的本科生。本章建立后续全课程的共同语言。

## 学习目标

- 理解**随机试验、样本点、样本空间**与**事件**（集合）之间的关系。
- 掌握 Kolmogorov **三条公理**，并能在有限样本空间下计算概率。
- 会用加法公式、对立事件与**容斥原理**的基本形式处理简单模型。

## 1.1 样本空间与事件

设随机试验的所有可能结果组成的集合为 **样本空间** $\Omega$，任一子集 $A \subseteq \Omega$ 称为**事件**。

- 必然事件：$\Omega$
- 不可能事件：$\emptyset$
- 事件的并与交：$A \cup B$、$A \cap B$（也常写作 $AB$）

## 1.2 概率的公理化定义

**定义（概率测度）** 设 $\mathcal{F}$ 为 $\Omega$ 上的事件族（$\sigma$-代数，初等课程可先在有限情形下直观理解）。函数 $P: \mathcal{F} \to [0,1]$ 满足：

1. **非负性**：对任意 $A \in \mathcal{F}$，有 $P(A) \ge 0$。
2. **规范性**：$P(\Omega) = 1$。
3. **可列可加性**：若 $A_1,A_2,\ldots$ 两两不交，则
   $$
   P\Bigl(\bigcup_{n=1}^{\infty} A_n\Bigr) = \sum_{n=1}^{\infty} P(A_n).
   $$

在**古典概型**（有限样本空间且各样本点等可能）下，若 $|\Omega| = n$，则
$$
P(A) = \frac{|A|}{n}.
$$

## 1.3 加法公式与容斥（两事件）

对任意事件 $A,B$：
$$
P(A \cup B) = P(A) + P(B) - P(A \cap B).
$$

**对立事件**：$P(A^c) = 1 - P(A)$。

## 1.4 小例子（可读性练习）

1. 掷一枚公平骰子，$\Omega = \{1,2,3,4,5,6\}$，$P(\{k\}) = 1/6$。求“点数为偶数”的概率。
2. 设 $P(A)=0.4$，$P(B)=0.5$，$P(A \cap B)=0.2$，求 $P(A \cup B)$。

---

## 参考与延伸阅读（课程级）

1. **Sheldon Ross**, *A First Course in Probability*（第1–2章：公理与初等计数）.
2. **Grimmett & Welsh**, *Probability: An Introduction*（公理化与有限空间模型）.
3. **Durrett**, *Probability: Theory and Examples*（第1章附录：测度论入口，选读）.
4. 国内教材：李贤平《概率论基础》、何书元《概率引论》对应章节（集合与概率空间部分）。

> 说明：公式在系统中以 Markdown 形式存储；前端若启用数学渲染（如 KaTeX），将显示为排版公式，否则仍可读源码形式。
"""

PROB_HOMEWORK_MARKDOWN = r"""## 第一章习题（交 Markdown 文本即可）

### 题1（古典概型）
从集合 $\{1,2,\dots,10\}$ 中**均匀随机**取一数，记事件 $A$ 为“取到偶数”，事件 $B$ 为“取到不小于 6 的数”。

1. 写出样本空间 $\Omega$，并求 $P(A)$、$P(B)$。
2. 求 $P(A \cap B)$ 与 $P(A \cup B)$，并用加法公式验证。

### 题2（对立与差事件）
设 $P(A)=0.35$，$P(B)=0.55$，$P(A \cap B)=0.15$。求 $P(A \setminus B)$ 与 $P(A^c \cap B)$（可用文氏图说明思路）。

### 题3（概念）
用 3–5 句话解释：**为什么**概率测度需要“可列可加性”，而不仅是“有限可加性”（可举直观反例或类比）。
"""

PROB_RUBRIC_STUDENT = (
    "\u5bf9\u5b66\u751f\u53ef\u89c1\uff1a\n"
    "1\uff09\u9898 1 \u9700\u6b63\u786e\u5199\u51fa $\\Omega$\u3001\u7b49\u53ef\u80fd\u5047\u8bbe\uff0c"
    "\u5e76\u7ed9\u51fa $P(A),P(B),P(A\\cap B),P(A\\cup B)$ \u7684\u6570\u503c\u4e0e\u9a8c\u8bc1\u601d\u8def\uff1b\n"
    "2\uff09\u9898 2 \u9700\u5408\u7406\u8fd0\u7528 $P(A\\setminus B)=P(A)-P(A\\cap B)$ \u7b49\u5173\u7cfb\uff0c\u7ed3\u679c\u4e00\u81f4\uff1b\n"
    "3\uff09\u9898 3 \u9700\u63d0\u5230\u53ef\u5217/\u65e0\u9650\u6837\u672c\u7a7a\u95f4\u6216\u8fde\u7eed\u578b\u968f\u673a\u73b0\u8c61\u7684\u4e00\u6761\u7406\u7531\uff08\u4e0d\u6c42\u4e25\u683c\u6d4b\u5ea6\u8bba\u8bc1\u660e\uff09\u3002"
)

PROB_RUBRIC_TEACHER = (
    "\u4ec5\u6559\u5e08/\u81ea\u52a8\u8bc4\u5206\uff1a\n"
    "\u9898 1\uff1a$P(A)=1/2$, $P(B)=1/2$, $P(A\\cap B)=3/10$, $P(A\\cup B)=7/10$\uff1b\n"
    "\u9898 2\uff1a$P(A\\setminus B)=0.20$, $P(A^c\\cap B)=0.40$\uff1b\n"
    "\u9898 3\uff1a\u80af\u5b9a\u53ef\u5217\u52a0\u6027\u5bf9\u5904\u7406\u53ef\u5217\u4e2a\u4e92\u65a5\u4e8b\u4ef6\u4e4b\u5e76\u7684\u5fc5\u8981\u6027\uff0c\u6216\u4e3e\u8fde\u7eed\u5206\u5e03\u4e0b\u5355\u70b9\u6982\u7387\u4e3a 0 \u7684\u4f8b\u5b50\u5373\u53ef\u7ed9\u6ee1\u5206\u3002"
)

PROB_REFERENCE = (
    "\u53c2\u8003\u7b54\u6848\u6216\u601d\u8def\uff08\u4ec5\u6559\u5e08\u53ef\u89c1\uff09\uff1a\u89c1 rubric_teacher_text \u4e2d\u6570\u503c\u4e0e\u8bc4\u5206\u5c3a\u5ea6\u3002"
    "\u5efa\u8bae\u6ee1\u5206 100 \u6309 35/35/30 \u5206\u914d\u4e09\u9898\u3002"
)

PROB_SUBMIT_SAMPLE_B = r"""# 第一章习题（简要作答 prob_stu_002）

题1：$\Omega=\{1,\dots,10\}$，$P(A)=1/2$，$P(B)=1/2$，$P(A\cap B)=3/10$，$P(A\cup B)=7/10$（加法公式验证 $1/2+1/2-3/10=7/10$）。

题2：$P(A\setminus B)=0.2$，$P(A^c\cap B)=0.4$。

题3：需要可列可加性才能在无限样本或可列划分时保持一致性。
"""

PROB_SUBMIT_SAMPLE = r"""# 第一章习题作答（prob_stu_001）

## 题1
- $\Omega = \{1,2,\dots,10\}$，古典概型，$|\Omega|=10$。
- $A=\{2,4,6,8,10\}$，$|A|=5$，故 $P(A)=5/10=1/2$。
- $B=\{6,7,8,9,10\}$，$|B|=5$，故 $P(B)=1/2$。
- $A\cap B=\{6,8,10\}$，$|A\cap B|=3$，故 $P(A\cap B)=3/10$。
- $A\cup B$ 用加法公式：$P(A\cup B)=1/2+1/2-3/10=7/10$。

## 题2
- $P(A\setminus B)=P(A)-P(A\cap B)=0.35-0.15=0.20$。
- $P(A^c\cap B)=P(B)-P(A\cap B)=0.55-0.15=0.40$。

## 题3
如果只要求有限可加，遇到可列个互斥事件时无法保证“整体概率”良好；连续型随机变量中单点概率为 0，但需要把区间概率用可列操作拼接，Kolmogorov 公理把这套逻辑统一起来。
"""


def _ensure_user(
    db,
    *,
    username: str,
    password: str,
    real_name: str,
    role: str,
    class_id: int | None = None,
) -> User:
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return existing
    user = User(
        username=username,
        hashed_password=get_password_hash(password),
        real_name=real_name,
        role=role,
        class_id=class_id,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _pick_semester(db) -> Semester | None:
    row = db.query(Semester).filter(Semester.is_active.is_(True)).order_by(Semester.year.desc(), Semester.id.desc()).first()
    if row:
        return row
    return db.query(Semester).order_by(Semester.id.asc()).first()


def _seed_homework_submission_one_student(db, homework: Homework, student: Student, content: str) -> None:
    exists = (
        db.query(HomeworkSubmission)
        .filter(HomeworkSubmission.homework_id == homework.id, HomeworkSubmission.student_id == student.id)
        .first()
    )
    if exists:
        return
    now = datetime.now(timezone.utc)
    sub = HomeworkSubmission(
        homework_id=homework.id,
        student_id=student.id,
        subject_id=homework.subject_id,
        class_id=homework.class_id,
        content=content,
        submitted_at=now - timedelta(hours=2),
        updated_at=now - timedelta(hours=2),
    )
    db.add(sub)
    db.flush()
    attempt = HomeworkAttempt(
        homework_id=homework.id,
        student_id=student.id,
        subject_id=homework.subject_id,
        class_id=homework.class_id,
        submission_summary_id=sub.id,
        content=content,
        is_late=False,
        counts_toward_final_score=True,
        submitted_at=sub.submitted_at,
        updated_at=sub.updated_at,
    )
    db.add(attempt)
    db.flush()
    sub.latest_attempt_id = attempt.id
    if homework.auto_grading_enabled:
        queue_grading_task(db, attempt, "new_submission")


def seed_elementary_probability_elective_course(db) -> None:
    """
    Idempotent: skips if course name already exists.
    Creates teacher_pro, a pilot class, four student accounts, elective course with 2 enrollments,
    chapter material (Markdown + LaTeX), homework (auto-grade if validated LLM exists), one submission.
    """
    if db.query(Subject).filter(Subject.name == PROB_COURSE_NAME).first():
        print(f"Seed probability course: '{PROB_COURSE_NAME}' already exists, skip.")
        return

    teacher = _ensure_user(
        db,
        username=TEACHER_PRO_USERNAME,
        password=TEACHER_PRO_PASSWORD,
        real_name="\u6982\u7387\u8bba\u4e13\u4e1a\u6559\u5e08\uff08\u793a\u4f8b\uff09",
        role=UserRole.TEACHER.value,
        class_id=None,
    )

    klass = db.query(Class).filter(Class.name == PROB_SEED_CLASS_NAME).first()
    if not klass:
        klass = Class(name=PROB_SEED_CLASS_NAME, grade=2026)
        db.add(klass)
        db.flush()

    student_models: list[Student] = []
    for real_name, st_no, uname, pwd in PROB_STUDENTS:
        _ensure_user(db, username=uname, password=pwd, real_name=real_name, role=UserRole.STUDENT.value, class_id=klass.id)
        existing_st = db.query(Student).filter(Student.class_id == klass.id, Student.student_no == st_no).first()
        if existing_st:
            student_models.append(existing_st)
            continue
        st = Student(name=real_name, student_no=st_no, class_id=klass.id, teacher_id=teacher.id)
        db.add(st)
        db.flush()
        student_models.append(st)

    semester = _pick_semester(db)
    if not semester:
        print("Seed probability course: no semester row found, skip.")
        return

    course = Subject(
        name=PROB_COURSE_NAME,
        teacher_id=teacher.id,
        class_id=klass.id,
        semester_id=semester.id,
        course_type="elective",
        status="active",
        semester=semester.name,
        weekly_schedule="\u5468\u4e8c 10:00-11:40\uff1b\u53cc\u5468\u5468\u56db 14:00-15:40 \u4e60\u9898\u8bfe",
        description=(
            "\u672c\u8bfe\u4ecb\u7ecd\u521d\u7b49\u6982\u7387\u8bba\u7684\u516c\u5171\u9009\u4fee\u5185\u5bb9\uff0c"
            "\u7b2c\u4e00\u7ae0\u805a\u7126\u6982\u7387\u7a7a\u95f4\u4e0e\u516c\u7406\u5316\u3002"
            "\u9009\u4fee\u8bfe\u4e0d\u5f3a\u5236\u5168\u73ed\u9009\u8bfe\uff1b\u9ed8\u8ba4\u79cd\u5b50\u6570\u636e\u4ec5\u4e3a\u90e8\u5206\u540c\u5b66\u9009\u8bfb\u3002"
        ),
    )
    db.add(course)
    db.flush()

    # Only first two students enrolled (elective opt-in seed).
    for st in student_models[:2]:
        exists = (
            db.query(CourseEnrollment)
            .filter(CourseEnrollment.subject_id == course.id, CourseEnrollment.student_id == st.id)
            .first()
        )
        if exists:
            continue
        db.add(
            CourseEnrollment(
                subject_id=course.id,
                student_id=st.id,
                class_id=klass.id,
                enrollment_type="elective",
                can_remove=True,
            )
        )

    db.add(
        CourseMaterial(
            title="\u7b2c1\u7ae0 \u8bfe\u4ef6\uff1a\u6982\u7387\u7a7a\u95f4\u3001\u516c\u7406\u5316\u4e0e\u57fa\u672c\u6027\u8d28\uff08Markdown\uff09",
            content=PROB_CHAPTER_MARKDOWN,
            class_id=klass.id,
            subject_id=course.id,
            created_by=teacher.id,
        )
    )

    preset = get_latest_validated_vision_preset(db)
    auto_ok = preset is not None
    if auto_ok:
        from app.bootstrap import _wire_course_llm_from_preset

        _wire_course_llm_from_preset(db, course.id, preset, teacher.id)
    else:
        print(
            "Seed probability course: no validated vision LLM preset in DB; "
            "homework auto_grading disabled until an endpoint is configured."
        )

    hw = Homework(
        title="\u7b2c1\u7ae0\u4e60\u9898\uff1a\u6982\u7387\u516c\u7406\u4e0e\u52a0\u6cd5\u516c\u5f0f\uff08Markdown\u4f5c\u7b54\uff09",
        content=PROB_HOMEWORK_MARKDOWN,
        class_id=klass.id,
        subject_id=course.id,
        due_date=datetime.now(timezone.utc) + timedelta(days=14),
        max_score=100,
        grade_precision="integer",
        auto_grading_enabled=auto_ok,
        rubric_text=PROB_RUBRIC_STUDENT,
        rubric_teacher_text=PROB_RUBRIC_TEACHER,
        reference_answer=PROB_REFERENCE,
        response_language="zh-CN",
        allow_late_submission=True,
        late_submission_affects_score=False,
        created_by=teacher.id,
    )
    db.add(hw)
    db.flush()

    # Enrolled students: both submit (one detailed, one brief); unenrolled class members have no submission.
    if len(student_models) >= 1:
        _seed_homework_submission_one_student(db, hw, student_models[0], PROB_SUBMIT_SAMPLE)
    if len(student_models) >= 2:
        _seed_homework_submission_one_student(db, hw, student_models[1], PROB_SUBMIT_SAMPLE_B)

    db.commit()
    print(
        f"Seed probability course: created '{PROB_COURSE_NAME}' with teacher '{TEACHER_PRO_USERNAME}', "
        f"class '{PROB_SEED_CLASS_NAME}', 2 elective enrollments / 4 class students, "
        f"chapter material + homework (auto_grading={auto_ok})."
    )
