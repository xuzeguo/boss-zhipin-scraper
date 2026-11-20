#!/usr/bin/env python3
"""生成四方向多维对比表 + 岗位清单 CSV。"""
import json
import os
import re
import csv
from collections import Counter, defaultdict

OUT = "/Users/guoxuze/Documents/myproject/boss-zhipin-scraper/analysis"
RESULT = os.path.expanduser("~/.boss-zhipin-scraper/job-result")
JOBS = os.path.join(OUT, "market_jobs_v2.json")
ANA = os.path.join(OUT, "market_analysis_v2.json")
DET = os.path.join(RESULT, "market_details.json")

DIRS = ["纯前端", "全栈", "AI Agent（偏前端）", "偏前端细分赛道"]
DKEY = {"纯前端": "pure_fe", "全栈": "fullstack", "AI Agent（偏前端）": "ai_agent", "偏前端细分赛道": "frontier_sub"}


def parse_salary(s):
    m = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*[Kk]", s or "")
    if not m:
        return None
    lo, hi = float(m.group(1)), float(m.group(2))
    mm = re.search(r"·\s*(\d+(?:\.\d+)?)\s*薪", s)
    return lo, hi, float(mm.group(1)) if mm else 12.0


jobs = json.load(open(JOBS, encoding="utf-8"))["jobs"]
ana = json.load(open(ANA, encoding="utf-8"))
details = json.load(open(DET, encoding="utf-8")) if os.path.exists(DET) else []
det_map = {d["job_id"]: d for d in details}

# 严格落在 15-40K 内
for j in jobs:
    p = parse_salary(j.get("salary"))
    j["_p"] = p
strict = [j for j in jobs if j["_p"] and j["_p"][0] >= 15 and j["_p"][1] <= 40]

JD_PAT = {
    "AI/大模型": r"大模型|llm|agent|智能体|rag|提示词|prompt|openai|langchain|mcp|向量|embedding|aigc|claude|gpt|多模态",
    "后端/服务端": r"后端|服务端|java|golang|(?<![a-z])go(?![a-z])|python|spring|mysql|redis|数据库|api|接口设计|nest|express|koa|fastify",
    "工程化": r"webpack|vite|rollup|工程化|构建|ci/cd|monorepo|pnpm|turbo",
    "性能优化": r"性能优化|首屏|加载速度|渲染性能|内存|卡顿",
    "架构/方案": r"架构|技术选型|技术方案|设计模式|中台|从0到1|0-1|技术决策",
    "组件库/设计系统": r"组件库|设计系统|design system|hooks|ui库|基础库",
    "测试": r"单元测试|jest|vitest|自动化测试|e2e|playwright|cypress|单测",
    "沟通/推动": r"沟通|协作|跨团队|推动|owner|责任心|主动",
    "带人/管理": r"带团队|团队管理|管理经验|leader|导师|指导|培养",
    "英语": r"英语|english|英文",
    "数据/BI": r"bi|数据看板|报表|数据平台|指标体系|可视化",
    "跨端/小程序": r"小程序|react[\s-]?native|flutter|uni-?app|taro|鸿蒙|harmony|electron|跨端|多端",
    "业务/产品意识": r"产品|业务|用户|需求|商业|场景",
}


def rate(js, pat):
    n = sum(1 for j in js if re.search(pat, " ".join([j.get("skills") or "", j.get("title") or ""]),
                                         re.I))
    return n, len(js)


def jd_rate(js, pat):
    js2 = [j for j in js if j["job_id"] in det_map]
    n = sum(1 for j in js2 if re.search(pat, det_map[j["job_id"]].get("jd") or "", re.I))
    return n, len(js2)


rows = []
allc = Counter()
for d in DIRS:
    js = [j for j in jobs if j["direction"] == d]
    ks = [j for j in strict if j["direction"] == d]
    p = ana["directions"][DKEY[d]]
    mids = [(j["_p"][0] + j["_p"][1]) / 2 for j in js]
    rows.append((d, js, ks, p, mids))

L = []
L.append("# 上海前端市场四大方向 · 多维要求对比\n")
L.append(f"数据口径：BOSS直聘 · 上海 · 关键词覆盖 前端/全栈/AI Agent/AI应用开发/React/Vue/大前端/小程序/数据可视化/鸿蒙/Electron/Node.js/低代码/前端架构，"
         f"共抓取 {ana['total_raw']} 条，按「薪资区间与 15-40K 有交集」筛出 {ana['target']} 条（完全落在 15-40K 内 {ana['strict']} 条）。\n")

L.append("## 1. 总览：数量、薪资与结构\n")
L.append("| 方向 | 有效岗位 | 薪资中位 | P25–P75 | 中位年薪 | 16薪+占比 | 主力经验 | 本科占比 |")
L.append("|---|---|---|---|---|---|---|---|")
for d, js, ks, p, mids in rows:
    s = p["salary"]
    m16 = sum(1 for j in js if j["_p"][2] >= 15)
    top_exp = p["experience"][0][0] if p["experience"] else "-"
    deg = dict(p["degree"])
    ben = deg.get("本科", 0)
    L.append(f"| {d} | {len(js)} | {s['median_mid']:.1f}K | {s['p25']:.0f}–{s['p75']:.0f}K | "
             f"{s['median_annual']:.0f}K | {m16}/{len(js)} ({m16/len(js)*100:.0f}%) | {top_exp} | {ben/len(js)*100:.0f}% |")
L.append("")

L.append("## 2. 薪资带分布（按岗位月薪中位落在哪一档）\n")
L.append("| 方向 | 15-20K | 20-25K | 25-30K | 30-35K | 35-40K+ |")
L.append("|---|---|---|---|---|---|")
for k in DIRS:
    m = ana["salary_matrix"][DKEY[k]]
    L.append("| " + k + " | " + " | ".join(str(m[b]) for b in ["15-20K", "20-25K", "25-30K", "30-35K", "35-40K+"]) + " |")
L.append("")

L.append("## 3. 经验 / 学历 / 公司结构\n")
L.append("| 方向 | 经验要求分布 | 学历要求分布 | 公司规模 TOP3 | 融资阶段 TOP3 |")
L.append("|---|---|---|---|---|")
for d, js, ks, p, mids in rows:
    exp = " / ".join(f"{a}{b}" for a, b in p["experience"][:4])
    deg = " / ".join(f"{a}{b}" for a, b in p["degree"][:4])
    sc = " / ".join(f"{a}{b}" for a, b in p["scale"][:3])
    st = " / ".join(f"{a}{b}" for a, b in p["stage"][:3])
    L.append(f"| {d} | {exp} | {deg} | {sc} | {st} |")
L.append("")

L.append("## 4. 技术栈与能力要求（占比 = 命中岗位数 / 该方向岗位数）\n")
L.append("| 能力项 | 纯前端 | 全栈 | AI Agent（偏前端） | 偏前端细分 |")
L.append("|---|---|---|---|---|")
for nm, pat in JD_PAT.items():
    cells = []
    for d, js, ks, p, mids in rows:
        n, t = rate(js, pat)
        cells.append(f"{n}/{t} ({n/t*100:.0f}%)")
    L.append(f"| {nm} | " + " | ".join(cells) + " |")
L.append("")

L.append("### 4.1 具体技术栈命中数（标签+标题口径）\n")
TECH_STACK = ["React", "Vue", "TypeScript", "JavaScript", "Node.js", "后端能力", "性能优化",
              "工程化(Vite/Webpack)", "微前端/架构", "组件库/设计系统", "测试", "鸿蒙/ArkTS",
              "可视化/WebGL", "小程序", "React Native", "Electron/桌面", "AI能力", "全栈意识"]
L.append("| 技术栈 | 纯前端 | 全栈 | AI Agent（偏前端） | 偏前端细分 |")
L.append("|---|---|---|---|---|")
for t in TECH_STACK:
    cells = []
    for d, js, ks, p, mids in rows:
        v = p["signals"].get(t, 0)
        cells.append(f"{v} ({v/len(js)*100:.0f}%)")
    L.append(f"| {t} | " + " | ".join(cells) + " |")
L.append("")

L.append("## 5. 行业分布 TOP5\n")
L.append("| 方向 | 行业 |")
L.append("|---|---|")
for d, js, ks, p, mids in rows:
    L.append(f"| {d} | " + " / ".join(f"{a}{b}" for a, b in p["industry"][:6]) + " |")
L.append("")

L.append("## 6. 技能标签高频（TOP10，原始标签口径）\n")
L.append("| 方向 | 高频技能标签 |")
L.append("|---|---|")
for d, js, ks, p, mids in rows:
    L.append(f"| {d} | " + " / ".join(f"{a}×{b}" for a, b in p["skills"][:10]) + " |")
L.append("")

# JD 深度指标
if details:
    L.append(f"## 7. JD 原文深度指标（样本 {len(details)} 份，每方向约 5-6 份）\n")
    L.append("| JD 信号 | 纯前端 | 全栈 | AI Agent（偏前端） | 偏前端细分 |")
    L.append("|---|---|---|---|---|")
    for nm, pat in JD_PAT.items():
        cells = []
        for d, js, ks, p, mids in rows:
            n, t = jd_rate(js, pat)
            cells.append(f"{n}/{t}" if t else "-")
        L.append(f"| {nm} | " + " | ".join(cells) + " |")
    L.append("")

# CSV
csv_path = os.path.join(OUT, "岗位清单_15-40K.csv")
with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["方向", "岗位", "薪资", "月薪中位K", "完全落在15-40K", "经验", "学历", "公司", "规模", "行业", "融资", "技能标签", "链接"])
    for j in sorted(jobs, key=lambda x: (DIRS.index(x["direction"]), -((x["_p"][0] + x["_p"][1]) / 2))):
        exp = [t for t in (j.get("tags") or "").split("|") if re.search(r"年|应届|在校|不限", t)]
        deg = [t for t in (j.get("tags") or "").split("|") if re.search(r"本科|大专|硕士|博士|中专|高中|不限", t)]
        inr = "是" if (j["_p"] and j["_p"][0] >= 15 and j["_p"][1] <= 40) else "否(区间交叠)"
        w.writerow([j["direction"], j.get("title"), j.get("salary"),
                    (j["_p"][0] + j["_p"][1]) / 2 if j["_p"] else "",
                    inr,
                    exp[0] if exp else "", deg[0] if deg else "",
                    j.get("boss_name"), j.get("company_scale"), j.get("company_industry"),
                    j.get("company_stage"), j.get("skills"), j.get("job_link")])

open(os.path.join(OUT, "方向对比矩阵.md"), "w", encoding="utf-8").write("\n".join(L))
print("\n".join(L[:60]))
print("...")
print("saved:", os.path.join(OUT, "方向对比矩阵.md"), csv_path)
