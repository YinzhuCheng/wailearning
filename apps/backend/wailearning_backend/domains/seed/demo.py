"""Default demo data: teacher `teacher`, class 人工智能1班, students stu1–stu5.

- **必修课**「数据挖掘」：教师按班级花名册统一入课（`sync_course_enrollments`），含演示章节与第一次作业；写入虚构的学期起止与多时段课表 JSON。
- **选修课**「大语言模型」：同班开设，学生需自主选课；预置简要资料与入门作业，**不**自动写入全班选课；同样写入基本教学日历与课表 JSON。

若数据库中已有**通过校验且可用于评分**的全局 LLM 端点预设（`ensure_schema_updates` 会写入内置默认预设），本种子会为演示必修课/选修课**幂等绑定**首个可用预设（必修课同时 `is_enabled=True` 以配合自动评分作业）；否则不写入端点，由管理员或教师在课程 LLM 配置中手动选择。

演示必修课作业**不包含参考答案**（`reference_answer` 为空）。必修课资料区含三层演示章节。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from apps.backend.wailearning_backend.core.auth import get_password_hash
from apps.backend.wailearning_backend.domains.courses.access import sync_course_enrollments
from apps.backend.wailearning_backend.db.models import (
    Class,
    CourseEnrollment,
    CourseExamWeight,
    CourseGradeScheme,
    CourseLLMConfig,
    CourseLLMConfigEndpoint,
    CourseMaterial,
    CourseMaterialChapter,
    CourseMaterialSection,
    Homework,
    LLMEndpointPreset,
    Semester,
    Student,
    Subject,
    User,
    UserRole,
)
from apps.backend.wailearning_backend.domains.roster.sync import reconcile_student_users_and_roster

_DEMO_PASSWORD = "111111"

_CLASS_NAME = "人工智能1班"
_LEGACY_CLASS_NAME = "数据挖掘默认班"
_COURSE_NAME = "数据挖掘"

_LLM_COURSE_NAME = "大语言模型"
_LLM_MATERIAL_TITLE = "【选修】大语言模型：课程说明与阅读材料"
_LLM_MATERIAL_CONTENT = """## 欢迎选修「大语言模型」

本课程为**选修课**，请在「我的课程」页面使用**选课**按钮加入后，方可查看作业与完整资料池。

### 学习目标

- 了解大语言模型的基本能力与局限；
- 掌握提示（Prompt）书写的基本结构；
- 完成一次简短的实践作业。

### 推荐阅读

1. 关注课程通知与 LLM 使用规范；
2. 课前可预习「提示工程」基础概念。
"""
_LLM_HOMEWORK_TITLE = "大语言模型入门作业：提示工程小练习"
_LLM_HOMEWORK_CONTENT = """请完成以下任务（建议 300–800 字或等价条目）：

1. 用你自己的话解释：什么是「提示工程」？它为什么会影响大语言模型的输出质量？
2. 设计一个用于「总结一段中文新闻要点」的提示模板，并说明每个部分的作用。
3. 指出使用大语言模型辅助学习时，你认为需要注意的两条风险或边界。

提交形式：纯文本或 Markdown 均可。"""
_LLM_RUBRIC_TEXT = """总分 100。关注是否理解提示工程、模板结构是否清楚、风险意识是否到位；表达清晰即可，不必长篇。
"""

_TEACHER_DISPLAY_NAME = "李演示"
_COURSE_DESCRIPTION = (
    "数据挖掘入门与实践（演示课程）。涵盖 Python 数据分析基础、特征与可视化、"
    "简单预处理与经典数据集探索；平时作业与课堂表现结合考核。"
)


def _spring_term_bounds(year: int) -> tuple[datetime, datetime]:
    """Fictional spring term window for demo courses (UTC midnight boundaries)."""
    start = datetime(year, 2, 24, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(year, 6, 30, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


def _demo_data_mining_calendar(semester: Semester | None) -> dict:
    """
    Fictional syllabus calendar + structured course_times JSON for API consumers.

    Returns keys: weekly_schedule, course_start_at, course_end_at, course_times_json, description
    """
    year = int(semester.year) if semester and getattr(semester, "year", None) else 2026
    term_label = semester.name if semester else f"{year}春季（演示）"
    start, end = _spring_term_bounds(year)
    weekly_main = (
        "每周二 14:00–16:00 理论课；每周四 09:50–11:25 上机与习题讲评（教室与机位以教务为准，以下为演示占位）"
    )
    calendar_md = (
        "### 教学日历（演示数据，虚构）\n\n"
        f"- **学期**：{term_label}\n"
        f"- **开课—结课**：{year} 年 2 月 24 日 — {year} 年 6 月 30 日（约 16 教学周，遇节假日顺延）\n"
        f"- **上课节律**：{weekly_main}\n"
        "- **理论课地点（演示）**：东十二教学楼 301\n"
        "- **上机地点（演示）**：计算中心 B201\n"
        "- **答疑时间**：双周周三 12:30–13:30，线上会议链接于课程群发布\n"
        "- **期中**：约第 8 周随堂小测；**期末**：报告 + 答辩，截止周次见教务系统\n"
        "- **总学时（演示）**：48 学时（理论 32 + 上机 16）\n"
    )
    desc = f"{_COURSE_DESCRIPTION}\n\n{calendar_md}"
    items = [
        {
            "weekly_schedule": "每周二 14:00–16:00 理论课（演示：东十二-301）",
            "course_start_at": start.isoformat(),
            "course_end_at": end.isoformat(),
        },
        {
            "weekly_schedule": "每周四 09:50–11:25 上机与习题讲评（演示：计算中心-B201）",
            "course_start_at": start.isoformat(),
            "course_end_at": end.isoformat(),
        },
    ]
    return {
        "weekly_schedule": items[0]["weekly_schedule"],
        "course_start_at": start,
        "course_end_at": end,
        "course_times_json": json.dumps(items, ensure_ascii=False),
        "description": desc,
    }


def _demo_llm_elective_calendar(semester: Semester | None) -> dict:
    """Fictional elective calendar (lighter load) + course_times JSON."""
    year = int(semester.year) if semester and getattr(semester, "year", None) else 2026
    term_label = semester.name if semester else f"{year}春季（演示）"
    start, end = _spring_term_bounds(year)
    weekly_main = "每周四 15:00–17:00 研讨课（演示占位）"
    calendar_md = (
        "### 教学日历（演示数据，虚构）\n\n"
        f"- **学期**：{term_label}\n"
        f"- **开课—结课**：{year} 年 2 月 24 日 — {year} 年 6 月 20 日（选修，共约 14 次课）\n"
        f"- **上课节律**：{weekly_main}\n"
        "- **教室（演示）**：南一楼 108 讨论室\n"
        "- **线上回放**：课后 48 小时内上传至课程资料区（演示流程）\n"
    )
    base_desc = (
        "全校默认选修示例：大语言模型基础与应用入门。完成本课需由学生在「我的课程」中自主选课；"
        "内容包含提示工程简介与一次实践作业。"
    )
    desc = f"{base_desc}\n\n{calendar_md}"
    items = [
        {
            "weekly_schedule": "每周四 15:00–17:00 研讨课（演示：南一楼-108）",
            "course_start_at": start.isoformat(),
            "course_end_at": end.isoformat(),
        },
        {
            "weekly_schedule": "隔周周五 14:00–15:00 助教答疑（演示：线上）",
            "course_start_at": start.isoformat(),
            "course_end_at": end.isoformat(),
        },
    ]
    return {
        "weekly_schedule": items[0]["weekly_schedule"],
        "course_start_at": start,
        "course_end_at": end,
        "course_times_json": json.dumps(items, ensure_ascii=False),
        "description": desc,
    }

# Demo material outline: three chapter nodes (depth 3), idempotent by root title.
_DEMO_CHAPTER_ROOT = "【演示】第一单元：导论与数据概览"
_DEMO_CHAPTER_L2 = "【演示】第一节：Python 环境与常用库"
_DEMO_CHAPTER_L3 = "【演示】1.1 课程资料与拓展阅读"


def _first_validated_preset_for_demo_course(db: Session) -> LLMEndpointPreset | None:
    """
    Global preset suitable for demo course LLM binding (validated + active + usable for grading rules).
    """
    for pr in (
        db.query(LLMEndpointPreset)
        .filter(
            LLMEndpointPreset.is_active.is_(True),
            LLMEndpointPreset.validation_status == "validated",
            LLMEndpointPreset.supports_vision.is_(True),
        )
        .order_by(LLMEndpointPreset.id.asc())
        .all()
    ):
        ts = getattr(pr, "text_validation_status", None)
        if ts == "failed":
            continue
        if ts not in (None, "passed", "skipped"):
            continue
        vs = getattr(pr, "vision_validation_status", None)
        if vs == "failed":
            continue
        return pr
    return None


def _ensure_demo_subject_llm_binding(
    db: Session,
    *,
    subject_id: int,
    teacher_id: int,
    enable_auto_grading: bool,
) -> None:
    """Idempotent: attach first suitable validated preset when the course has no LLM endpoints."""
    cfg = db.query(CourseLLMConfig).filter(CourseLLMConfig.subject_id == subject_id).first()
    if not cfg:
        cfg = CourseLLMConfig(
            subject_id=subject_id,
            created_by=teacher_id,
            updated_by=teacher_id,
            is_enabled=bool(enable_auto_grading),
        )
        db.add(cfg)
        db.flush()
    if db.query(CourseLLMConfigEndpoint).filter(CourseLLMConfigEndpoint.config_id == cfg.id).first():
        if enable_auto_grading:
            cfg.is_enabled = True
        return
    preset = _first_validated_preset_for_demo_course(db)
    if not preset:
        return
    db.add(CourseLLMConfigEndpoint(config_id=cfg.id, preset_id=preset.id, priority=1))
    if enable_auto_grading:
        cfg.is_enabled = True
    db.flush()


_HOMEWORK_TITLE = "数据挖掘第一次作业：Python 环境、NumPy/Pandas 基础与 Wine 数据探索"

_HOMEWORK_CONTENT = """本次作业是数据挖掘课程的第一次实践作业，目标是帮助大家完成 Python 数据分析环境的基本准备，并初步熟悉 NumPy、Pandas、Matplotlib、Seaborn 和 sklearn 等常用工具。

本次作业不要求大家已经掌握复杂机器学习模型，重点是能够把 Python 数据分析流程跑通，并能够用自己的语言解释基本结果。

一、Python 环境与基础运行

请完成以下任务，并在提交内容中展示你的完成情况：

1. 说明你使用的 Python 环境，例如 Anaconda、Jupyter Notebook、VS Code、Google Colab、课程服务器或其他在线 Python 环境。
2. 成功运行一个简单的 Python 程序，例如输出 Hello Python。
3. 尝试导入以下常用库中的若干个：
   - numpy
   - pandas
   - matplotlib
   - seaborn
   - sklearn

如果你在环境配置过程中遇到问题，也可以把错误信息、解决过程或自己的理解写出来。第一次作业更重视尝试和过程，不要求所有同学的环境完全一致。

二、概念理解题

请用自己的话回答以下问题：

1. NumPy 在数据分析或数据挖掘中的作用是什么？
2. Pandas 在数据分析或数据挖掘中的作用是什么？
3. NumPy 数组和 Pandas DataFrame 分别适合处理什么类型的问题？
4. 请解释以下 Pandas 操作的大致含义：

   df.loc[0:10, ['age', 'score']]

   df[df['age'] > 20]

   df.groupby('gender')['score'].mean()

不要求回答非常理论化，只要能够体现你理解这些操作在做什么即可。

三、Wine 数据集基础操作

请使用 sklearn.datasets.load_wine 加载 Wine 数据集，并完成基础数据探索。

建议完成以下任务：

1. 加载 Wine 数据集。
2. 将数据转换为 Pandas DataFrame。
3. 添加 target 或 target_name 列，用于表示样本类别。
4. 查看数据前 5 行。
5. 查看数据的基本信息或描述性统计结果，例如 head()、info()、describe()。
6. 选取若干个你认为重要或感兴趣的特征进行分析。

推荐关注以下特征：

- alcohol
- malic_acid
- color_intensity
- hue
- proline

你可以分析全部推荐特征，也可以选择其中几个进行分析。

四、简单可视化与观察结论

请对 Wine 数据集进行简单可视化分析。

可选图表包括但不限于：

1. 直方图；
2. 箱线图；
3. 散点图；
4. 类别分布图；
5. pairplot；
6. 相关系数热力图。

至少完成一种可视化即可。如果由于环境问题无法正常显示图片，也可以使用统计表格和文字说明代替。

请根据统计结果或可视化结果，用自己的话写出至少 2 到 3 条观察结论。例如：

1. 不同类别葡萄酒在哪些特征上可能存在差异；
2. 哪些特征的数值范围较大；
3. 哪些特征可能有助于区分不同类别；
4. 是否发现某些特征存在明显分布差异。

五、NumPy 标准化练习

请尝试实现一个简单的标准化函数 standardize(x)。

函数目标是把一维数值数组转换为均值接近 0、标准差接近 1 的形式。

参考形式如下：

def standardize(x):
    '''
    输入：一维 numpy 数组 x
    输出：标准化后的数组
    '''
    return (x - x.mean()) / x.std()

请完成以下任务：

1. 从 Wine 数据集中选取一个数值特征，例如 alcohol。
2. 将该特征转换为 NumPy 数组。
3. 使用 standardize(x) 或其他等价方式进行标准化。
4. 查看标准化后的均值和标准差。
5. 用文字解释标准化的作用。

如果你使用 sklearn.preprocessing.StandardScaler 完成标准化，也可以接受，但建议尽量理解手写公式的含义。

六、思考题：特征尺度与建模

Wine 数据集中，不同化学成分的数值范围差异较大。例如 proline 的数值通常远大于 alcohol。

请回答：

1. 如果直接把这些原始特征输入到某些机器学习模型中，可能会出现什么问题？
2. 为什么很多机器学习模型需要进行标准化或归一化？
3. 请举出一个对特征尺度比较敏感的模型，并简单说明原因。

可以举的模型包括但不限于：

- KNN
- K-Means
- SVM
- 逻辑回归
- 神经网络

七、拓展练习，选做加分

以下拓展练习为选做内容，不做不扣分，完成后可以酌情加分。

选项 A：Iris 数据集分析

1. 使用 sklearn.datasets.load_iris 加载 Iris 数据集。
2. 构建 DataFrame，并添加 target_name 列。
3. 按类别计算各特征的平均值。
4. 画出至少一张图表，例如箱线图、散点图或 pairplot。
5. 简要说明哪些特征可能有助于区分不同类别。

选项 B：自选公开 CSV 数据集

1. 从 Kaggle、UCI 或其他公开来源选择一个小型 CSV 数据集。
2. 使用 pandas 读取数据。
3. 完成 head()、info()、describe() 等基础查看。
4. 至少绘制一张简单图表。
5. 用不超过 200 字写一段迷你 EDA 报告，说明数据集是什么、有哪些有意思的特征、适合做什么类型的数据挖掘任务。

提交建议：

本次作业推荐提交 Jupyter Notebook 文件（.ipynb）或 PDF 报告。

推荐提交形式：

1. .ipynb 文件：适合展示代码、运行结果、图表和文字说明；
2. PDF 报告：适合展示整理后的实验过程和结论；
3. 也可以同时提交 .ipynb 和 PDF。

如果暂时不熟悉 Notebook 或 PDF，也可以提交 .py 文件、Word 文档、Markdown 文档、截图或压缩包。只要提交内容能够清楚展示你的完成过程和结果即可。

推荐文件命名格式：

学号_姓名_数据挖掘第一次作业.ipynb

或：

学号_姓名_数据挖掘第一次作业.pdf

例如：

20260001_张三_数据挖掘第一次作业.ipynb
20260001_张三_数据挖掘第一次作业.pdf

文件命名不规范一般不会严重扣分，但建议大家尽量按照格式提交，方便教师整理和查看。"""

_RUBRIC_TEXT = """请根据以下标准评分，总分 100 分。评分时应以鼓励学生完成第一次数据挖掘实践为主，重点关注学生是否动手完成了基本流程，是否能够展示代码、结果和自己的理解。不要过度强调提交格式、图表美观程度或答案是否完全一致。

一、Python 环境与基础运行，20 分

1. 能说明自己使用的 Python 环境，6 分
   - 可以是 Anaconda、Jupyter Notebook、VS Code、Google Colab、课程服务器或其他在线 Python 环境。
   - 不要求所有学生使用完全相同的环境。

2. 能成功运行基础 Python 程序，4 分
   - 例如输出 Hello Python，或运行其他简单 Python 代码。

3. 能成功导入常用数据分析库中的大部分，5 分
   - 包括 numpy、pandas、matplotlib、seaborn、sklearn 等。
   - 不要求所有库都必须成功，只要能够体现学生进行了环境准备即可。

4. 能简单说明环境配置过程、使用方式或遇到的问题，5 分
   - 如果环境配置失败，但学生清楚记录了尝试过程、错误信息或解决思路，也可以酌情给分。

二、概念理解题，20 分

1. 能用自己的话说明 NumPy 的基本作用，5 分
   - 例如用于数组计算、矩阵运算、数值处理等。

2. 能用自己的话说明 Pandas 的基本作用，5 分
   - 例如用于表格数据处理、数据清洗、缺失值处理、字段选择、条件筛选、分组统计等。

3. 能大致区分 NumPy 数组和 Pandas DataFrame 的使用场景，5 分
   - 不要求表述严格，只要方向正确即可。

4. 能基本解释 loc、条件筛选、groupby 聚合等 Pandas 操作，5 分
   - df.loc[0:10, ['age', 'score']]：选择部分行和指定列；
   - df[df['age'] > 20]：筛选 age 大于 20 的行；
   - df.groupby('gender')['score'].mean()：按 gender 分组后计算 score 平均值。
   - 学生用自己的语言解释正确即可，不必逐字一致。

三、Wine 数据集基础操作，25 分

1. 能成功加载 Wine 数据集，或使用其他合理数据集完成类似分析，5 分。

2. 能将数据整理成表格形式，例如 Pandas DataFrame，5 分。

3. 能查看数据前几行、字段信息、类别信息或基本统计信息，5 分。

4. 能选取若干特征进行分析，5 分。
   - 推荐特征包括 alcohol、malic_acid、color_intensity、hue、proline。
   - 如果学生没有严格使用全部推荐特征，但完成了类似分析，也可酌情给分。

5. 能使用 describe()、value_counts()、groupby() 或其他方式进行基础统计分析，5 分。

四、简单可视化与观察结论，15 分

1. 能完成至少一种合理的数据可视化，6 分。
   - 可以是直方图、箱线图、散点图、类别分布图、pairplot、热力图等。
   - 如果图表显示不完整，但代码和思路基本正确，也可以酌情给分。

2. 能结合统计结果或图表写出至少 2 到 3 条观察结论，6 分。
   - 结论可以涉及类别差异、特征分布、特征尺度、可能有用的分类特征等。

3. 能将图表或统计结果与文字说明对应起来，3 分。
   - 不要求分析很深入，只要不是单纯贴代码即可。

五、NumPy 标准化练习，10 分

1. 能尝试实现 standardize(x) 函数，或使用等价方法完成标准化，4 分。
   - 手写函数、NumPy 运算或 StandardScaler 均可接受。

2. 能对某个数值特征进行标准化处理，2 分。

3. 能查看或说明标准化后均值接近 0、标准差接近 1，2 分。

4. 能用自己的话解释标准化的作用，2 分。
   - 例如减少不同量纲和数值范围对模型训练的影响。

六、特征尺度与建模思考题，10 分

1. 能说明不同特征数值范围差异可能带来的问题，4 分。
   - 例如数值范围大的特征可能在距离计算或优化过程中占据更大影响。

2. 能解释为什么需要标准化或归一化，3 分。

3. 能举出一个对特征尺度敏感的模型并简单说明原因，3 分。
   - 例如 KNN、K-Means、SVM、逻辑回归、神经网络等。

七、表达与完成度，5 分

1. 作业整体结构较清楚，2 分。

2. 代码、截图、文字说明或运行结果能够基本对应，2 分。

3. 提交内容能够让教师或自动评分系统判断学生完成情况，1 分。

八、拓展练习加分项，最多加 10 分

拓展练习为选做内容，不做不扣分。完成 Iris 数据集分析或自选公开 CSV 数据集分析的学生，可以根据完成情况加 1 到 10 分。

1. 完成一个额外数据集的读取和基本查看，加 3 分。
2. 完成描述性统计、分组统计或类似分析，加 2 分。
3. 完成至少一张额外图表，加 2 分。
4. 写出简短但合理的分析结论，加 3 分。

如果系统支持超过满分，可以允许最高 110 分。如果系统不支持超过满分，则加分项可以用于弥补前面的小失误，但最终成绩不超过 100 分。

宽松评分原则：

1. 本次作业是第一次实践作业，评分应以鼓励学生动手为主。
2. 推荐提交 .ipynb 或 PDF，但不强制限定提交形式。
3. 没有提交 .ipynb 不应直接大幅扣分，只要提交内容能够展示代码、结果或分析过程即可。
4. 图表数量不足时不应大幅扣分，只要有基本统计分析或文字解释即可酌情给分。
5. 代码存在小错误但整体思路清楚，可以少量扣分，不应直接给低分。
6. 文件命名不规范一般只提醒，不作为主要扣分项；严重无法识别身份时再酌情扣 1 到 2 分。
7. 学生如果使用了 Colab、在线平台、课程服务器或其他 Python 环境，也应视为有效完成。
8. 学生如果使用了其他合理数据集完成类似流程，也可以酌情给分。
9. 只有在几乎没有完成主要任务、内容明显与作业无关、完全无法判断完成情况，或存在明显大段抄袭时，才应给较低分。
10. 对于认真完成主要任务的学生，建议分数集中在 85 分以上。"""


def _seed_demo_grade_weights(db: Session, *, course: Subject) -> None:
    """Align demo course with default grade composition (30/20/50) when rows are missing."""
    if not db.query(CourseGradeScheme).filter(CourseGradeScheme.subject_id == course.id).first():
        db.add(
            CourseGradeScheme(
                subject_id=course.id,
                homework_weight=30.0,
                extra_daily_weight=20.0,
            )
        )
    if not db.query(CourseExamWeight).filter(CourseExamWeight.subject_id == course.id).first():
        db.add(CourseExamWeight(subject_id=course.id, exam_type="期末考试", weight=50.0))


def _seed_demo_material_chapters(db: Session, *, subject_id: int) -> None:
    """Three-level outline (root → child → grandchild) for course materials UI demo."""
    exists = (
        db.query(CourseMaterialChapter)
        .filter(
            CourseMaterialChapter.subject_id == subject_id,
            CourseMaterialChapter.title == _DEMO_CHAPTER_ROOT,
            CourseMaterialChapter.is_uncategorized.is_(False),
        )
        .first()
    )
    if exists:
        return

    root = CourseMaterialChapter(
        subject_id=subject_id,
        parent_id=None,
        title=_DEMO_CHAPTER_ROOT,
        sort_order=10,
        is_uncategorized=False,
    )
    db.add(root)
    db.flush()

    level2 = CourseMaterialChapter(
        subject_id=subject_id,
        parent_id=root.id,
        title=_DEMO_CHAPTER_L2,
        sort_order=0,
        is_uncategorized=False,
    )
    db.add(level2)
    db.flush()

    level3 = CourseMaterialChapter(
        subject_id=subject_id,
        parent_id=level2.id,
        title=_DEMO_CHAPTER_L3,
        sort_order=0,
        is_uncategorized=False,
    )
    db.add(level3)
    print("Created demo course material chapter outline (3 levels).")


def _merge_legacy_demo_class_into_target(db: Session, *, target: Class) -> None:
    """Rename or merge old demo class name into 人工智能1班 so existing installs keep one roster."""
    legacy = db.query(Class).filter(Class.name == _LEGACY_CLASS_NAME).first()
    if not legacy or legacy.id == target.id:
        return
    db.query(Subject).filter(Subject.class_id == legacy.id).update({Subject.class_id: target.id}, synchronize_session=False)
    db.query(Student).filter(Student.class_id == legacy.id).update({Student.class_id: target.id}, synchronize_session=False)
    db.query(User).filter(User.class_id == legacy.id, User.role == UserRole.STUDENT.value).update(
        {User.class_id: target.id},
        synchronize_session=False,
    )
    db.query(CourseEnrollment).filter(CourseEnrollment.class_id == legacy.id).update(
        {CourseEnrollment.class_id: target.id},
        synchronize_session=False,
    )
    db.query(CourseMaterial).filter(CourseMaterial.class_id == legacy.id).update(
        {CourseMaterial.class_id: target.id},
        synchronize_session=False,
    )
    db.query(Homework).filter(Homework.class_id == legacy.id).update({Homework.class_id: target.id}, synchronize_session=False)
    db.delete(legacy)
    db.flush()
    print(f"Merged legacy demo class '{_LEGACY_CLASS_NAME}' into '{_CLASS_NAME}'.")


def _get_or_create_uncategorized_chapter(db: Session, *, subject_id: int) -> CourseMaterialChapter:
    unc = (
        db.query(CourseMaterialChapter)
        .filter(
            CourseMaterialChapter.subject_id == subject_id,
            CourseMaterialChapter.is_uncategorized.is_(True),
        )
        .first()
    )
    if unc:
        return unc
    unc = CourseMaterialChapter(
        subject_id=subject_id,
        parent_id=None,
        title="未分类",
        sort_order=0,
        is_uncategorized=True,
    )
    db.add(unc)
    db.flush()
    return unc


def _seed_llm_elective_course(
    db: Session,
    *,
    teacher: User,
    klass: Class,
    semester: Semester | None,
) -> None:
    """Elective on the same demo class; students self-enroll (no roster-wide auto enrollment)."""
    cal = _demo_llm_elective_calendar(semester)
    course = (
        db.query(Subject)
        .filter(
            Subject.name == _LLM_COURSE_NAME,
            Subject.teacher_id == teacher.id,
            Subject.class_id == klass.id,
        )
        .first()
    )
    if not course:
        course = Subject(
            name=_LLM_COURSE_NAME,
            teacher_id=teacher.id,
            class_id=klass.id,
            semester_id=semester.id if semester else None,
            semester=semester.name if semester else None,
            course_type="elective",
            status="active",
            weekly_schedule=cal["weekly_schedule"],
            course_start_at=cal["course_start_at"],
            course_end_at=cal["course_end_at"],
            course_times=cal["course_times_json"],
            description=cal["description"],
        )
        db.add(course)
        db.flush()
        print(f"Created demo elective course '{_LLM_COURSE_NAME}'.")
    else:
        course.course_type = "elective"
        course.status = "active"
        course.weekly_schedule = cal["weekly_schedule"]
        course.course_start_at = cal["course_start_at"]
        course.course_end_at = cal["course_end_at"]
        course.course_times = cal["course_times_json"]
        course.description = cal["description"]
        print(f"Demo elective '{_LLM_COURSE_NAME}' already exists; refreshed fields.")

    _ensure_demo_subject_llm_binding(
        db,
        subject_id=course.id,
        teacher_id=teacher.id,
        enable_auto_grading=False,
    )

    _seed_demo_grade_weights(db, course=course)
    unc = _get_or_create_uncategorized_chapter(db, subject_id=course.id)

    mat = (
        db.query(CourseMaterial)
        .filter(CourseMaterial.subject_id == course.id, CourseMaterial.title == _LLM_MATERIAL_TITLE)
        .first()
    )
    if not mat:
        mat = CourseMaterial(
            title=_LLM_MATERIAL_TITLE,
            content=_LLM_MATERIAL_CONTENT,
            class_id=klass.id,
            subject_id=course.id,
            created_by=teacher.id,
        )
        db.add(mat)
        db.flush()
        exists_sec = (
            db.query(CourseMaterialSection)
            .filter(CourseMaterialSection.material_id == mat.id, CourseMaterialSection.chapter_id == unc.id)
            .first()
        )
        if not exists_sec:
            db.add(CourseMaterialSection(material_id=mat.id, chapter_id=unc.id, sort_order=0))
        print("Created demo LLM course material.")
    else:
        mat.content = _LLM_MATERIAL_CONTENT

    due = datetime.now(timezone.utc) + timedelta(days=21)
    hw = (
        db.query(Homework)
        .filter(Homework.subject_id == course.id, Homework.title == _LLM_HOMEWORK_TITLE)
        .first()
    )
    if not hw:
        db.add(
            Homework(
                title=_LLM_HOMEWORK_TITLE,
                content=_LLM_HOMEWORK_CONTENT,
                class_id=klass.id,
                subject_id=course.id,
                due_date=due,
                max_score=100,
                grade_precision="integer",
                auto_grading_enabled=False,
                rubric_text=_LLM_RUBRIC_TEXT,
                reference_answer=None,
                response_language="zh-CN",
                allow_late_submission=True,
                late_submission_affects_score=False,
                max_submissions=3,
                created_by=teacher.id,
            )
        )
        print("Created demo LLM homework.")
    else:
        hw.content = _LLM_HOMEWORK_CONTENT
        hw.rubric_text = _LLM_RUBRIC_TEXT
        hw.due_date = hw.due_date or due


def seed_demo_course_bundle(db: Session) -> None:
    """
    Idempotent seed: teacher `teacher`, class 人工智能1班, students stu1–stu5,
    必修课「数据挖掘」+ 选修课「大语言模型」。
    Password for all demo accounts: 111111.
    """
    pwd_hash = get_password_hash(_DEMO_PASSWORD)

    teacher = db.query(User).filter(User.username == "teacher").first()
    if not teacher:
        teacher = User(
            username="teacher",
            hashed_password=pwd_hash,
            real_name=_TEACHER_DISPLAY_NAME,
            role=UserRole.TEACHER.value,
            class_id=None,
            is_active=True,
        )
        db.add(teacher)
        db.flush()
        print("Created demo teacher 'teacher'.")
    else:
        print("Demo teacher 'teacher' already exists.")
    teacher.real_name = _TEACHER_DISPLAY_NAME

    klass = db.query(Class).filter(Class.name == _CLASS_NAME).first()
    if not klass:
        klass = Class(name=_CLASS_NAME, grade=2026)
        db.add(klass)
        db.flush()
        print(f"Created demo class '{_CLASS_NAME}'.")
    else:
        print(f"Demo class '{_CLASS_NAME}' already exists.")
    _merge_legacy_demo_class_into_target(db, target=klass)

    student_specs = [
        ("stu1", "学生一", "13800001001"),
        ("stu2", "学生二", "13800001002"),
        ("stu3", "学生三", "13800001003"),
        ("stu4", "学生四", "13800001004"),
        ("stu5", "学生五", "13800001005"),
    ]
    for uname, display, phone in student_specs:
        u = db.query(User).filter(User.username == uname).first()
        if not u:
            u = User(
                username=uname,
                hashed_password=pwd_hash,
                real_name=display,
                role=UserRole.STUDENT.value,
                class_id=klass.id,
                is_active=True,
            )
            db.add(u)
            db.flush()
            print(f"Created demo student user '{uname}'.")
        else:
            if u.role != UserRole.STUDENT.value:
                u.role = UserRole.STUDENT.value
            if u.class_id != klass.id or not u.is_active:
                u.class_id = klass.id
                u.is_active = True
            u.hashed_password = pwd_hash

        st = db.query(Student).filter(Student.student_no == uname, Student.class_id == klass.id).first()
        if not st:
            db.add(
                Student(
                    name=display,
                    student_no=uname,
                    class_id=klass.id,
                    teacher_id=teacher.id,
                    phone=phone,
                )
            )
            print(f"Created roster row for '{uname}'.")
        else:
            st.teacher_id = teacher.id
            st.phone = phone
            if (st.name or "") != display:
                st.name = display

    semester = (
        db.query(Semester)
        .filter(Semester.name == "2026春季")
        .first()
        or db.query(Semester).order_by(Semester.year.desc(), Semester.id.desc()).first()
    )

    dm_cal = _demo_data_mining_calendar(semester)

    course = (
        db.query(Subject)
        .filter(
            Subject.name == _COURSE_NAME,
            Subject.teacher_id == teacher.id,
            Subject.class_id == klass.id,
        )
        .first()
    )
    if not course:
        course = Subject(
            name=_COURSE_NAME,
            teacher_id=teacher.id,
            class_id=klass.id,
            semester_id=semester.id if semester else None,
            semester=semester.name if semester else None,
            course_type="required",
            status="active",
            weekly_schedule=dm_cal["weekly_schedule"],
            course_start_at=dm_cal["course_start_at"],
            course_end_at=dm_cal["course_end_at"],
            course_times=dm_cal["course_times_json"],
            description=dm_cal["description"],
        )
        db.add(course)
        db.flush()
        print(f"Created demo course '{_COURSE_NAME}'.")
    else:
        if semester and course.semester_id != semester.id:
            course.semester_id = semester.id
            course.semester = semester.name
        course.weekly_schedule = dm_cal["weekly_schedule"]
        course.course_start_at = dm_cal["course_start_at"]
        course.course_end_at = dm_cal["course_end_at"]
        course.course_times = dm_cal["course_times_json"]
        course.description = dm_cal["description"]
        print(f"Demo course '{_COURSE_NAME}' already exists.")

    _ensure_demo_subject_llm_binding(
        db,
        subject_id=course.id,
        teacher_id=teacher.id,
        enable_auto_grading=True,
    )

    _seed_demo_grade_weights(db, course=course)
    _seed_demo_material_chapters(db, subject_id=course.id)

    enrolled = sync_course_enrollments(course, db)
    if enrolled:
        print(f"Synced demo course enrollments: +{enrolled}.")

    hw = (
        db.query(Homework)
        .filter(Homework.subject_id == course.id, Homework.title == _HOMEWORK_TITLE)
        .first()
    )
    due = datetime.now(timezone.utc) + timedelta(days=14)
    if not hw:
        db.add(
            Homework(
                title=_HOMEWORK_TITLE,
                content=_HOMEWORK_CONTENT,
                class_id=klass.id,
                subject_id=course.id,
                due_date=due,
                max_score=100,
                grade_precision="integer",
                auto_grading_enabled=True,
                rubric_text=_RUBRIC_TEXT,
                reference_answer=None,
                response_language="zh-CN",
                allow_late_submission=True,
                late_submission_affects_score=False,
                max_submissions=3,
                created_by=teacher.id,
            )
        )
        print("Created demo homework (first assignment).")
    else:
        hw.content = _HOMEWORK_CONTENT
        hw.max_score = 100
        hw.grade_precision = "integer"
        hw.auto_grading_enabled = True
        hw.rubric_text = _RUBRIC_TEXT
        hw.reference_answer = None
        hw.response_language = "zh-CN"
        hw.due_date = hw.due_date or due
        hw.max_submissions = hw.max_submissions if hw.max_submissions is not None else 3
        print("Demo homework already exists; refreshed text fields.")

    _seed_llm_elective_course(db, teacher=teacher, klass=klass, semester=semester)

    reconcile_student_users_and_roster(db)
    db.commit()
    print("Demo course bundle seed completed.")
