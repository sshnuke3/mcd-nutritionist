#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线自测：用 tests/ 下的模拟菜单验证求解器（不需要 MCP Token）。
用法：python3 tests/run_tests.py
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
OPT = os.path.join(HERE, "..", "skill", "scripts", "optimize_meal.py")


def run(mode, fixture):
    out = subprocess.run(
        [PY, OPT, "--input", os.path.join(HERE, fixture), "--mode", mode],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


def main():
    bulk = run("bulk", "mock_menu.json")
    t = bulk["totals"]
    assert t["calories"] <= 900, "bulk 违反热量硬约束"
    assert t["price"] <= 50, "bulk 违反价格硬约束"
    assert t["protein"] == 50, "bulk 未找到已知最优解（蛋白 50g）"

    cut = run("cut", "mock_menu_cut.json")
    t2 = cut["totals"]
    assert t2["protein"] >= 40, "cut 未达到蛋白目标"
    assert t2["calories"] == 690, "cut 未找到已知最优解（690 kcal）"

    print("PASS")
    print("  bulk:", json.dumps(t, ensure_ascii=False))
    print("  cut :", json.dumps(t2, ensure_ascii=False))


if __name__ == "__main__":
    main()
