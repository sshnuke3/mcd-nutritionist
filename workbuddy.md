# WorkBuddy 开发上下文导出 · workbuddy.md

本文件记录「麦记营养师」使用**腾讯 WorkBuddy** 开发的过程上下文，用于麦当劳程序员创意开发大赛 WorkBuddy 联动奖励的核验。

## 项目信息

| 项 | 值 |
|---|---|
| 项目名称 | 麦记营养师（mcd-nutritionist） |
| 赛事 | 麦当劳程序员创意开发大赛（1024 程序员节） |
| 开发日期 | 2026-10-24 |
| 开发工具 | 腾讯 WorkBuddy（本次赛事官方合作伙伴） |

## 开发过程记录（WorkBuddy 会话摘要）

### 1. MCP 接入

用户提供麦当劳 MCP Token 后，按官方《WorkBuddy 开发指南》在 WorkBuddy 中配置自定义连接器 `mcd-mcp`：

- type: `streamablehttp`，url: `https://mcp.mcd.cn`
- header: `Authorization: Bearer <MCP Token>`

Token 仅保存于本地安全位置（`~/.config/mcd-mcp/token`，600 权限），**未进入任何仓库文件**。

### 2. MCP 能力探测

在 WorkBuddy 内编写并运行探测脚本，完成 MCP 握手（协议版本 `2025-06-18`，服务端 `mcd-mcp` v1.0.0）：

- `initialize` → `notifications/initialized` → `tools/list`
- 获取服务端全部 **35 个工具**的 schema，作为 Skill 主题设计依据

### 3. 主题确定

官方 README 建议方向为「套餐推荐助手、麦门省钱助手、麦麦活动推荐助手」，官方 Issue 示例为「麦当劳营养膳食专家」。结合探测到的工具链（`query-meals` + `list-nutrition-foods` + `calculate-price`），选定差异化方向：**营养约束配餐**。

### 4. 核心开发（全部在 WorkBuddy 内完成）

- `skill/scripts/optimize_meal.py`：零依赖纯 Python 约束求解器
  - `bulk` 增肌模式：热量预算内蛋白最大化
  - `cut` 减脂模式：蛋白达标前提下总热量最低
  - 算法：多种子贪心（蛋白/热量密度、蛋白/价格密度、绝对蛋白量）+ 局部爬山 + 多单位「破坏-修复」局部搜索
- `skill/scripts/report_card.py`：营养报告卡 Markdown 渲染器
- **调试过程**：首轮测试发现纯贪心在价格约束下陷入局部最优（3 份麦乐鸡 + 玉米杯打满 ¥50，漏掉更优的 2 份板烧鸡腿堡 50g 蛋白 / ¥43）；在 WorkBuddy 中定位问题后引入多种子与多单位破坏-修复，求解结果达到已知最优
- `tests/run_tests.py`：两种模式的离线断言测试，全部通过

### 5. 参赛文件与发布

在 WorkBuddy 内完成 README.md、MCP_INTEGRATION.md、mcp-config.example.json（仅环境变量占位符）、CONTEST_DECLARATION.md（官方原文未改动）的撰写，创建 GitHub 公开仓库并提交参赛 Issue。

## 本次开发使用的 WorkBuddy 能力

- 文件读写与代码编辑
- 命令行执行（Python 3.13 运行求解器与自测）
- 自定义连接器（MCP）配置与工具调用
- Skill 开发（`skill/SKILL.md`）

## 真实性承诺

本文件所述开发过程真实发生于腾讯 WorkBuddy 客户端；本项目由参赛者使用 WorkBuddy 辅助开发完成。
