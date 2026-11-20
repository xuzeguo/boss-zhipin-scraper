#!/usr/bin/env python3
"""多关键词抓取：纯前端 / 全栈 / AI Agent / 偏前端细分，合并为总库（不抓详情，快速）。"""
import os
import sys
import json
import time
import shutil
import subprocess

PROJ = "/Users/guoxuze/Documents/myproject/boss-zhipin-scraper"
PY = os.path.join(PROJ, ".venv", "bin", "python")
SCRIPT = os.path.join(PROJ, "scripts", "boss_cdp_raw.py")
RESULT_DIR = os.path.expanduser("~/.boss-zhipin-scraper/job-result")
MASTER = os.path.join(RESULT_DIR, "market_master.json")
SEED = os.path.join(RESULT_DIR, "boss_jobs_20261120_1647.json")
LOG = os.path.join(PROJ, "run_multi.log")
TMP = os.path.join(RESULT_DIR, "_tmp_keyword.json")

# (keyword, pages)
PLAN = [
    ("全栈", 6),
    ("AI Agent", 6),
    ("AI应用开发", 3),
    ("React", 3),
    ("Vue", 3),
    ("大前端", 2),
    ("小程序", 2),
    ("数据可视化", 2),
    ("鸿蒙", 2),
    ("Electron", 1),
    ("Node.js", 2),
    ("低代码", 1),
    ("前端架构", 2),
]


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(cmd, desc):
    log(f"▶ {desc}")
    p = subprocess.run(cmd, cwd=PROJ, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True)
    tail = "\n".join(p.stdout.splitlines()[-8:])
    log("  " + tail.replace("\n", "\n  "))
    log(f"◀ {desc} exit={p.returncode}")
    return p.returncode


def count(path):
    try:
        return len(json.load(open(path, encoding="utf-8")).get("jobs", []))
    except Exception:
        return 0


def main():
    os.makedirs(RESULT_DIR, exist_ok=True)
    log("=" * 60)
    log("多关键词抓取启动（无详情，合并去重）")
    log("=" * 60)

    # 种子：已有「前端」120 条
    if os.path.exists(SEED) and not os.path.exists(MASTER):
        shutil.copyfile(SEED, MASTER)
        log(f"种子数据 {count(MASTER)} 条 -> master")

    for kw, pages in PLAN:
        log(f"===== 关键词「{kw}」 {pages} 页 =====")
        cmd = [PY, SCRIPT, "--keyword", kw, "--city", "上海",
               "--pages", str(pages), "--no-detail",
               "--output", TMP, "--format", "json", "--merge", MASTER]
        rc = run(cmd, f"抓取「{kw}」")
        # 脚本的 --merge 会把「旧文件 + 本次」写到 --output(临时文件)，需回写为新的累加库
        if rc == 0 and os.path.exists(TMP) and count(TMP) >= count(MASTER):
            shutil.copyfile(TMP, MASTER)
        n = count(MASTER)
        log(f"合并后总库: {n} 条")
        if rc != 0:
            log(f"⚠️「{kw}」返回 {rc}，继续下一个")
        time.sleep(6)

    log(f"✅ 全部完成，总库 {count(MASTER)} 条: {MASTER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
