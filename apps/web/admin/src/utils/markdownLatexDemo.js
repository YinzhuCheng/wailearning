/**
 * Canonical Markdown + KaTeX + semantic-card demo block for the admin SPA.
 *
 * Shown wherever users can author Markdown so they see rendered cards, images,
 * and math using the same controlled renderer as published content.
 */
export const DEMO_MARKDOWN_IMAGE_PATH = '/markdown-demo-card-image.svg'
export const MARKDOWN_IMAGE_EXAMPLE_MARKDOWN = `![课程卡片与插图示意图](${DEMO_MARKDOWN_IMAGE_PATH})`

export const MARKDOWN_LATEX_EXAMPLE_MARKDOWN = `**Markdown + LaTeX + Card 标准示例**

以下示例展示当前站点支持的增强渲染：你可以直接写 Markdown 内容，并使用 \`:::\` 卡片块获得更清晰的视觉层级。

:::example 示例用法
1. 价格、配额、返回示例适合放进卡片。
2. 普通正文继续使用标准 Markdown。
3. 卡片内部依然支持 **粗体**、列表、\`行内代码\`、图片和公式。
:::

:::pricing 价格说明
- 输入：**$5 / M Tokens**
- 输出：**$30 / M Tokens**
- Web Search：**$0.01 / request**
:::

:::note 插图示例
下图使用当前系统支持的标准 Markdown 图片语法插入，图片源是站点内置静态 SVG。

${MARKDOWN_IMAGE_EXAMPLE_MARKDOWN}
:::

:::tip 公式示例
- 行内公式：Bayes 公式 \\(P(A\\mid B)=\\dfrac{P(B\\mid A)P(A)}{P(B)}\\)
- 独立公式：

$$
\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}
$$
:::

:::warning 兼容性说明
- 该卡片效果依赖当前文档站的受控 Markdown 渲染器与主题 CSS。
- 如果以后更换渲染环境，应继续保留“语义块 + 全局样式”的做法，而不是回退到零散的内联样式。
:::

:::danger 常见误区
- 不要把样式直接写死在每一段 HTML 里。
- 不要用单独的英文方括号 \`[ ... ]\` 冒充数学公式定界符。
:::
`
