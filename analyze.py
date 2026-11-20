#!/usr/bin/env python3
"""上海前端岗位 18-30K 市场分析：薪资精筛 + 技能/经验/学历/JD 词频统计。"""
import json
import re
import os
from collections import Counter

RESULT_DIR = os.path.expanduser("~/.boss-zhipin-scraper/job-result")
JOBS_FILE = os.path.join(RESULT_DIR, "boss_jobs_20261120_1647.json")
DETAILS_FILE = os.path.join(RESULT_DIR, "boss_details_20261120_1650.json")
OUT_DIR = "/Users/guoxuze/Documents/myproject/boss-zhipin-scraper/analysis"
os.makedirs(OUT_DIR, exist_ok=True)

LOW, HIGH = 18, 30  # K


def parse_salary(s):
    """'18-35K·18薪' -> (18,35,18) ; '250-300元/天' -> None ; 返回月薪下限/上限(K)。"""
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*[Kk]", s)
    if not m:
        return None
    lo, hi = float(m.group(1)), float(m.group(2))
    months = 12
    mm = re.search(r"·\s*(\d+)\s*薪", s)
    if mm:
        months = int(mm.group(1))
    return lo, hi, months


def in_range(parsed):
    """薪资区间与 18-30K 有交集即视为目标区间（下限<=30 且 上限>=18）。"""
    if not parsed:
        return False
    lo, hi, _ = parsed
    return lo <= HIGH and hi >= LOW


jobs = json.load(open(JOBS_FILE, encoding="utf-8"))["jobs"]
for j in jobs:
    j["_p"] = parse_salary(j.get("salary", ""))

target = [j for j in jobs if in_range(j["_p"])]
print(f"总岗位 {len(jobs)} | 18-30K 区间 {len(target)} 条\n")

# 精确落在 18-30K 内（更严格口径）
strict = [j for j in jobs if j["_p"] and j["_p"][0] >= LOW and j["_p"][1] <= HIGH]
print(f"严格完全落在18-30K: {len(strict)} 条")

# ---- 统计 ----
def counter_of(field, split="|"):
    c = Counter()
    for j in target:
        v = j.get(field, "") or ""
        for item in v.split(split):
            item = item.strip()
            if item:
                c[item] += 1
    return c

skills = counter_of("skills")
labels = counter_of("tags")
company_scale = Counter(j.get("company_scale", "") for j in target if j.get("company_scale"))
company_stage = Counter(j.get("company_stage", "") for j in target if j.get("company_stage"))
industry = Counter(j.get("company_industry", "") for j in target if j.get("company_industry"))
welfare = counter_of("welfare")

# 经验 & 学历从 tags 拆
exp = Counter()
degree = Counter()
for j in target:
    for t in (j.get("tags", "") or "").split("|"):
        t = t.strip()
        if t in ("应届生", "在校生", "经验不限", "1年以内", "1-3年", "3-5年", "5-10年", "10年以上"):
            exp[t] += 1
        if t in ("初中及以下", "中专/中技", "高中", "大专", "本科", "硕士", "博士", "学历不限"):
            degree[t] += 1

# 薪资分布
salary_bins = Counter()
for j in target:
    lo, hi, months = j["_p"]
    salary_bins[f"{int(lo)}-{int(hi)}K"] += 1

# 标题关键词
title_kw = Counter()
KW = ["React", "Vue", "Angular", "TypeScript", "TS", "JavaScript", "JS", "Node", "全栈",
      "小程序", "H5", "移动端", "React Native", "Flutter", "WebGL", "Three.js", "低代码",
      "架构", "资深", "高级", "中级", "专家", "负责人", "leader", "Leader", "前端"]
for j in target:
    t = j.get("title", "")
    for k in KW:
        if k.lower() in t.lower():
            title_kw[k] += 1

# JD 词频（9 条真实详情）
details = []
if os.path.exists(DETAILS_FILE):
    details = json.load(open(DETAILS_FILE, encoding="utf-8"))
jd_text = "\n".join((d.get("jd", "") or "") for d in details)
jd_skill_tags = Counter()
for d in details:
    for s in (d.get("skill_tags", "") or "").split("|"):
        s = s.strip()
        if s:
            jd_skill_tags[s] += 1

TECH_PATTERNS = {
    "React": r"\breact\b", "Vue": r"\bvue\b", "Angular": r"angular",
    "TypeScript": r"typescript|\bts\b", "JavaScript": r"javascript|\bjs\b",
    "HTML/CSS": r"html|css", "Node.js": r"node\.?js|\bnode\b",
    "Webpack/Vite": r"webpack|\bvite\b|rollup", "Git": r"\bgit\b",
    "微信小程序": r"小程序|miniprogram", "React Native": r"react.?native",
    "Flutter": r"flutter", "Next.js/SSR": r"next\.?js|\bssr\b|服务端渲染",
    "低代码": r"低代码|lowcode", "Three.js/WebGL": r"three\.?js|webgl",
    "单元测试": r"单元测试|jest|单测", "CI/CD": r"ci/cd|持续集成",
    "性能优化": r"性能优化|首屏|加载速度", "微前端": r"微前端|micro.?frontend",
    "ECharts/可视化": r"echarts|图表|可视化", "后端(Node/Go/Java)": r"后端|golang|\bgo\b|\bjava\b",
}
jd_tech = Counter()
for name, pat in TECH_PATTERNS.items():
    n = len(re.findall(pat, jd_text, re.I))
    if n:
        jd_tech[name] = n


def top(c, k=15):
    return [(a, b) for a, b in c.most_common(k)]


report = {
    "total": len(jobs), "target_count": len(target), "strict_count": len(strict),
    "salary_bins": top(salary_bins, 20),
    "skills": top(skills, 25), "experience": top(exp), "degree": top(degree),
    "title_kw": top(title_kw, 20), "company_scale": top(company_scale, 12),
    "company_stage": top(company_stage, 12), "industry": top(industry, 12),
    "welfare": top(welfare, 15), "jd_skill_tags": top(jd_skill_tags, 20),
    "jd_tech": top(jd_tech, 20), "details_count": len(details),
}
json.dump(report, open(os.path.join(OUT_DIR, "analysis_data.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

# 保存精筛后的岗位
json.dump({"keyword": "前端", "city": "上海", "range": "18-30K",
           "total": len(target), "jobs": [{k: v for k, v in j.items() if k != "_p"} for j in target]},
          open(os.path.join(OUT_DIR, "fe_18-30k_jobs.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

# 文本报告
L = []
L.append("# 上海前端岗位 18-30K 市场数据分析报告\n")
L.append(f"数据源：BOSS直聘 · 关键词「前端」 · 上海 · 抓取时间 2026-11-20\n")
L.append(f"样本：共抓取 {len(jobs)} 条岗位，其中薪资区间与 18-30K 重叠的有 **{len(target)}** 条，"
         f"完全落在 18-30K 内的有 {len(strict)} 条。\n")

def section(title, data, unit="次"):
    L.append(f"\n## {title}\n")
    if not data:
        L.append("_无数据_\n"); return
    maxv = data[0][1]
    for name, v in data:
        bar = "█" * int(v / maxv * 30) if maxv else ""
        L.append(f"- {name}: {v} {unit} {bar}")
    L.append("")

L.append("> 说明：18-30K 无精确 API 筛选项，采用「薪资区间与 18-30K 有交集」口径（如 13-26K、18-35K、20-40K 均计入），更贴近市场真实分布。\n")
section("薪资区间分布", report["salary_bins"])
section("技能要求（skills 标签）", report["skills"])
section("经验要求", report["experience"])
section("学历要求", report["degree"])
section("岗位标题高频关键词", report["title_kw"])
section("公司规模", report["company_scale"])
section("融资阶段", report["company_stage"])
section("行业分布", report["industry"])
section("福利待遇词频", report["welfare"])
section(f"JD 技能标签（{len(details)} 份真实详情）", report["jd_skill_tags"])
section("JD 技术词命中次数（9 份详情文本）", report["jd_tech"])

open(os.path.join(OUT_DIR, "市场分析报告.md"), "w", encoding="utf-8").write("\n".join(L))

print("=== 核心结果 ===")
for k in ["salary_bins", "skills", "experience", "degree", "title_kw", "jd_tech"]:
    print(f"\n[{k}]")
    for name, v in report[k][:12]:
        print(f"  {name}: {v}")
print(f"\n报告已保存: {OUT_DIR}")
