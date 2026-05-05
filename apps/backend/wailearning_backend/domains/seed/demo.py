"""Default demo data: teacher `teacher`, class 人工智能1班, students stu1–stu5.

- **必修课**「数据挖掘」：教师按班级花名册统一入课（`sync_course_enrollments`），含演示章节、若干带正文的课程资料与第一次作业；默认可有部分学生已提交且含教师评分（用于演示列表与成绩）。
- **选修课**「大语言模型」：同班开设；默认种子会为全班写入选课记录（与必修课一致），便于首次部署后师生立即可用；含阅读材料与入门作业，默认可有部分学生已提交。

若数据库中已有**通过校验且可用于评分**的全局 LLM 端点预设（`ensure_schema_updates` 会写入内置默认预设），本种子会为演示必修课/选修课**幂等绑定**首个可用预设（必修课同时 `is_enabled=True` 以配合自动评分作业）；否则不写入端点，由管理员或教师在课程 LLM 配置中手动选择。

演示必修课作业**不包含参考答案**（`reference_answer` 为空）。必修课资料区含三层演示章节，并在最深层级挂载若干 Markdown 讲义。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from apps.backend.wailearning_backend.core.auth import get_password_hash
from apps.backend.wailearning_backend.domains.courses.access import sync_course_enrollments
from apps.backend.wailearning_backend.llm_grading import refresh_submission_summary
from apps.backend.wailearning_backend.db.models import (
    Class,
    CourseEnrollment,
    CourseEnrollmentBlock,
    CourseExamWeight,
    CourseGradeScheme,
    CourseLLMConfig,
    CourseLLMConfigEndpoint,
    CourseMaterial,
    CourseMaterialChapter,
    CourseMaterialSection,
    Gender,
    Homework,
    HomeworkAttempt,
    HomeworkScoreCandidate,
    HomeworkSubmission,
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
_LLM_COURSE_DESCRIPTION = (
    "全校默认选修示例：大语言模型基础与应用入门。完成本课需由学生在「我的课程」中自主选课；"
    "内容包含提示工程简介与一次实践作业。"
)
_LLM_WEEKLY = "每周四 15:00–17:00（选修，以教务通知为准）"
_LLM_MATERIAL_TITLE = "【选修】大语言模型：课程说明与阅读材料"
_LLM_MATERIAL_CONTENT = """## 欢迎选修「大语言模型」

本课程为**选修课**。在默认演示数据中，系统已为全班预置选课记录，便于首次部署后直接进入作业与资料；生产环境可自行调整选课策略。

### 学习目标

- 了解大语言模型的基本能力与局限；
- 掌握提示（Prompt）书写的基本结构；
- 完成一次简短的实践作业。

### 课堂纪律与学术诚信

- 生成式内容须标注用途，禁止将模型输出冒充本人未理解的原创结论；
- 涉及隐私、考试题目或未公开数据时，**不得**粘贴到外部模型；
- 教师保留对异常相似提交进行核查的权利。

### 什么是大语言模型（课堂版定义）

大语言模型（LLM）是在海量文本上训练出的概率模型，给定前文（或指令）后预测下一个词元序列。它擅长**语言重组、摘要草稿、头脑风暴**，但可能出现事实幻觉、遗漏约束或与领域规范不符的输出，因此需要人在回路中审阅。

### 提示工程速记：CRISP 结构

在作业中你会被要求写「新闻摘要」提示模板，可先记住下列骨架（可自行增删）：

1. **Context**：角色与受众（例如「你是新闻编辑，面向普通读者」）；
2. **Request**：任务与输出形式（「用 5 条要点总结下文」）；
3. **Input**：粘贴待处理文本的占位；
4. **Style**：语气、长度、是否保留人名地名；
5. **Safety**：拒绝编造数字、若原文缺失信息则明确写「原文未提及」。

### 推荐阅读

1. 课程通知中的 **API 与配额** 说明；
2. 课前可预习「提示工程」基础概念与「幻觉」案例；
3. 完成阅读后，可直接打开「提示工程小练习」作业，按条目提交即可。
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
_COURSE_WEEKLY_SCHEDULE = "每周二 14:00–16:00（教室以教务通知为准）"
_COURSE_TIMES = "第1–16周；实验课与讨论课穿插安排，请关注课程群通知。"
_COURSE_DESCRIPTION = (
    "数据挖掘入门与实践（演示课程）。涵盖 Python 数据分析基础、特征与可视化、"
    "简单预处理与经典数据集探索；平时作业与课堂表现结合考核。"
)

# Demo material outline: three chapter nodes (depth 3), idempotent by root title.
_DEMO_CHAPTER_ROOT = "【演示】第一单元：导论与数据概览"
_DEMO_CHAPTER_L2 = "【演示】第一节：Python 环境与常用库"
_DEMO_CHAPTER_L3 = "【演示】1.1 课程资料与拓展阅读"

_DEMO_MATERIAL_INTRO_TITLE = "【讲义】数据挖掘绪论：问题类型与典型流程"
_DEMO_MATERIAL_INTRO_CONTENT = """## 本讲定位

本讲义配合「数据挖掘」演示课程第一单元，帮助你建立**问题类型—数据—方法—评估**的整体心智模型。阅读时间约 15–25 分钟。

## 什么是数据挖掘

数据挖掘（Data Mining）是从大量数据中**自动或半自动**发现有用模式、规律或异常的过程。它与统计分析、机器学习、数据库技术高度交叉，但更强调**面向业务或科研问题**的可操作产出。

## 常见任务类型（按输出划分）

| 类型 | 典型问题 | 常见算法/思路 |
|------|----------|----------------|
| 分类 | 给定特征，预测离散标签 | 逻辑回归、决策树、随机森林、梯度提升 |
| 回归 | 预测连续数值 | 线性回归、岭回归、树模型回归 |
| 聚类 | 无标签，发现群组结构 | K-Means、层次聚类、DBSCAN |
| 关联规则 | 购物篮、共现模式 | Apriori、FP-Growth |
| 异常检测 | 发现离群或欺诈 | 孤立森林、基于密度的方法 |

## 典型流程（CRISP-DM 简化版）

1. **业务理解**：明确目标、约束与成功标准。
2. **数据理解**：数据来源、字段含义、缺失与噪声。
3. **数据准备**：清洗、特征构造、训练/验证划分。
4. **建模**：选择模型与基线，迭代对比。
5. **评估**：用预留数据与业务指标检验，避免仅看训练误差。
6. **部署与维护**：监控漂移、定期重训与文档化。

## 与后续实验的关系

后续讲义将用 **Python + Pandas + 可视化** 完成小型数据集的描述性统计；第一次作业要求你在本环境中跑通 **Wine** 数据集的基础探索。建议你在阅读本讲后，打开下一篇「Python 数据分析栈」对照自己的环境逐项自检。
"""

_DEMO_MATERIAL_PYTHON_TITLE = "【讲义】Python 数据分析栈与环境自检"
_DEMO_MATERIAL_PYTHON_CONTENT = """## 目标

确认本机或在线环境能稳定使用 **NumPy / Pandas / Matplotlib / Seaborn / scikit-learn**，并理解各库在分析流水线中的分工。

## 各库在做什么

- **NumPy**：同质数值数组、向量化运算、线性代数与随机数；是许多库的底层。
- **Pandas**：带索引的表格（`DataFrame` / `Series`）、对齐、分组聚合、时间序列。
- **Matplotlib**：底层绘图 API，可控性强。
- **Seaborn**：在 Matplotlib 之上封装统计图形（分布、关系、分类图）。
- **scikit-learn**：经典机器学习算法、预处理、管道与评估指标。

## 最小自检代码（建议在 Notebook 或 `.py` 中运行）

```python
import sys
import numpy as np
import pandas as pd
import matplotlib
import seaborn as sns
import sklearn

print("python", sys.version.split()[0])
print("numpy", np.__version__)
print("pandas", pd.__version__)
print("matplotlib", matplotlib.__version__)
print("seaborn", sns.__version__)
print("sklearn", sklearn.__version__)
```

若某行报错，请记录完整 traceback；第一次作业鼓励把**环境说明 + 排错过程**写进报告。

## Pandas 三板斧（与作业直接相关）

```python
import pandas as pd

df = pd.read_csv("example.csv")  # 或作业中的 DataFrame 构造方式
df.head()
df.info()
df.describe()
```

- `head`：快速查看前几行与列名。
- `info`：每列类型与非空数量。
- `describe`：数值列的计数、均值、标准差、分位数等。

## 阅读建议

1. 先跑通自检代码，再进入 Wine 数据集探索；
2. 养成「小步运行、即时打印形状 `df.shape`」的习惯；
3. 可视化时注意坐标轴标签与图例，便于助教或自动评分系统理解你的结论。
"""

_DEMO_MATERIAL_WINE_TITLE = "【讲义】Wine 数据集：描述性统计与可视化入门"
_DEMO_MATERIAL_WINE_CONTENT = """## 数据集简介

**Wine** 是 scikit-learn 内置的多分类数据集，样本为葡萄酒化学成分测量值，标签为 cultivar 类别。适合练习 **加载 → DataFrame → 描述统计 → 简单可视化**。

## 加载与整理

```python
from sklearn.datasets import load_wine
import pandas as pd

raw = load_wine(as_frame=True)
df = raw.frame  # 已包含 target 名称的 DataFrame
df.head()
```

若使用 `load_wine()` 返回的 `Bunch`，可手动组装：

```python
from sklearn.datasets import load_wine
import pandas as pd

bunch = load_wine()
df = pd.DataFrame(bunch.data, columns=bunch.feature_names)
df["target"] = bunch.target
df["target_name"] = df["target"].map(dict(enumerate(bunch.target_names)))
```

## 建议的探索步骤

1. `df.shape`、`df.columns`：确认维度与字段。
2. `df["target_name"].value_counts()`：类别是否均衡。
3. 对 `alcohol`、`malic_acid`、`color_intensity` 等列做 `describe()`。
4. 任选两列画散点图，用颜色区分类别（Seaborn `scatterplot` 或 Matplotlib）。
5. 用一两句话写出观察：哪些特征在不同类别间差异更明显。

## 常见易错点

- 把特征与标签混在一步里做标准化，导致信息泄漏；作业要求先理解「对哪些列做标准化」。
- 只贴图不写结论；数据挖掘强调**证据与解释**配套。
- 忽略 `random_state` 与可复现性；课堂演示建议固定种子。

## 延伸阅读（选读）

- scikit-learn User Guide 中关于预处理与模型评估的章节；
- 第一次作业评分量表中的「宽松评分原则」——重视过程与可解释性。
"""


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


def _ensure_demo_material_outline_leaf(db: Session, *, subject_id: int) -> CourseMaterialChapter:
    """Return the deepest demo chapter (L3), creating the 3-level outline when missing."""
    root = (
        db.query(CourseMaterialChapter)
        .filter(
            CourseMaterialChapter.subject_id == subject_id,
            CourseMaterialChapter.title == _DEMO_CHAPTER_ROOT,
            CourseMaterialChapter.is_uncategorized.is_(False),
        )
        .first()
    )
    if not root:
        root = CourseMaterialChapter(
            subject_id=subject_id,
            parent_id=None,
            title=_DEMO_CHAPTER_ROOT,
            sort_order=10,
            is_uncategorized=False,
        )
        db.add(root)
        db.flush()
        print("Created demo course material chapter outline (root).")

    level2 = (
        db.query(CourseMaterialChapter)
        .filter(
            CourseMaterialChapter.subject_id == subject_id,
            CourseMaterialChapter.parent_id == root.id,
            CourseMaterialChapter.title == _DEMO_CHAPTER_L2,
            CourseMaterialChapter.is_uncategorized.is_(False),
        )
        .first()
    )
    if not level2:
        level2 = CourseMaterialChapter(
            subject_id=subject_id,
            parent_id=root.id,
            title=_DEMO_CHAPTER_L2,
            sort_order=0,
            is_uncategorized=False,
        )
        db.add(level2)
        db.flush()
        print("Created demo course material chapter outline (level 2).")

    level3 = (
        db.query(CourseMaterialChapter)
        .filter(
            CourseMaterialChapter.subject_id == subject_id,
            CourseMaterialChapter.parent_id == level2.id,
            CourseMaterialChapter.title == _DEMO_CHAPTER_L3,
            CourseMaterialChapter.is_uncategorized.is_(False),
        )
        .first()
    )
    if not level3:
        level3 = CourseMaterialChapter(
            subject_id=subject_id,
            parent_id=level2.id,
            title=_DEMO_CHAPTER_L3,
            sort_order=0,
            is_uncategorized=False,
        )
        db.add(level3)
        db.flush()
        print("Created demo course material chapter outline (level 3).")

    return level3


def _ensure_material_in_chapter(
    db: Session,
    *,
    title: str,
    content: str,
    class_id: int,
    subject_id: int,
    created_by: int,
    chapter: CourseMaterialChapter,
    sort_order: int,
) -> CourseMaterial:
    """Upsert material body by title and ensure one section link under chapter."""
    mat = db.query(CourseMaterial).filter(CourseMaterial.subject_id == subject_id, CourseMaterial.title == title).first()
    if not mat:
        mat = CourseMaterial(
            title=title,
            content=content,
            class_id=class_id,
            subject_id=subject_id,
            created_by=created_by,
        )
        db.add(mat)
        db.flush()
    else:
        mat.content = content
        mat.class_id = class_id
        mat.subject_id = subject_id
        mat.created_by = created_by

    link = (
        db.query(CourseMaterialSection)
        .filter(CourseMaterialSection.material_id == mat.id, CourseMaterialSection.chapter_id == chapter.id)
        .first()
    )
    if not link:
        db.add(CourseMaterialSection(material_id=mat.id, chapter_id=chapter.id, sort_order=sort_order))
    else:
        link.sort_order = sort_order
    return mat


def _ensure_demo_subject_materials(
    db: Session,
    *,
    course: Subject,
    teacher_id: int,
    leaf_chapter: CourseMaterialChapter,
) -> None:
    """Idempotent Markdown materials under the demo leaf chapter."""
    assert course.class_id is not None
    _ensure_material_in_chapter(
        db,
        title=_DEMO_MATERIAL_INTRO_TITLE,
        content=_DEMO_MATERIAL_INTRO_CONTENT,
        class_id=course.class_id,
        subject_id=course.id,
        created_by=teacher_id,
        chapter=leaf_chapter,
        sort_order=0,
    )
    _ensure_material_in_chapter(
        db,
        title=_DEMO_MATERIAL_PYTHON_TITLE,
        content=_DEMO_MATERIAL_PYTHON_CONTENT,
        class_id=course.class_id,
        subject_id=course.id,
        created_by=teacher_id,
        chapter=leaf_chapter,
        sort_order=1,
    )
    _ensure_material_in_chapter(
        db,
        title=_DEMO_MATERIAL_WINE_TITLE,
        content=_DEMO_MATERIAL_WINE_CONTENT,
        class_id=course.class_id,
        subject_id=course.id,
        created_by=teacher_id,
        chapter=leaf_chapter,
        sort_order=2,
    )


def _seed_demo_homework_summaries(
    db: Session,
    *,
    klass: Class,
    teacher_id: int,
    dm_homework: Homework,
    llm_homework: Homework,
) -> None:
    """
    Idempotent: a few students already submitted with varied quality and teacher scores.

    Uses teacher score candidates so the UI shows grades without running auto-grading.
    """
    now = datetime.now(timezone.utc)
    dm_specs: list[tuple[str, str, float, str, bool]] = [
        (
            "stu1",
            "## 数据挖掘第一次作业（演示提交：较完整）\n\n"
            "### 一、环境\n- Python 3.11，VS Code + venv。\n"
            "### 二、概念简述\n"
            "- NumPy：底层数值数组与向量化。\n- Pandas：表格与 groupby。\n"
            "### 三、Wine 探索摘要\n"
            "已用 `load_wine(as_frame=True)` 得到 DataFrame；`describe()` 显示 alcohol 等特征尺度差异大；"
            "按 target_name 分组后 color_intensity 的均值在不同类别间差距明显。\n"
            "### 四、标准化\n"
            "对 alcohol 手写 z-score，标准化后均值约 0、标准差约 1。\n"
            "### 五、思考题\n"
            "KNN 对尺度敏感：未标准化时大数值特征会主导距离。\n",
            91.0,
            "结构清楚，Wine 探索与标准化到位；思考题简洁准确。",
            False,
        ),
        (
            "stu2",
            "环境：Anaconda。导入了 numpy pandas matplotlib seaborn sklearn。\n"
            "Wine：load_wine 放进 DataFrame，head 和 describe 看了。\n"
            "画了一张 alcohol 的直方图。\n"
            "标准化：用了 StandardScaler 对 alcohol 列。\n"
            "思考题：SVM 会受特征大小影响。\n",
            84.0,
            "主要任务完成；分析略简但结论方向正确。",
            False,
        ),
        (
            "stu3",
            "NumPy 是数组，Pandas 是表。Wine 数据看了前几行。\n"
            "标准化公式写了一下但没给运行结果截图。\n"
            "思考题没写完。\n",
            68.0,
            "基础部分有触及；Wine 与标准化证据不足，思考题未完成。",
            False,
        ),
        (
            "stu4",
            "抱歉迟交了。环境配了很久，最后 Colab 跑通。\n"
            "Wine：`df.groupby('target_name')['alcohol'].mean()` 做了。\n"
            "图：seaborn pairplot 太大只截了部分。\n"
            "标准化：用 sklearn 对多列做了 fit_transform。\n"
            "迟交说明：家里网络不稳定。\n",
            76.0,
            "内容尚可；迟交按课程说明处理，表达与结构一般。",
            True,
        ),
    ]
    llm_specs: list[tuple[str, str, float, str, bool]] = [
        (
            "stu1",
            "### 提示工程\n用自然语言指令约束模型输出；清晰指令能减少跑题。\n\n"
            "### 新闻摘要模板\n"
            "1) 角色：新闻编辑；2) 任务：5 条要点；3) 输入：{NEWS}；"
            "4) 约束：不得编造；5) 风格：中文、客观。\n\n"
            "### 风险\n"
            "- 隐私泄露；- 不加核实当作事实来源。\n",
            93.0,
            "三部分完整，模板结构清楚，风险意识到位。",
            False,
        ),
        (
            "stu2",
            "提示工程就是写 prompt。模板：把新闻贴进去让模型总结。\n"
            "风险：不要太依赖 AI。\n",
            72.0,
            "要点有提到；模板与风险部分偏简略。",
            False,
        ),
        (
            "stu5",
            "1) 提示工程：给例子和格式。2) 模板：随便写写。3) 风险：无。\n",
            54.0,
            "完成度低；风险与模板几乎未展开。",
            False,
        ),
    ]

    def _apply(
        homework: Homework,
        rows: list[tuple[str, str, float, str, bool]],
    ) -> None:
        for student_no, body, score, comment, is_late in rows:
            st = db.query(Student).filter(Student.student_no == student_no, Student.class_id == klass.id).first()
            if not st:
                continue
            sub = (
                db.query(HomeworkSubmission)
                .filter(HomeworkSubmission.homework_id == homework.id, HomeworkSubmission.student_id == st.id)
                .first()
            )
            submitted_at = now - timedelta(days=2 if not is_late else 1)
            if not sub:
                sub = HomeworkSubmission(
                    homework_id=homework.id,
                    student_id=st.id,
                    subject_id=homework.subject_id,
                    class_id=homework.class_id,
                    content=body,
                    used_llm_assist=False,
                    submitted_at=submitted_at,
                )
                db.add(sub)
                db.flush()
            else:
                sub.subject_id = homework.subject_id
                sub.class_id = homework.class_id

            att = (
                db.query(HomeworkAttempt)
                .filter(
                    HomeworkAttempt.homework_id == homework.id,
                    HomeworkAttempt.student_id == st.id,
                    HomeworkAttempt.submission_summary_id == sub.id,
                )
                .order_by(HomeworkAttempt.submitted_at.desc(), HomeworkAttempt.id.desc())
                .first()
            )
            if not att:
                att = HomeworkAttempt(
                    homework_id=homework.id,
                    student_id=st.id,
                    subject_id=homework.subject_id,
                    class_id=homework.class_id,
                    submission_summary_id=sub.id,
                    content=body,
                    is_late=is_late,
                    counts_toward_final_score=True,
                    used_llm_assist=False,
                    submission_mode="full",
                    submitted_at=submitted_at,
                )
                db.add(att)
                db.flush()
            else:
                att.content = body
                att.is_late = is_late
                att.submitted_at = submitted_at
                att.counts_toward_final_score = True

            sub.latest_attempt_id = att.id
            refresh_submission_summary(db, sub)

            has_teacher = (
                db.query(HomeworkScoreCandidate)
                .filter(
                    HomeworkScoreCandidate.attempt_id == att.id,
                    HomeworkScoreCandidate.source == "teacher",
                )
                .first()
            )
            if not has_teacher:
                db.add(
                    HomeworkScoreCandidate(
                        attempt_id=att.id,
                        homework_id=homework.id,
                        student_id=st.id,
                        source="teacher",
                        score=float(score),
                        comment=comment,
                        created_by=teacher_id,
                    )
                )
                db.flush()
            refresh_submission_summary(db, sub)

    _apply(dm_homework, dm_specs)
    _apply(llm_homework, llm_specs)


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


def _sync_demo_elective_enrollments_for_class(db: Session, *, course: Subject, klass: Class) -> int:
    """
    Ensure every roster student in the demo class is enrolled in the demo elective.

    Clears enrollment blocks for this course so login-time student sync cannot suppress the row.
    """
    if not course.class_id:
        return 0
    class_students = db.query(Student).filter(Student.class_id == klass.id).all()
    existing = {
        row.student_id
        for row in db.query(CourseEnrollment).filter(CourseEnrollment.subject_id == course.id).all()
    }
    created = 0
    for st in class_students:
        db.query(CourseEnrollmentBlock).filter(
            CourseEnrollmentBlock.subject_id == course.id,
            CourseEnrollmentBlock.student_id == st.id,
        ).delete(synchronize_session=False)
        if st.id in existing:
            continue
        db.add(
            CourseEnrollment(
                subject_id=course.id,
                student_id=st.id,
                class_id=course.class_id,
                enrollment_type="elective",
                can_remove=True,
            )
        )
        created += 1
    if created:
        db.flush()
    return created


def _seed_llm_elective_course(
    db: Session,
    *,
    teacher: User,
    klass: Class,
    semester: Semester | None,
) -> Subject:
    """Elective on the same demo class; seed also adds roster enrollments for the demo bundle."""
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
            weekly_schedule=_LLM_WEEKLY,
            course_times="选修课：请自主选课；课次以教务与课程群通知为准。",
            description=_LLM_COURSE_DESCRIPTION,
        )
        db.add(course)
        db.flush()
        print(f"Created demo elective course '{_LLM_COURSE_NAME}'.")
    else:
        course.course_type = "elective"
        course.status = "active"
        course.weekly_schedule = _LLM_WEEKLY
        course.description = _LLM_COURSE_DESCRIPTION
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

    return course


def seed_demo_course_bundle(db: Session) -> None:
    """
    Idempotent seed: teacher `teacher`, class 人工智能1班, students stu1–stu5,
    必修课「数据挖掘」+ 选修课「大语言模型」（全班默认已选课）。
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
                    gender=Gender.MALE,
                    class_id=klass.id,
                    teacher_id=teacher.id,
                    phone=phone,
                )
            )
            print(f"Created roster row for '{uname}'.")
        else:
            st.teacher_id = teacher.id
            st.phone = phone
            if st.gender is None:
                st.gender = Gender.MALE
            if (st.name or "") != display:
                st.name = display

    semester = (
        db.query(Semester)
        .filter(Semester.name == "2026春季")
        .first()
        or db.query(Semester).order_by(Semester.year.desc(), Semester.id.desc()).first()
    )

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
            weekly_schedule=_COURSE_WEEKLY_SCHEDULE,
            course_times=_COURSE_TIMES,
            description=_COURSE_DESCRIPTION,
        )
        db.add(course)
        db.flush()
        print(f"Created demo course '{_COURSE_NAME}'.")
    else:
        if semester and course.semester_id != semester.id:
            course.semester_id = semester.id
            course.semester = semester.name
        course.weekly_schedule = _COURSE_WEEKLY_SCHEDULE
        course.course_times = _COURSE_TIMES
        course.description = _COURSE_DESCRIPTION
        print(f"Demo course '{_COURSE_NAME}' already exists.")

    _ensure_demo_subject_llm_binding(
        db,
        subject_id=course.id,
        teacher_id=teacher.id,
        enable_auto_grading=True,
    )

    _seed_demo_grade_weights(db, course=course)
    leaf = _ensure_demo_material_outline_leaf(db, subject_id=course.id)
    _ensure_demo_subject_materials(db, course=course, teacher_id=teacher.id, leaf_chapter=leaf)

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
        hw = Homework(
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
        db.add(hw)
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
    db.flush()

    llm_course = _seed_llm_elective_course(db, teacher=teacher, klass=klass, semester=semester)
    llm_hw = (
        db.query(Homework)
        .filter(Homework.subject_id == llm_course.id, Homework.title == _LLM_HOMEWORK_TITLE)
        .first()
    )
    if llm_hw:
        _seed_demo_homework_summaries(
            db,
            klass=klass,
            teacher_id=teacher.id,
            dm_homework=hw,
            llm_homework=llm_hw,
        )
    n_elective = _sync_demo_elective_enrollments_for_class(db, course=llm_course, klass=klass)
    n_elective = _sync_demo_elective_enrollments_for_class(db, course=llm_course, klass=klass)
    if n_elective:
        print(f"Synced demo elective enrollments: +{n_elective}.")

    reconcile_student_users_and_roster(db)
    db.commit()
    print("Demo course bundle seed completed.")
