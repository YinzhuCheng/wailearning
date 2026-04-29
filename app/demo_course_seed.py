"""Default demo course data: teacher `teacher`, students stu1–stu5, 数据挖掘 course + first homework."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.course_access import sync_course_enrollments
from app.models import Class, Homework, Semester, Student, Subject, User, UserRole

_DEMO_PASSWORD = "111111"

_CLASS_NAME = "数据挖掘默认班"
_COURSE_NAME = "数据挖掘"

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

_REFERENCE_ANSWER = """参考答案 / 自动评分参考
本次作业没有唯一标准答案。评分时重点关注学生是否完成了 Python 数据分析的基本入门流程，而不是是否完全按照某一种固定格式提交，也不是是否与参考答案逐字一致。

一份较好的答案通常应包括以下内容：

1. 说明使用的 Python 环境

学生可以使用 Anaconda、Jupyter Notebook、VS Code、Google Colab、课程服务器或其他 Python 环境。只要能够运行 Python 代码即可。

示例说明：

我使用 Anaconda 创建 Python 环境，并在 Jupyter Notebook 中完成本次作业。使用的主要库包括 numpy、pandas、matplotlib、seaborn 和 sklearn。

或者：

我使用 Google Colab 完成本次作业，因为它不需要在本地安装环境，可以直接运行 Python 代码。

2. 成功运行基础代码

示例：

print("Hello Python")

3. 成功导入常用库

示例：

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.datasets import load_wine

4. NumPy 和 Pandas 的概念理解

NumPy 主要用于高效的数值计算，特别适合处理数组、矩阵和向量化计算。它是很多科学计算和机器学习库的基础。

Pandas 主要用于表格数据处理，适合进行数据读取、数据清洗、缺失值处理、字段选择、条件筛选、分组统计和简单数据分析。

NumPy 数组更适合处理纯数值型、结构较规则的数据；Pandas DataFrame 更适合处理带有行列标签、字段名称和混合数据类型的表格数据。

5. Pandas 操作解释

df.loc[0:10, ['age', 'score']] 表示选择标签为 0 到 10 的行，以及 age 和 score 两列。

df[df['age'] > 20] 表示筛选出 age 大于 20 的所有行。

df.groupby('gender')['score'].mean() 表示按照 gender 分组，并计算每组 score 的平均值。

6. Wine 数据集加载与 DataFrame 构建

参考代码：

from sklearn.datasets import load_wine
import pandas as pd

wine = load_wine()
df_wine = pd.DataFrame(wine.data, columns=wine.feature_names)
df_wine['target'] = wine.target
df_wine['target_name'] = df_wine['target'].map(lambda i: wine.target_names[i])

df_wine.head()

7. 基础统计分析

示例代码：

features = ['alcohol', 'malic_acid', 'color_intensity', 'hue', 'proline']
df_wine[features].describe()

也可以使用：

df_wine.info()
df_wine['target_name'].value_counts()
df_wine.groupby('target_name')[features].mean()

8. 简单可视化

示例代码一：类别分布图

sns.countplot(data=df_wine, x='target_name')
plt.title('Wine Class Distribution')
plt.show()

示例代码二：散点图

sns.scatterplot(
    data=df_wine,
    x='alcohol',
    y='color_intensity',
    hue='target_name'
)
plt.title('Alcohol vs Color Intensity')
plt.show()

示例代码三：箱线图

sns.boxplot(
    data=df_wine,
    x='target_name',
    y='proline'
)
plt.title('Proline by Wine Class')
plt.show()

学生不必使用完全相同的图表，只要图表与数据分析相关即可。

9. 观察结论示例

学生可以写出类似结论：

第一，不同类别葡萄酒在 alcohol、color_intensity、proline 等特征上存在一定差异，这说明这些特征可能有助于分类。

第二，proline 的数值范围明显大于 alcohol、hue 等特征，因此不同特征之间存在较明显的尺度差异。

第三，从散点图可以看出，部分葡萄酒类别在 alcohol 和 color_intensity 组成的二维空间中有一定区分度，但也可能存在重叠。

第四，不同类别样本数量大致接近，因此本数据集的类别分布相对均衡。

这些结论不要求完全一致，只要能够结合统计结果或图表进行合理解释即可。

10. 标准化函数

参考代码：

import numpy as np

def standardize(x):
    return (x - x.mean()) / x.std()

x = df_wine['alcohol'].to_numpy()
x_std = standardize(x)

print(x_std.mean())
print(x_std.std())

输出结果中，标准化后的均值应接近 0，标准差应接近 1。由于浮点数计算误差，均值可能不是严格等于 0，但应该非常接近 0。

如果学生使用以下方式，也可以接受：

from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
x_std = scaler.fit_transform(df_wine[['alcohol']])

11. 标准化作用解释

标准化可以把不同量纲或不同数值范围的特征调整到相近尺度，减少某些数值范围特别大的特征对模型的过度影响。对于依赖距离计算或梯度优化的模型，标准化通常比较重要。

12. 特征尺度与建模思考题

可接受回答示例：

如果不同特征的数值范围差异很大，模型可能会更重视数值范围大的特征。例如在 KNN 或 K-Means 中，模型需要计算样本之间的距离。如果 proline 的数值远大于 alcohol，那么距离可能主要由 proline 决定，从而削弱其他特征的作用。

很多模型需要标准化或归一化，是因为它可以让不同特征处于相近尺度，使模型训练更稳定，也让距离计算或参数优化更加合理。

对特征尺度敏感的模型包括 KNN、K-Means、SVM、逻辑回归和神经网络等。例如 KNN 根据样本之间的距离进行分类，如果特征尺度差异很大，距离会被大尺度特征主导。

13. 拓展练习参考

拓展练习为选做内容，不做不扣分。

如果学生完成 Iris 数据集分析，可以参考以下代码：

from sklearn.datasets import load_iris

iris = load_iris()
df_iris = pd.DataFrame(iris.data, columns=iris.feature_names)
df_iris['target'] = iris.target
df_iris['target_name'] = df_iris['target'].map(lambda i: iris.target_names[i])

df_iris.groupby('target_name').mean()

sns.boxplot(data=df_iris, x='target_name', y='petal length (cm)')
plt.show()

合理结论示例：

Iris 数据集中，petal length 和 petal width 对不同类别的区分比较明显，尤其 setosa 与其他类别差异较大。

如果学生选择自选 CSV 数据集，只要能够完成读取、基本查看、简单图表和简短分析，也可以给予加分。

总体评分说明：

本次作业是入门作业，不要求学生完成复杂建模，也不要求图表非常美观。只要学生能够完成基本环境运行、数据读取、统计分析、简单可视化、标准化理解和基本思考题，就应给予较高分数。对于认真完成主要任务的学生，建议分数集中在 85 分以上。拓展练习只作为加分项，不做不扣分。"""


def seed_demo_course_bundle(db: Session) -> None:
    """
    Idempotent seed: teacher `teacher`, class, students stu1–stu5, course 数据挖掘, first homework.
    Password for all demo accounts: 111111.
    """
    pwd_hash = get_password_hash(_DEMO_PASSWORD)

    teacher = db.query(User).filter(User.username == "teacher").first()
    if not teacher:
        teacher = User(
            username="teacher",
            hashed_password=pwd_hash,
            real_name="演示教师",
            role=UserRole.TEACHER.value,
            class_id=None,
            is_active=True,
        )
        db.add(teacher)
        db.flush()
        print("Created demo teacher 'teacher'.")
    else:
        print("Demo teacher 'teacher' already exists.")

    klass = db.query(Class).filter(Class.name == _CLASS_NAME).first()
    if not klass:
        klass = Class(name=_CLASS_NAME, grade=2026)
        db.add(klass)
        db.flush()
        print(f"Created demo class '{_CLASS_NAME}'.")
    else:
        print(f"Demo class '{_CLASS_NAME}' already exists.")

    student_specs = [
        ("stu1", "学生一"),
        ("stu2", "学生二"),
        ("stu3", "学生三"),
        ("stu4", "学生四"),
        ("stu5", "学生五"),
    ]
    for uname, display in student_specs:
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
        elif u.class_id != klass.id or not u.is_active:
            u.class_id = klass.id
            u.is_active = True
            u.hashed_password = pwd_hash

        st = db.query(Student).filter(Student.student_no == uname, Student.class_id == klass.id).first()
        if not st:
            db.add(Student(name=display, student_no=uname, class_id=klass.id, teacher_id=teacher.id))
            print(f"Created roster row for '{uname}'.")

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
            description="数据挖掘课程（演示种子数据）。",
        )
        db.add(course)
        db.flush()
        print(f"Created demo course '{_COURSE_NAME}'.")
    else:
        if semester and course.semester_id != semester.id:
            course.semester_id = semester.id
            course.semester = semester.name
        print(f"Demo course '{_COURSE_NAME}' already exists.")

    enrolled = sync_course_enrollments(course, db)
    if enrolled:
        print(f"Synced demo course enrollments: +{enrolled}.")

    hw = (
        db.query(Homework)
        .filter(Homework.subject_id == course.id, Homework.title == _HOMEWORK_TITLE)
        .first()
    )
    if not hw:
        db.add(
            Homework(
                title=_HOMEWORK_TITLE,
                content=_HOMEWORK_CONTENT,
                class_id=klass.id,
                subject_id=course.id,
                due_date=None,
                max_score=100,
                grade_precision="integer",
                auto_grading_enabled=True,
                rubric_text=_RUBRIC_TEXT,
                reference_answer=_REFERENCE_ANSWER,
                response_language="zh-CN",
                allow_late_submission=True,
                late_submission_affects_score=False,
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
        hw.reference_answer = _REFERENCE_ANSWER
        hw.response_language = "zh-CN"
        print("Demo homework already exists; refreshed text fields.")

    db.commit()
    print("Demo course bundle seed completed.")
