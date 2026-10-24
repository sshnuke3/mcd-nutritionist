# 麦记营养师 · McDonald's Nutritionist

> 身材管控期也想吃麦当劳？告诉它你的热量预算和蛋白目标，它基于麦当劳 MCP 的实时菜单与营养数据，帮你配出一顿最优餐，并生成一张可以晒的营养报告卡。

麦当劳程序员创意开发大赛（1024）参赛项目 · 基于麦当劳 MCP 能力开发

## 它解决什么问题

健身 / 减脂 / 增肌的人面对麦当劳菜单时只有三个模糊问题：

- **这一顿多少热量？** 菜单上不标，得一个个查。
- **蛋白够不够？** 想吃饱又怕练了白练，不知道该怎么搭。
- **会不会超预算？** 单点凑单和套餐哪个划算，全靠心算。

麦记营养师把这三个问题变成一个约束求解问题：给定热量预算、蛋白目标和价格上限，在门店实时菜单中求解最优组合，输出带营养合计和蛋白密度点评的报告卡。

## 功能特性

- **两种求解模式**
  - `bulk` 增肌模式：热量预算内，蛋白最大化
  - `cut` 减脂模式：蛋白达标前提下，总热量最低
- **真实数据**：门店、菜单、价格、营养全部来自麦当劳 MCP 实时接口，不是写死的表
- **营养报告卡**：热量 / 蛋白 / 脂肪 / 碳水 / 钠合计 + 每日参考值占比 + 蛋白密度点评，Markdown 直接可晒
- **价格闭环**：求解结果用 `calculate-price` 核价，报告卡数字和下单价格一致
- **可继续下单**：确认方案后一句话即可创建订单（需用户明确确认）

## 快速开始

### 1. 领取麦当劳 MCP Token

前往 [open.mcd.cn/mcp](https://open.mcd.cn/mcp)，手机号登录后在控制台激活领取（免费）。

### 2. 配置 MCP 连接器

复制 [`mcp-config.example.json`](./mcp-config.example.json) 到你的 MCP 客户端配置中，把 Token 放进去：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": {
        "Authorization": "Bearer ${MCD_MCP_TOKEN}"
      }
    }
  }
}
```

在 WorkBuddy 中：【连接器】→【自定义连接器】→【配置 MCP】，粘贴上述 JSON 并启用 `mcd-mcp`。

### 3. 安装 Skill

把 `skill/` 目录放入你的 WorkBuddy skills 目录（或直接引用本仓库的 `skill/SKILL.md`），即可在对话中触发。

## 使用示例

对 WorkBuddy 说：

> 我在增肌，今天在公司附近麦当劳自取，热量预算 900 大卡，蛋白尽量多，预算 50 块。

Skill 会自动完成：定位附近门店 → 拉实时菜单 → 合并营养数据 → 求解 → 核价 → 输出报告卡：

```markdown
# 麦记营养师 · 配餐报告卡

**模式：** 增肌模式 · 热量预算内蛋白最大化

| 指标 | 数值 | 占每日参考值 |
|---|---:|---:|
| 热量 | 860 kcal | 43% |
| 蛋白质 | 50 g | 83% |
| 脂肪 | 34 g | 52% |
| 碳水化合物 | 88 g | 29% |
| 钠 | 1960 mg | 98% |
| 合计价格 | ¥43.00 | - |

**蛋白密度：** 5.8 g / 100 kcal

| 餐品 | 数量 | 小计 | 热量 | 蛋白 |
|---|---:|---:|---:|---:|
| 板烧鸡腿堡 | x2 | ¥43.00 | 860 kcal | 50 g |
```

完整示例见 [`examples/sample_output.md`](./examples/sample_output.md)（由 `tests/` 下的模拟数据离线生成）。

也可以直接用求解器，不依赖 Agent：

```bash
python3 skill/scripts/optimize_meal.py --input tests/mock_menu.json --mode bulk --report card.md
python3 skill/scripts/report_card.py < result.json
```

## 工作原理

```
用户约束 ──┐
           ▼
┌─────────────────── MCP 实时数据 ───────────────────┐
│ query-nearby-stores / delivery-query-stores 定位门店 │
│ query-meals                                    菜单  │
│ list-nutrition-foods                           营养  │
└───────────────────────┬───────────────────────────┘
                        ▼
             optimize_meal.py 约束求解
        （多种子贪心 + 局部爬山 + 破坏-修复）
                        ▼
┌─────────────────── 输出 ───────────────────┐
│ 最优配餐 JSON → report_card.py 渲染报告卡     │
│ calculate-price 核价 → 用户确认 → create-order│
└──────────────────────────────────────────────┘
```

## 项目结构

```
├── README.md                  # 本文档
├── CONTEST_DECLARATION.md     # 参赛声明（官方原文，不可改动）
├── MCP_INTEGRATION.md         # MCP 接入说明：Server / Tool / 调用流程 / 业务价值
├── mcp-config.example.json    # 脱敏 MCP 配置示例（仅环境变量占位符）
├── workbuddy.md               # WorkBuddy 开发上下文（联动活动核验用）
├── skill/
│   ├── SKILL.md               # WorkBuddy Skill 主文件
│   └── scripts/
│       ├── optimize_meal.py   # 配餐约束求解器（bulk / cut 两种模式）
│       └── report_card.py     # 营养报告卡渲染器
├── tests/
│   ├── mock_menu.json         # 模拟菜单（增肌模式用例）
│   ├── mock_menu_cut.json     # 模拟菜单（减脂模式用例）
│   └── run_tests.py           # 离线自测（不需要 MCP Token）
└── examples/
    └── sample_output.md       # 示例报告卡
```

## 测试

```bash
python3 tests/run_tests.py
```

用模拟菜单验证两种模式的求解正确性与硬约束（无网络、无 Token 也可运行）。

## 目标用户

- **健身 / 增肌人群**：在麦当劳快速凑够一顿高蛋白，不超热量预算
- **减脂 / 控卡人群**：蛋白达标的前提下把热量压到最低
- **办公室午休决策困难户**：输入预算和偏好，30 秒拿到带营养数据的方案

## 免责声明

本项目为麦当劳程序员节创意开发大赛参赛作品，由参赛者独立开发，非麦当劳官方产品。
餐品信息、价格及供应状态以麦当劳官方渠道实时结果为准；营养数据仅供参考，不构成医疗或营养专业建议。
