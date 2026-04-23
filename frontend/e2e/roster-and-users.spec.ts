/**
 * 全链路（浏览器 UI → 后端 API）测试规格 — 默认整包跳过，下一轮实现。
 *
 * 前置（实现时统一约定）：
 * - 后端可访问：VITE_API_BASE_URL 指向测试 API（或同源代理）。
 * - 种子数据：至少管理员 adm、任课教师、两班、花名册、一门绑定班级的课程；或使用专用 seed 接口/脚本。
 *
 * 与 tests/test_roster_enroll_and_batch_class.py 中 API 表 R/B 的对应关系（追溯矩阵）：
 *
 * | ID  | UI 场景 | 关键步骤 | 预期（DB 或 API 可二次断言） |
 * |-----|---------|----------|------------------------------|
 * | E-R1 | 学生无法进课 | 学生登录 → 若路由可见则打开课程管理并尝试触发进课 | 无入口或操作后 403 |
 * | E-R2 | 无关教师无法进课 | 教师 B 登录 → 打开非本人课程（若可深链）→ 从花名册进课 | 403 或无按钮 |
 * | E-R3 | 退选后进课恢复 | 教师 A 登录 → 学生信息/课程学生移除选课 → 课程管理「从花名册进课」勾选该生 → 提交 | 选课出现；学生可再交作业 |
 * | E-R4 | 选修课勾选进课 | 选修课 + 从花名册进课一名学生 | 选课类型为选修（界面或 API） |
 * | E-R5 | 无班级课程 | 管理员创建/保留无 class_id 的课（若 UI 允许）→ 从花名册进课 | 按钮禁用或错误提示 |
 * | E-R6 | 粘贴批量进花名册 | 教师 → 学生信息 → 粘贴批量导入 → 解析预览 → 确认 | POST /students/batch 成功；列表刷新 |
 * | E-B1 | 教师不能批量调班 | 教师登录 → 用户管理（若有）→ 批量调班 | 403 或无入口 |
 * | E-B2 | 管理员批量调班 | 管理员 → 用户管理勾选两名学生 → 批量调班选目标班 → 确认 | POST batch-set-class；两人 class 更新 |
 * | E-B3 | 无效目标班 | 批量调班若 UI 仅下拉则跳过；若有自定义 ID 输入则测 400 | 错误提示 |
 * | E-sync | 同步选课 | 教师 → 学生信息或课程行 → 同步选课名单 | POST sync-enrollments；toast 成功 |
 *
 * 实现建议：data-testid 加在「从花名册进课」「粘贴批量导入」「批量调班」按钮与对话框确认键上，避免 brittle 文本选择器。
 */

import { test } from '@playwright/test'

test.describe.skip('Full-stack: roster enroll, paste import, batch class (Round 2)', () => {
  test('placeholder — implement E-R1 … E-sync per table above', async () => {
    // Intentionally empty until Round 2.
  })
})
