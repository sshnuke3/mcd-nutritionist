# MCP 接入说明 · MCP_INTEGRATION.md

## MCP Server

| 项 | 值 |
|---|---|
| 名称 | `mcd-mcp`（麦当劳中国官方 MCP Server） |
| 地址 | `https://mcp.mcd.cn` |
| 协议 | MCP over Streamable HTTP |
| 鉴权 | `Authorization: Bearer <MCP_MCP_TOKEN>` |
| Token 获取 | [open.mcd.cn/mcp](https://open.mcd.cn/mcp) 手机号登录 → 控制台 → 激活领取（免费） |
| 服务端信息 | `mcd-mcp` v1.0.0，协议版本 2025-06-18，共 35 个 tools |

## 实际使用的 Tool

| Tool | 用途 | 调用时机 |
|---|---|---|
| `query-nearby-stores` | 到店场景按位置搜索门店（beType=1 自取 / 5 得来速） | 用户选择到店时，拿到 `storeCode`（得来速还有 `beCode`） |
| `delivery-query-addresses` | 查询用户配送地址列表 | 用户选择麦乐送外送时 |
| `delivery-query-stores` | 按地址 ID 查可配送门店 | 外送场景，拿到 `storeCode` / `beCode` |
| `query-meals` | 拉取门店在售餐品（编码、名称、价格） | 门店确定后，作为求解器的商品池 |
| `list-nutrition-foods` | 拉取餐品营养成分（能量、蛋白、脂肪、碳水、钠等） | 与菜单按名称对齐，合并成求解器输入 |
| `query-store-coupons` | 查询该门店 + 订单类型下可用的券 | 可选：有券时用于校准实际到手价 |
| `calculate-price` | 按门店 + 商品列表计算含优惠价格 | 求解完成后核价，保证报告卡数字与真实下单价一致 |
| `create-order` | 创建订单（到店 / 外送） | 仅限用户明确确认方案后，由用户触发 |

> 说明：求解与渲染全部由本地脚本完成（`skill/scripts/`），MCP 只负责提供实时业务数据，
> 不依赖服务端做推荐——`calculate-price` 是唯一用于"验证"的写前读接口。

## 调用流程

```
1. 收集约束（场景 / 位置 / 热量预算 / 蛋白目标 / 价格预算）
        │
2. 门店定位
   ├─ 到店：query-nearby-stores(searchType=2, city, keyword, beType=1|5)
   └─ 外送：delivery-query-addresses → delivery-query-stores(beType=2)
        │  得到 storeCode（+ beCode）
3. query-meals(storeCode, orderType, beType)          → 商品池（code/name/price）
4. list-nutrition-foods                              → 营养表
5. 本地求解：optimize_meal.py
   ├─ bulk：多种子贪心 + 局部爬山 + 破坏-修复，max 蛋白 s.t. 热量≤预算
   └─ cut ：密度贪心 + 精简，min 热量 s.t. 蛋白≥目标
6. calculate-price(同参数) 核价 → 与报告卡对齐
7. report_card.py 渲染 Markdown 报告卡交付给用户
8. （可选）用户确认后 create-order 下单
```

## 业务价值

1. **把"查营养"从 10 分钟变成 30 秒**：热量、蛋白、钠一键合计，附带每日参考值占比。
2. **把"怎么搭"从拍脑袋变成最优解**：约束求解给出可证明的最优组合（热量预算内蛋白最高 / 蛋白达标下热量最低），而不是启发式拼凑。
3. **价格可信**：所有方案经 `calculate-price` 核价，报告卡价格即下单价格，不靠估算。
4. **可复用的求解内核**：`optimize_meal.py` 是零依赖纯 Python，不接 MCP 也能跑（见 `tests/`），可移植到任何餐品数据源。

## 安全说明

- 仓库内**不包含任何真实 Token**：`mcp-config.example.json` 仅使用环境变量占位符 `${MCD_MCP_TOKEN}`。
- 求解过程不落盘任何用户个人数据；报告卡只包含餐品与营养合计。
