#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦记营养师 · 营养报告卡 (report_card.py)

读取 optimize_meal.py 的输出 JSON，渲染一份可直接分享的 Markdown 报告卡。
用法：python3 report_card.py result.json   （缺省读 stdin）
"""
import json
import sys

DAILY_REFERENCE = {"calories": 2000, "protein": 60, "fat": 65, "carb": 300, "sodium": 2000}


def verdict(m):
    """根据蛋白密度给出点评（阈值按快餐场景校准）"""
    d = m["protein_per_100kcal"]
    if d >= 7:
        return "蛋白密度优秀，这一餐的性价比拉满了。"
    if d >= 5:
        return "蛋白密度良好，是健身友好的选择。"
    if d >= 3.5:
        return "蛋白密度一般，可以再往高蛋白单品靠一靠。"
    return "蛋白密度偏低，建议把预算多分给汉堡和鸡腿肉。"


def render(r):
    t = r["totals"]
    daily = r["metrics"]["daily_percent"]
    mode_name = "增肌模式 · 热量预算内蛋白最大化" if r["mode"] == "bulk" else "减脂模式 · 蛋白达标热量最低"
    lines = []
    lines.append("# 麦记营养师 · 配餐报告卡")
    lines.append("")
    lines.append("**模式：** %s" % mode_name)
    lines.append("")
    lines.append("## 营养合计")
    lines.append("")
    lines.append("| 指标 | 数值 | 占每日参考值 |")
    lines.append("|---|---:|---:|")
    lines.append("| 热量 | %.0f kcal | %d%% |" % (t["calories"], daily["calories"]))
    lines.append("| 蛋白质 | %.0f g | %d%% |" % (t["protein"], daily["protein"]))
    lines.append("| 脂肪 | %.0f g | %d%% |" % (t["fat"], daily["fat"]))
    lines.append("| 碳水化合物 | %.0f g | %d%% |" % (t["carb"], daily["carb"]))
    lines.append("| 钠 | %.0f mg | %d%% |" % (t["sodium"], daily["sodium"]))
    lines.append("| 合计价格 | ¥%.2f | - |" % t["price"])
    lines.append("")
    lines.append("**蛋白密度：** %.1f g / 100 kcal　|　**蛋白单价：** %.1f g / 元"
                 % (r["metrics"]["protein_per_100kcal"], r["metrics"]["protein_per_yuan"]))
    lines.append("")
    lines.append("## 餐品明细")
    lines.append("")
    lines.append("| 餐品 | 数量 | 小计 | 热量 | 蛋白 |")
    lines.append("|---|---:|---:|---:|---:|")
    for p in r["plan"]:
        lines.append("| %s | x%d | ¥%.2f | %.0f kcal | %.0f g |"
                     % (p["name"], p["quantity"], p["subtotal_price"], p["calories"], p["protein"]))
    lines.append("")
    lines.append("## 点评")
    lines.append("")
    lines.append(verdict(r["metrics"]))
    if r.get("warnings"):
        lines.append("")
        for w in r["warnings"]:
            lines.append("- 注意：%s" % w)
    lines.append("")
    lines.append("---")
    lines.append("*数据来自麦当劳 MCP 实时菜单与营养接口；输出仅供参考，不构成营养建议。*")
    lines.append("")
    return "\n".join(lines)


def main():
    raw = sys.stdin.read() if len(sys.argv) < 2 else open(sys.argv[1], encoding="utf-8").read()
    print(render(json.loads(raw)))


if __name__ == "__main__":
    main()
