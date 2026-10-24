#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦记营养师 · 配餐优化器 (optimize_meal.py)

输入一份麦当劳餐品清单（含营养与价格），在约束条件下求解最优配餐：
  - bulk 增肌模式：热量预算内，蛋白最大化
  - cut  减脂模式：满足蛋白目标的前提下，总热量最低

数据来源（由 Agent 通过麦当劳 MCP 采集后喂入）：
  - 餐品编码/价格  -> query-meals
  - 营养数据       -> list-nutrition-foods
  - 门店可用的券   -> query-store-coupons（可选，用于价格校准）

用法：
  python3 optimize_meal.py --input menu.json [--mode bulk|cut] [--report out.md]
  cat menu.json | python3 optimize_meal.py
输入 JSON 结构见 tests/mock_menu.json；输出为 JSON（stdout）。
"""
import argparse
import json
import os
import sys

# 每日营养素参考值（中国食品标签通用参考，基于 2000 kcal 膳食）
DAILY_REFERENCE = {
    "calories": 2000,
    "protein": 60,
    "fat": 65,
    "carb": 300,
    "sodium": 2000,
}
NUTRIENTS = ("calories", "protein", "fat", "carb", "sodium")


def load_items(raw_items):
    """清洗餐品数据：缺营养数据的项剔除并记录。"""
    items, skipped = [], []
    for it in raw_items or []:
        try:
            code = str(it["code"])
            name = str(it["name"])
            cal = float(it.get("calories") or 0)
        except (KeyError, TypeError, ValueError):
            skipped.append(str(it.get("name", "未知餐品")))
            continue
        if cal <= 0:
            skipped.append(name)
            continue
        items.append({
            "code": code,
            "name": name,
            "price": round(float(it.get("price") or 0), 2),
            "calories": cal,
            "protein": max(0.0, float(it.get("protein") or 0)),
            "fat": max(0.0, float(it.get("fat") or 0)),
            "carb": max(0.0, float(it.get("carb") or 0)),
            "sodium": max(0.0, float(it.get("sodium") or 0)),
        })
    return items, skipped


def totals(sel):
    """sel: [(item, qty), ...] -> 合计营养与价格"""
    t = {k: 0.0 for k in NUTRIENTS}
    t["price"] = 0.0
    for it, q in sel:
        for k in NUTRIENTS:
            t[k] += it[k] * q
        t["price"] += it["price"] * q
    t["price"] = round(t["price"], 2)
    return t


def _copy(sel):
    return [(it, q) for it, q in sel]


def _add(sel, it):
    out = _copy(sel)
    for idx, (i, q) in enumerate(out):
        if i["code"] == it["code"]:
            out[idx] = (i, q + 1)
            return out
    out.append((it, 1))
    return out


def _remove(sel, it):
    return _remove_n(sel, it, 1)


def _remove_n(sel, it, n):
    out = []
    left = n
    for i, q in sel:
        if i["code"] == it["code"]:
            take = min(q, left)
            left -= take
            if q > take:
                out.append((i, q - take))
            continue
        out.append((i, q))
    return out


def _qty(sel, code):
    return sum(q for it, q in sel if it["code"] == code)


def feasible(sel, c):
    """硬约束检查：热量上限 / 价格上限 / 件数上限 / 单品件数上限"""
    t = totals(sel)
    cap = c.get("max_calories")
    if cap and t["calories"] > cap + 1e-6:
        return False
    pcap = c.get("max_price")
    if pcap and t["price"] > pcap + 1e-6:
        return False
    m = c.get("max_items")
    if m and sum(q for _, q in sel) > m:
        return False
    mq = c.get("max_qty")
    if mq:
        for it, q in sel:
            if q > mq:
                return False
    return True


def density(it):
    """蛋白密度：每千卡的蛋白克数"""
    return it["protein"] / max(it["calories"], 1.0)


def _hill_climb_add(sel, items, c, maxq):
    """局部爬山：在硬约束内，能涨蛋白就加一件"""
    improved = True
    while improved:
        improved = False
        for it in items:
            if _qty(sel, it["code"]) >= maxq:
                continue
            trial = _add(sel, it)
            if feasible(trial, c) and totals(trial)["protein"] > totals(sel)["protein"] + 1e-6:
                sel = trial
                improved = True
    return sel


def _greedy(sel0, items, c, order_key, maxq):
    """按指定排序键贪心塞满热量预算"""
    budget = c.get("max_calories") or 2000
    sel = _copy(sel0)
    for it in sorted(items, key=order_key):
        if _qty(sel, it["code"]) >= maxq:
            continue
        q = 0
        while q < maxq and totals(sel)["calories"] + it["calories"] <= budget:
            sel = _add(sel, it)
            q += 1
    return sel


def _destroy_repair(sel, items, c, maxq):
    """破坏-修复：移除已有单品 1~2 个单位后重新爬山，接受严格更优解"""
    best = sel
    improved = True
    while improved:
        improved = False
        for it in items:
            q0 = _qty(best, it["code"])
            for drop in (1, 2):
                if q0 < drop:
                    continue
                cand = _hill_climb_add(_remove_n(best, it, drop), items, c, maxq)
                if feasible(cand, c) and totals(cand)["protein"] > totals(best)["protein"] + 1e-6:
                    best = cand
                    improved = True
                    break
    return best


def optimize_bulk(items, c):
    """热量预算内蛋白最大化：多种子贪心 + 爬山 + 破坏-修复"""
    maxq = int(c.get("max_qty", 3))
    seeds = (
        lambda x: -density(x),                                    # 蛋白/热量 密度
        lambda x: -(x["protein"] / max(x["price"], 0.01)),        # 蛋白/价格 密度
        lambda x: -x["protein"],                                  # 绝对蛋白量
    )
    best, best_p = [], -1.0
    for key in seeds:
        sel = _hill_climb_add(_greedy([], items, c, key, maxq), items, c, maxq)
        sel = _destroy_repair(sel, items, c, maxq)
        p = totals(sel)["protein"]
        if p > best_p + 1e-6:
            best, best_p = sel, p
    return best


def optimize_cut(items, c):
    """蛋白达标前提下总热量最低：密度贪心 + 精简"""
    target = float(c.get("min_protein") or 30)
    maxq = int(c.get("max_qty", 3))
    sel = []
    for it in sorted(items, key=lambda x: -density(x)):
        while totals(sel)["protein"] < target - 1e-6:
            if _qty(sel, it["code"]) >= maxq:
                break
            trial = _add(sel, it)
            cap = c.get("max_calories")
            if cap and totals(trial)["calories"] > cap + 1e-6:
                break
            sel = trial
        if totals(sel)["protein"] >= target - 1e-6:
            break
    # 精简：优先移除"每克蛋白热量代价最高"的件，且不跌破蛋白目标
    changed = True
    while changed:
        changed = False
        for it, q in sorted(sel, key=lambda x: -(x[0]["calories"] / max(x[0]["protein"], 1e-6))):
            trial = _remove(sel, it)
            if totals(trial)["protein"] >= target - 1e-6 and feasible(trial, c):
                sel = trial
                changed = True
                break
    return sel


def build_result(sel, mode, c, skipped):
    t = totals(sel)
    plan = []
    for it, q in sel:
        plan.append({
            "code": it["code"],
            "name": it["name"],
            "quantity": q,
            "unit_price": it["price"],
            "subtotal_price": round(it["price"] * q, 2),
            "calories": round(it["calories"] * q, 1),
            "protein": round(it["protein"] * q, 1),
            "fat": round(it["fat"] * q, 1),
            "carb": round(it["carb"] * q, 1),
            "sodium": round(it["sodium"] * q, 1),
        })
    plan.sort(key=lambda x: -x["calories"])
    daily = {k: round(t[k] / DAILY_REFERENCE[k] * 100) for k in NUTRIENTS}
    warnings = []
    if c.get("min_protein") and t["protein"] < c["min_protein"]:
        warnings.append("约束条件下无法达到蛋白目标 %.0f g，已给出当前最优解（蛋白 %.0f g）"
                        % (c["min_protein"], t["protein"]))
    return {
        "mode": mode,
        "constraints": {k: v for k, v in c.items() if v},
        "plan": plan,
        "totals": {
            "calories": round(t["calories"], 1),
            "protein": round(t["protein"], 1),
            "fat": round(t["fat"], 1),
            "carb": round(t["carb"], 1),
            "sodium": round(t["sodium"], 1),
            "price": t["price"],
            "item_count": sum(q for _, q in sel),
        },
        "metrics": {
            "protein_per_100kcal": round(t["protein"] / max(t["calories"], 1) * 100, 2),
            "protein_per_yuan": round(t["protein"] / max(t["price"], 0.01), 2),
            "calories_per_yuan": round(t["calories"] / max(t["price"], 0.01), 1),
            "daily_percent": daily,
        },
        "skipped_items": skipped,
        "warnings": warnings,
    }


def main():
    ap = argparse.ArgumentParser(description="麦当劳配餐营养优化器")
    ap.add_argument("--input", help="餐品 JSON 文件路径（缺省读 stdin）")
    ap.add_argument("--mode", choices=["bulk", "cut"], help="覆盖输入文件中的 mode")
    ap.add_argument("--report", help="可选：把 Markdown 营养报告卡写到该路径")
    args = ap.parse_args()

    raw = open(args.input, encoding="utf-8") if args.input else sys.stdin
    data = json.load(raw)
    mode = args.mode or data.get("mode", "bulk")
    c = data.get("constraints", {}) or {}
    items, skipped = load_items(data.get("items"))

    if not items:
        print(json.dumps({"error": "没有可用餐品（缺少营养数据）", "skipped_items": skipped},
                         ensure_ascii=False, indent=2))
        sys.exit(2)

    sel = optimize_bulk(items, c) if mode == "bulk" else optimize_cut(items, c)
    result = build_result(sel, mode, c, skipped)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.report:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import report_card
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report_card.render(result))
        print("报告卡已写入: %s" % args.report, file=sys.stderr)


if __name__ == "__main__":
    main()
