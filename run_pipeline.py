#!/usr/bin/env python3
"""等待手动登录 -> 自动抓取上海前端岗位 -> 18-30K 精筛 -> 生成分析。"""
import os
import sys
import time
import json
import subprocess

PROJ = "/Users/guoxuze/Documents/myproject/boss-zhipin-scraper"
PY = os.path.join(PROJ, ".venv", "bin", "python")
SCRIPT = os.path.join(PROJ, "scripts", "boss_cdp_raw.py")
RESULT_DIR = os.path.expanduser("~/.boss-zhipin-scraper/job-result")
os.makedirs(RESULT_DIR, exist_ok=True)
LOG = os.path.join(PROJ, "run_pipeline.log")


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


sys.path.insert(0, os.path.join(PROJ, "scripts"))
import boss_cdp_raw as b  # noqa: E402


def wait_login(timeout=1500, interval=15):
    log("开始轮询登录态（后台标签页探测，不干扰你手动登录）...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = b.check_login_state(9222)
            if r.status is b.LoginProbeStatus.AVAILABLE:
                log("✅ 检测到登录态且接口返回明文薪资，开始抓取")
                return True
            if r.status is b.LoginProbeStatus.RESTRICTED:
                log(f"❌ 触发风控限制，停止: {b.describe_login_probe_result(r)}")
                return False
            log(f"登录态: {b.describe_login_probe_result(r)} ... 继续等待")
        except Exception as e:
            log(f"探测异常（可重试）: {e}")
        time.sleep(interval)
    log("❌ 等待登录超时")
    return False


def run(cmd, desc):
    log(f"▶ {desc}")
    log("  CMD: " + " ".join(cmd))
    p = subprocess.run(cmd, cwd=PROJ, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True)
    for line in p.stdout.splitlines():
        log("  | " + line)
    log(f"◀ {desc} 退出码={p.returncode}")
    return p.returncode


def main():
    log("=" * 60)
    log("流水线启动：上海 · 前端 · 18-30K 市场分析")
    log("=" * 60)
    if not wait_login():
        log("登录未完成，流水线终止")
        return 1

    # 抓取：不设 API 薪资粗档，抓全量前端岗位后本地按明文薪资精筛 18-30K
    # 关键词用「前端」覆盖 前端开发/前端工程师/Web前端 等
    # --output 需传完整文件名；省略则由脚本自动生成 boss_jobs_*.json 到默认结果目录
    base = [PY, SCRIPT, "--keyword", "前端", "--city", "上海",
            "--pages", "8", "--detail", "--analysis", "--format", "json"]
    rc = run(base, "抓取上海前端岗位（含JD详情，8页）")
    if rc != 0:
        log("抓取返回非零，但仍尝试分析已有数据")

    log("✅ 抓取阶段完成，请查看 run_pipeline.log 与结果目录")
    log(f"结果目录: {RESULT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
