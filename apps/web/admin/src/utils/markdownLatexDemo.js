/**
 * Canonical Markdown + KaTeX demo block for the admin SPA.
 *
 * Shown wherever users can author Markdown so they see **rendered** math alongside
 * supported delimiter rules. Keep in sync with `RichMarkdownDisplay` delimiters
 * (`$...$`, `$$...$$`, `\\(...\\)`, `\\[...\\]`).
 *
 * Pitfall: do **not** wrap formulas in bare `[ ... ]` — KaTeX auto-render will not
 * treat them as math (common confusion after copying from external notes).
 */
export const MARKDOWN_LATEX_EXAMPLE_MARKDOWN = `**Markdown + LaTeX 标准示例**

以下为系统支持的写法（可复制到编辑区）。保存后与下方「预览」使用同一套渲染管线。

- **行内公式（推荐）**：Bayes 公式 \\(P(A\\mid B)=\\dfrac{P(B\\mid A)\\,P(A)}{P(B)}\\)。
- **美元行内**：$E[X]=\\mu$（若正文需写金额，优先用中文「元」，少用半角美元符号以免与公式混淆）。

**独立成行（块级）** 任选其一：

$$
\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}
$$

或 

\\[
\\int_0^1 x^2\\,dx=\\frac{1}{3}
\\]

**常见误区**：不要用单独的英文方括号包裹公式（不要用半角方括号当作公式定界符）——系统不会识别为数学公式。
`
