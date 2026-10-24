---
name: mcd-nutritionist
description: 麦当劳营养配餐师——基于麦当劳 MCP 的健身/控卡配餐 Skill。当用户想"在麦当劳搭配一顿健身餐/控卡餐/增肌餐"、询问麦当劳餐品的热量和营养、或要求按蛋白/热量/价格预算约束推荐麦当劳套餐时使用。自动完成：定位门店→拉取实时菜单→合并营养数据→约束求解→价格核验→生成可分享的营养报告卡，用户确认后可继续下单。
agent_created: true
---

# 麦记营养师（McDonald's Nutritionist）

健身、减脂、增肌的人也想吃麦当劳，但不知道一顿下来多少热量、多少蛋白、怎么搭才不超预算。
这个 Skill 把「点餐」变成「解一道营养优化题」：给定约束，在麦当劳实时菜单里求出最优组合。

## 前置条件

1. 已在 open.mcd.cn/mcp 用手机号登录并领取 MCP Token（免费）。
2. WorkBuddy 连接器已按 `mcp-config.example.json` 配置 `mcd-mcp` 并启用：
   - url: `https://mcp.mcd.cn`
   - header: `Authorization: Bearer $MCD_MCP_TOKEN`
   - **Token 只走环境变量/连接器配置，严禁写进任何文件或回复。**

## 工作流程（严格按顺序）

1. **收集约束**（缺项就问，不要编）：
   - 场景：到店自取 / 得来速 / 麦乐送外送
   - 位置或城市（外送还需要配送地址）
   - 热量预算 `max_calories`（kcal）、蛋白目标 `min_protein`（g）
   - 可选：价格预算 `max_price`、单品件数上限 `max_qty`（默认 3）、总件数 `max_items`
2. **定位门店**：
   - 到店：`query-nearby-stores`（beType=1 自取 / 5 得来速，searchType=2 按位置搜）
   - 外送：`delivery-query-addresses` → `delivery-query-stores`（beType=2）
   - 拿到 `storeCode`（得来速还要 `beCode`）
3. **拉菜单**：`query-meals`（storeCode + orderType + beType），得到餐品 code / 名称 / 价格
4. **拉营养**：`list-nutrition-foods`，与菜单按名称对齐；对不上营养数据的项剔除并在结果里说明
5. **合并喂给求解器**：把 items 写成一个 JSON 临时文件（或 stdin），跑
   `python3 skill/scripts/optimize_meal.py --input items.json --mode bulk|cut --report card.md`
   - 用户想「多吃蛋白 / 增肌」→ `bulk`（热量预算内蛋白最大化）
   - 用户想「控卡 / 减脂」→ `cut`（蛋白达标前提下热量最低）
6. **核价**：`calculate-price`（同样参数）核对求解结果的实际价格，与报告卡数字对齐后再展示
7. **输出**：把报告卡 Markdown 原文给用户；钠超过每日参考值 80% 时主动提醒
8. **下单（可选）**：用户明确说"下单/创建订单"才调 `create-order`，下单前必须完整展示餐品、数量、价格，等用户确认

## 模式选择速查

| 用户说法 | 模式 | 目标 |
|---|---|---|
| 增肌 / 多吃蛋白 / 练完补充 | bulk | max 蛋白 s.t. 热量 ≤ 预算 |
| 减脂 / 控卡 / 热量越低越好 | cut | min 热量 s.t. 蛋白 ≥ 目标 |

## 约束字段（输入 JSON）

| 字段 | 类型 | 说明 |
|---|---|---|
| max_calories | number | 热量上限（kcal），bulk 模式主要约束 |
| min_protein | number | 蛋白目标（g），cut 模式硬约束 |
| max_price | number | 价格上限（元） |
| max_qty | number | 同一单品最多几份，默认 3 |
| max_items | number | 总件数上限 |

## 红线

- **Token 不进文件**：items JSON、报告卡、仓库里都不允许出现真实 Token。
- **不自动下单**：`create-order` 前必须展示明细并获得用户明确确认。
- **不编数据**：营养对不上就如实说"该项无营养数据，已剔除"，不要估算一个数填上。
- **报告卡即交付**：最后给用户的必须是 report_card.py 渲染的完整 Markdown，不是口头总结。
