#!/usr/bin/env python3
"""多方向前端岗位市场分析：纯前端 / 全栈 / AI Agent(偏前端) / 偏前端细分。
输出：统计 JSON、Markdown 对比表、按方向均衡排序的详情采样清单。
"""
import json
import re
import os
import argparse
from collections import Counter, defaultdict

RESULT_DIR = os.path.expanduser("~/.boss-zhipin-scraper/job-result")
OUT_DIR = "/Users/guoxuze/Documents/myproject/boss-zhipin-scraper/analysis"
MASTER = os.path.join(RESULT_DIR, "market_master.json")

LOW, HIGH = 15, 40  # K

EXP_ORDER = ["应届生", "在校生", "经验不限", "1年以内", "1-3年", "3-5年", "5-10年", "10年以上"]
DEG_ORDER = ["学历不限", "大专", "本科", "硕士", "博士"]


def parse_salary(s):
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*[Kk]", s)
    if not m:
        return None
    lo, hi = float(m.group(1)), float(m.group(2))
    months = 12
    mm = re.search(r"·\s*(\d+(?:\.\d+)?)\s*薪", s)
    if mm:
        months = float(mm.group(1))
    return lo, hi, months


def overlap(lo, hi):
    return lo <= HIGH and hi >= LOW


AI_RE = re.compile(r"(?<![a-z])(ai|aigc|agent|agents|llm|大模型|智能体|机器学习|深度学习|算法工程|提示词|prompt|rag|多模态|生成式)(?![a-z])", re.I)
FS_RE = re.compile(r"全栈|full[\s-]?stack", re.I)
SUB_RE = re.compile(r"鸿蒙|harmony|arkts|electron|flutter|react[\s-]?native|\brn\b|跨端|小程序|uni-?app|taro|可视化|webgl|three\.?js|大屏|低代码|low[\s-]?code|桌面端|客户端|web3|区块链|游戏前端|cocos|laya", re.I)
FE_RE = re.compile(r"前端|web|react|vue|angular|svelte|h5|javascript|\bjs\b|typescript|\bts\b|node|小程序|页面|界面|大前端|移动端|c端|b端|saas|低代码", re.I)
# 非开发岗（运营/产品/推广等）排除
NON_DEV_RE = re.compile(r"运营|产品经理|产品专家|推广|审核|投放|销售|市场|客服|实施|项目经理|招聘|猎头|商务|顾问|分析师|设计师|美工|讲师|编辑", re.I)

TECH = {
    "React": r"\breact\b(?![\s-]?native)",
    "Vue": r"\bvue\b",
    "Angular": r"angular",
    "TypeScript": r"typescript|\bts\b",
    "JavaScript": r"javascript|(?<![a-z])js(?![a-z])",
    "Node.js": r"node\.?js|(?<![a-z])node(?![a-z])",
    "小程序": r"小程序|miniprogram|微信生态",
    "React Native": r"react[\s-]?native|\brn\b",
    "Flutter": r"flutter",
    "鸿蒙/ArkTS": r"鸿蒙|harmony|arkts",
    "Electron/桌面": r"electron|桌面端|tauri",
    "可视化/WebGL": r"可视化|echarts|webgl|three\.?js|大屏|d3",
    "工程化(Vite/Webpack)": r"webpack|vite|rollup|工程化|构建工具",
    "性能优化": r"性能优化|首屏|加载速度|内存|渲染性能",
    "微前端/架构": r"微前端|架构|技术选型|技术方案|设计模式",
    "组件库/设计系统": r"组件库|设计系统|design system|hooks|ui库",
    "测试": r"单元测试|jest|vitest|自动化测试|e2e|playwright|cypress",
    "后端能力": r"后端|服务端|java|golang|(?<![a-z])go(?![a-z])|python|spring|mysql|redis|数据库|api设计|接口设计|nest|express|koa|fastify",
    "AI能力": r"大模型|llm|agent|智能体|rag|提示词|prompt|openai|langchain|mcp|向量|embedding|function[\s-]?calling|aigc|claude|gpt",
    "全栈意识": r"全栈|前后端|端到端|独立完成|从0到1|0-1",
    "数据/BI": r"bi|数据看板|报表|数据平台|指标体系",
    "低代码": r"低代码|low[\s-]?code|可视化搭建|搭建平台",
    "沟通协作": r"沟通|协作|跨团队|推动|owner|责任心|主动性",
    "带人/管理": r"带团队|团队管理|管理经验|leader|导师|指导|梯队",
    "英文": r"英语|english|读写英文|英文文档",
}


def counter_split(jobs, field):
    c = Counter()
    for j in jobs:
        v = j.get(field) or ""
        for item in re.split(r"[|,、/]", v):
            item = item.strip()
            if item:
                c[item] += 1
    return c


def classify(job):
    title = job.get("title", "") or ""
    extra = " ".join([job.get("skills", "") or "", job.get("job_labels", "") or "",
                      job.get("company_industry", "") or ""])
    t = title + " " + extra
    if NON_DEV_RE.search(title):
        return "other"
    if AI_RE.search(title):
        return "ai_agent"
    if FS_RE.search(title):
        return "fullstack"
    if SUB_RE.search(title) or SUB_RE.search(job.get("skills", "") or ""):
        return "frontier_sub"
    if FE_RE.search(t):
        return "pure_fe"
    return "other"


def pct(a, b):
    return f"{a/b*100:.0f}%" if b else "-"


def median(xs):
    if not xs:
        return None
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", default=MASTER)
    ap.add_argument("--details", default="")
    ap.add_argument("--sample", default="")
    ap.add_argument("--tag", default="v2")
    args = ap.parse_args()

    data = json.load(open(args.master, encoding="utf-8"))
    jobs = data["jobs"]
    for j in jobs:
        j["_p"] = parse_salary(j.get("salary", ""))
        j["_dir"] = classify(j)

    # 详情按 job_id 索引
    detail_map = {}
    if args.details and os.path.exists(args.details):
        for d in json.load(open(args.details, encoding="utf-8")):
            if d.get("job_id"):
                detail_map[d["job_id"]] = d
            elif d.get("job_link"):
                detail_map[d["job_link"]] = d

    target = [j for j in jobs if j["_p"] and overlap(j["_p"][0], j["_p"][1])
              and j["_dir"] != "other"]
    # 严格完全落在 15-40K
    strict = [j for j in target if j["_p"][0] >= LOW and j["_p"][1] <= HIGH]

    DIRS = {
        "pure_fe": "纯前端",
        "fullstack": "全栈",
        "ai_agent": "AI Agent（偏前端）",
        "frontier_sub": "偏前端细分赛道",
    }

    def jd_text(j):
        d = detail_map.get(j.get("job_id")) or detail_map.get(j.get("job_link")) or {}
        return (d.get("jd") or "") + " " + (d.get("skill_tags") or "")

    summary = {"total_raw": len(jobs), "target": len(target), "strict": len(strict),
               "details": len(detail_map), "directions": {}}

    for key, name in DIRS.items():
        js = [j for j in target if j["_dir"] == key]
        if not js:
            summary["directions"][key] = {"name": name, "count": 0}
            continue
        mids = [(j["_p"][0] + j["_p"][1]) / 2 for j in js]
        ann = [((j["_p"][0] + j["_p"][1]) / 2) * j["_p"][2] for j in js]
        months = [j["_p"][2] for j in js]
        exp = Counter()
        deg = Counter()
        for j in js:
            for t in (j.get("tags") or "").split("|"):
                t = t.strip()
                if t in EXP_ORDER:
                    exp[t] += 1
                elif t in DEG_ORDER:
                    deg[t] += 1

        skills = counter_split(js, "skills")
        industry = Counter(j.get("company_industry") for j in js if j.get("company_industry"))
        scale = Counter(j.get("company_scale") for j in js if j.get("company_scale"))
        stage = Counter(j.get("company_stage") for j in js if j.get("company_stage"))
        welfare = counter_split(js, "welfare")

        # 技术/能力信号：skills 标签 + JD 文本（技能标签权重等同出现）
        sig = {}
        for nm, pat in TECH.items():
            n = 0
            for j in js:
                blob = " ".join([j.get("skills") or "", j.get("title") or "", jd_text(j)])
                if re.search(pat, blob, re.I):
                    n += 1
            sig[nm] = n

        jd_n = sum(1 for j in js if jd_text(j).strip())
        title_kw = Counter()
        for j in js:
            for k in ["高级", "资深", "专家", "架构", "负责人", "leader", "Leader", "工程师", "开发"]:
                if k.lower() in (j.get("title") or "").lower():
                    title_kw[k] += 1

        # 代表岗位（按薪资中位+公司规模排序，取前8，便于人工核对）
        reps = sorted(js, key=lambda j: -((j["_p"][0] + j["_p"][1]) / 2))[:8]

        summary["directions"][key] = {
            "name": name, "count": len(js), "with_jd": jd_n,
            "salary": {
                "median_mid": median(mids), "p25": sorted(mids)[len(mids)//4],
                "p75": sorted(mids)[int(len(mids)*3/4)-1],
                "median_annual": median(ann),
                "months_16plus": sum(1 for m in months if m >= 15),
                "months_14plus": sum(1 for m in months if m >= 13.5),
            },
            "experience": exp.most_common(), "degree": deg.most_common(),
            "skills": skills.most_common(30), "industry": industry.most_common(12),
            "scale": scale.most_common(10), "stage": stage.most_common(10),
            "welfare": welfare.most_common(15), "signals": sig,
            "title_kw": title_kw.most_common(10),
            "reps": [{"title": j.get("title"), "salary": j.get("salary"), "company": j.get("boss_name"),
                      "scale": j.get("company_scale"), "tags": j.get("tags"), "skills": j.get("skills"),
                      "industry": j.get("company_industry"), "link": j.get("job_link")} for j in reps],
        }

    # 方向 × 薪资矩阵
    bins = {"15-20K": 0, "20-25K": 0, "25-30K": 0, "30-35K": 0, "35-40K+": 0}
    def binof(m):
        if m < 20: return "15-20K"
        if m < 25: return "20-25K"
        if m < 30: return "25-30K"
        if m < 35: return "30-35K"
        return "35-40K+"
    matrix = {k: {b: 0 for b in bins} for k in DIRS}
    for j in target:
        m = (j["_p"][0] + j["_p"][1]) / 2
        matrix[j["_dir"]][binof(m)] += 1
    summary["salary_matrix"] = matrix
    summary["salary_bins"] = {b: sum(matrix[k][b] for k in matrix) for b in bins}

    os.makedirs(OUT_DIR, exist_ok=True)
    json.dump(summary, open(os.path.join(OUT_DIR, f"market_analysis_{args.tag}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    out_jobs = [{k: v for k, v in j.items() if not k.startswith("_")} | {"direction": DIRS[j["_dir"]]}
                for j in target]
    json.dump({"total": len(target), "jobs": out_jobs},
              open(os.path.join(OUT_DIR, f"market_jobs_{args.tag}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # 均衡采样清单：每个方向按薪资降序交错排列，便于 --max-details 覆盖各方向
    if args.sample:
        per = defaultdict(list)
        for j in sorted(target, key=lambda j: -((j["_p"][0] + j["_p"][1]) / 2)):
            per[j["_dir"]].append(j)
        ordered, quota = [], {k: 14 for k in DIRS}
        for i in range(max(quota.values())):
            for k in DIRS:
                if i < quota[k] and i < len(per[k]):
                    ordered.append({kk: vv for kk, vv in per[k][i].items() if not kk.startswith("_")})
        json.dump({"keyword": "frontend-multi", "city": "上海", "total": len(ordered), "jobs": ordered},
                  open(args.sample, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"采样清单 {len(ordered)} 条 -> {args.sample}")

    print(f"原始 {len(jobs)} | 15-40K 有效 {len(target)} | 严格区间 {len(strict)} | 详情 {len(detail_map)}")
    for k, v in summary["directions"].items():
        print(f"  {v['name']}: {v['count']} 条, 薪资中位 {v.get('salary', {}).get('median_mid')}K")
    print(f"已保存: {OUT_DIR}/market_analysis_{args.tag}.json")


if __name__ == "__main__":
    main()
