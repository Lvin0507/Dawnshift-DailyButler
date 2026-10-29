from pathlib import Path
from dotenv import load_dotenv
import html
import time
import os
import subprocess
import requests
import datetime
import glob
import ctypes
from ctypes import wintypes
import shutil
import re
# ==========================================
# 1. Config - secrets and local paths come from .env
# ==========================================
# Load .env from this script's folder (Task Scheduler may start us from another working dir)
load_dotenv(Path(__file__).with_name(".env"))

def require_env(name):
    """Fail fast with a clear message if a required setting is missing from .env."""
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required setting in .env: {name}")
    return value

# Switch files (create the file to turn that game OFF)
SWITCH_FILE = require_env("SWITCH_FILE")
WW_SWITCH_FILE = require_env("WW_SWITCH_FILE")
ARK_SWITCH_FILE = require_env("ARK_SWITCH_FILE")

# Endfield (MaaEnd)
MAA_END_PATH = require_env("MAA_END_PATH")
MAA_LOG_DIR = require_env("MAA_LOG_DIR")
# Only needed when USE_MAAEND_LAUNCH is False
ENDFIELD_LAUNCHER_PATH = os.getenv("ENDFIELD_LAUNCHER_PATH", "")
# Let MaaEnd's built-in "Launch Game (PC)" task start the game
USE_MAAEND_LAUNCH = True

# Wuthering Waves (ok-ww)
OK_WW_PATH = require_env("OK_WW_PATH")
WW_LOG_PATH = require_env("WW_LOG_PATH")

# Arknights (MAA, PC client) - MAA launches the game itself
MAA_ARK_PATH = require_env("MAA_ARK_PATH")
MAA_ARK_LOG = require_env("MAA_ARK_LOG")
MAA_DONE_MARKERS = ["任务已全部完成"]
ARK_GAME_EXE = "Arknights.exe"

# Archived copies of each run's MaaEnd log (MaaEnd overwrites go-service.log on every launch)
ARCHIVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

# Secrets
GEMINI_API_KEY = require_env("GEMINI_API_KEY")
TG_BOT_TOKEN = require_env("TG_BOT_TOKEN")
TG_CHAT_ID = require_env("TG_CHAT_ID")

GEMINI_MODELS = ["gemini-flash-latest", "gemini-flash-lite-latest"]
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# ==========================================
# 2. 功能函数
# ==========================================
def run_until_log_marker(exe_path, app_exe_names, log_path, done_markers, game_exe_name=None, timeout=1800):
    """Start an app that never exits on its own; stop it once its log prints a completion marker.
    Returns (reason, log_text) where log_text contains only what this run wrote."""
    if isinstance(app_exe_names, str):
        app_exe_names = [app_exe_names]
    ts = lambda: datetime.datetime.now().strftime('%H:%M:%S')

    # Remember where the log ends now, so earlier runs are ignored
    offset = os.path.getsize(log_path) if os.path.exists(log_path) else 0
    collected = b""

    print(f"[{ts()}] 正在启动: {exe_path}")
    try:
        subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
    except Exception as e:
        # Don't let a launch failure crash the whole morning run
        print(f"⚠️ 启动失败: {e}")
        return "launch_failed", ""
    start_time = time.time()
    reason = "timeout"
    missing_count = 0

    while time.time() - start_time < timeout:
        time.sleep(15)

        if os.path.exists(log_path):
            size = os.path.getsize(log_path)
            if size < offset:
                offset = 0  # log was truncated or rotated
            if size > offset:
                with open(log_path, "rb") as f:
                    f.seek(offset)
                    chunk = f.read()
                offset += len(chunk)
                collected += chunk
            if any(m in collected.decode("utf-8", errors="ignore") for m in done_markers):
                reason = "done"
                break

        # MAA briefly disappears while self-updating, so require two misses in a row
        running = os.popen('tasklist').read().lower()
        if any(app.lower() in running for app in app_exe_names):
            missing_count = 0
        else:
            missing_count += 1
            if missing_count >= 2:
                reason = "exited"
                break

    print(f"[{ts()}] 结束原因: {reason}")
    time.sleep(10)  # let the app finish writing logs

    for name in app_exe_names + ([game_exe_name] if game_exe_name else []):
        subprocess.run(["taskkill", "/F", "/IM", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)
    return reason, collected.decode("utf-8", errors="ignore")


def parse_maa_log(text, reason):
    """Build the Arknights report directly from this run's MAA log, no AI needed."""
    started = re.findall(r"开始任务: (\S+)", text)
    finished = set(re.findall(r"完成任务: (\S+)", text))
    recruits = len(re.findall(r"已确认招募", text))

    lines = ["『🎯 明日方舟战报』"]
    if not started:
        lines.append("⚠️ MAA 未开始任何任务（游戏未启动或未连接）")

    seen = []
    for name in started:
        if name in seen:
            continue
        seen.append(name)
        status = "✅成功" if name in finished else "❌失败"
        if name == "自动公招" and name in finished:
            status += f"(招募{recruits}次)"
        lines.append(f"{name}：{status}")

    if reason != "done":
        lines.append(f"⚠️ 未检测到全部完成标记（结束原因: {reason}）")
    return "\n".join(lines)

def check_switch(file_path):
    return not os.path.exists(file_path)

def start_endfield_background_click(launcher_path):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 正在调起官方启动器...")
    work_dir = os.path.dirname(launcher_path)
    subprocess.Popen([launcher_path], cwd=work_dir, shell=False)
    
    # 早上冷启动留足 15 秒让启动器加载完界面和网络状态
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 等待 15 秒让启动器加载...")
    time.sleep(15)
    
    def click_launcher():
        hwnd = ctypes.windll.user32.FindWindowW(None, "GRYPHLINK")
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 9)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            time.sleep(0.5)
            
            rect = wintypes.RECT()
            ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect))
            rel_x = int(rect.right * 0.85)
            rel_y = int(rect.bottom * 0.88)
            lparam = (rel_y << 16) | (rel_x & 0xFFFF)
            
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 正在后台向 GRYPHLINK 发送点击指令...")
            ctypes.windll.user32.PostMessageW(hwnd, 0x0201, 1, lparam) # WM_LBUTTONDOWN
            time.sleep(0.05)
            ctypes.windll.user32.PostMessageW(hwnd, 0x0202, 0, lparam) # WM_LBUTTONUP
        else:
            print("⚠️ 未找到 GRYPHLINK 窗口句柄！")

    # 第一次点击启动器
    click_launcher()

    # 💡 核心升级：直接检测 MaaEnd 所需要的 UnityWndClass 游戏窗口是否真正弹出（最多等 120 秒）
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 正在等待游戏窗口 (UnityWndClass - Endfield) 弹出...")
    for i in range(60):
        # 直接查找和 MaaEnd 完全一致的窗口类名与标题
        game_hwnd = ctypes.windll.user32.FindWindowW("UnityWndClass", "Endfield")
        if game_hwnd:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ✅ 已捕获到游戏窗口 (句柄: {game_hwnd})！等待 25 秒加载画面后交由 MaaEnd 接管...")
            time.sleep(25)
            return True
            
        # 防御机制：如果过了 20 秒连 endfield.exe 进程都还没出来（说明早上启动器卡加载没点上），自动补点一次
        if i == 10 and "endfield.exe" not in os.popen('tasklist').read().lower():
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 尚未检测到游戏进程，尝试重新点击一次启动器...")
            click_launcher()
            
        time.sleep(2)
        
    print("⚠️ 警告：120秒内未检测到游戏窗口，尝试强行拉起 MaaEnd...")
    return False

def run_and_monitor(exe_path, app_exe_names, game_exe_name=None, timeout=7200, args=None):
    if isinstance(app_exe_names, str):
        app_exe_names = [app_exe_names]
        
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 正在启动: {exe_path}")
    try:
        cmd = [exe_path]
        if args:
            cmd.extend(args)
            
        work_dir = os.path.dirname(exe_path)
        subprocess.Popen(cmd, cwd=work_dir, shell=False)
        time.sleep(15)
        
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 正在监控 {app_exe_names} 运行状态...")
        start_time = time.time()
        
        while True:
            output = os.popen('tasklist').read().lower()
            is_running = any(app.lower() in output for app in app_exe_names)
            
            if not is_running:
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 检测到核心进程已自行关闭。")
                break
                
            if time.time() - start_time > timeout:
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ⚠ 警告：监控超时，强行击杀...")
                for app in app_exe_names:
                    subprocess.run(["taskkill", "/F", "/IM", app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                break
                
            time.sleep(10) 
            
        if game_exe_name:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 正在清理游戏本体 ({game_exe_name})...")
            subprocess.run(["taskkill", "/F", "/IM", game_exe_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)
            
    except Exception as e:
        print(f"运行监控失败: {e}")

def read_tail_log_endfield(log_dir):
    try:
        output_sections = []
        today_str = datetime.datetime.now().strftime('%Y-%m-%d')
        gui_logs = [os.path.basename(gl) for gl in glob.glob(os.path.join(log_dir, f'{today_str}*.log'))]
        target_files = ['go-service.log'] + gui_logs + ['maafw.log']

        keep_keywords = [
            'msg=Tasker.Task.Starting', 'msg=Tasker.Task.Succeeded', 'msg=Tasker.Task.Failed',
            '任务开始:', '任务完成:', '任务失败:', 'color: #f44', ' entry=',
            '"entry":', 'taskfail/sink.go', 'Task failed', 'FailureCollector', '"level":"error"', '"level":"warn"',
            'Error', 'Exception', '失败', '停止', 'SeizeDeliveryJobs', '送货', '委托', 'Delivery', 'Pretask'
        ]
        
        for file_name in target_files:
            file_path = os.path.join(log_dir, file_name)
            if os.path.exists(file_path):
                file_matched = []
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    scan_limit = 4000 if file_name == 'go-service.log' else 2000
                    noise = ['MinReward node json', 'recognition miss']
                    for line in lines[-scan_limit:]:
                        # Drop repetitive scan noise (each MinReward line is ~2KB of JSON)
                        if any(n in line for n in noise):
                            continue
                        # Keep only one debug line per task: the task-start marker
                        # Keep only two kinds of debug lines: task-start markers and task failures
                        # (some failures, e.g. EnvironmentMonitoringMain, are only logged at debug level)
                        debug_keep = ('Checking aspect ratio before task execution', 'Task failed')
                        if '"level":"debug"' in line and not any(k in line for k in debug_keep):
                            continue
                        if any(k in line for k in keep_keywords):
                            # Cap line length so a single huge line can't bloat the prompt
                            file_matched.append(line.strip()[:400])
                
                if file_matched:
                    # Drop consecutive duplicate lines (ignoring timestamps) - retries and warnings repeat a lot
                    deduped = []
                    last_body = None
                    for line in file_matched:
                        body = line[24:] if len(line) > 24 else line  # skip leading timestamp
                        if body != last_body:
                            deduped.append(line)
                        last_body = body
                    file_matched = deduped
                    keep_limit = 400 if file_name == 'go-service.log' else 300
                    output_sections.append(f"=== [{file_name}] ===\n" + "\n".join(file_matched[-keep_limit:]))
        
        return "\n\n".join(output_sections)
    except Exception as e:
        return f"读取终末地日志报错: {e}"

def read_tail_log_wuthering(log_path):
    try:
        filtered_lines = []
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                keep_kw = ['completed', 'error', 'exception', 'failed', 'traceback', '完成', 'gardentask']
                for line in f:
                    if any(k in line.lower() for k in keep_kw):
                        filtered_lines.append(line.strip())
        return "\n".join(filtered_lines[-300:])
    except Exception as e:
        return f"读取鸣潮日志报错: {e}"

def ai_analyze_logs(end_log, ww_log=None):
    if not GEMINI_API_KEY:
        return "⚠️ 未配置 Gemini API Key。"
    
    prompt_content = f"【终末地核心日志】:\n{end_log}\n\n"
    if ww_log:
        prompt_content += f"【鸣潮核心日志】:\n{ww_log}"
        ww_rules = (
            "第二部分：『🌊 鸣潮战报』\n"
            "1. 【绝对强制】：必须完整输出鸣潮字典中仅有的 2 个任务的状态（✅成功, ❌失败, ⚠️未执行）！一行一个，绝不允许遗漏！\n"
            "2. 【成功判定核心法则】：\n"
            "   - 对于每日任务：看到 'completed' 即为成功。\n"
            "   - 对于每周花园：看到 'completed'、'完成' 或 'Garden current' 相关的结束词汇，即为成功。\n"
        )
    else:
        ww_rules = "今天没有执行鸣潮，不要输出任何鸣潮相关内容。\n"

    prompt = (
        "你是一个精通代肝战报分析的无情机器管家，说话极其精简，绝不废话。\n"
        "【终末地字典：英文代号与中文界面的对应关系】\n"
        "- LaunchGamePC / GameLauncherMain -> 启动游戏（看到 'Pretask succeeded' 或 'game launched' 即成功）\n"
        "- StashBackpackMain -> 存放背包\n"
        "- DijiangRewards -> 基建任务\n"
        "- OutpostTradingSchedule -> 据点贸易\n"
        "- AutoStockStapleSchedule -> 购买稳定物资\n"
        "- AutoStockpileMain -> 自动囤货\n"
        "- DeliveryJobsMain -> 转交委托\n"
        "- SellProductSchedule / AutoSellMain -> 出售类产品\n"
        "- EnvironmentMonitoringMain -> 环境监测\n"
        "- TrialOfSwordmancyMain -> 选剑演武\n"
        "- SeizeDeliveryJobsMain / SeizeDeliveryJobsCheckOngoingJob -> 抢委托送货 / 自行送货\n"
        "- VisitFriendsMain -> 拜访好友 / 客访优先\n"
        "- CreditShoppingMain -> 信用点购物\n"
        "- GiftOperatorMain -> 赠送礼物\n"
        "- DailyRewardStart -> 日常奖励领取\n"
        "- MXU_KILLPROC -> 结束进程\n\n"
        "【鸣潮字典：任务映射】\n"
        "- DailyTask -> 每日任务\n"
        "- GardenTask / weekly garden -> 每周花园\n\n"
        "【你的任务与死命令】：请输出排版清晰的战报。\n"
        "第一部分：『🪐 终末地战报』\n"
        "1. 必须完整输出终末地字典中全部 16 个任务的状态（✅成功, ❌失败, ⚠️未执行），一行一个，不要合并。\n"
        "2. 💡 【终极成败判定法则】：\n"
        "   - 【❌失败判定（最高优先级）】：只要在任何日志中看到某任务对应 'msg=Tasker.Task.Failed'、'任务失败'，或者在 go-service.log 中看到该 entry 出现 'Task failed'（含 'skip feedback hint'）、'taskfail/sink.go'，亦或在其运行期间紧跟了 'FailureCollector subtask failed'，若后续重试未成功，**必须**判定该任务为【❌失败】！\n"
        "   - 【✅成功判定】：因为底层日志可能省略结束标志或发生轮转，只要在日志中看到了某个任务的英文代号（如 '\"entry\":\"StashBackpackMain\"' 或 'entry=StashBackpackMain'），且整个流程中没有命中上述失败条件，就判定为【✅成功】！\n"
        "3. 若成功但带有轻微警告，在状态后括号内极简补充（限10字内）。\n"
        "4. 💡 【精确次数判定】：针对'抢委托送货 / 自行送货'，请仔细扫描日志中的执行次数、当前进度或剩余次数（如 3/3, 1/3 等）。\n"
        "   - 若完美完成 3 次，输出：✅成功(3/3)\n"
        "   - 若仅完成部分（如 1 次），输出：⚠️未执行(1/3) 或 ❌失败(1/3)\n"
        "   - 若日志未记录明确数字，但流程已跑通，输出：✅成功\n\n"
        f"{ww_rules}"
        "绝对禁止输出任何解释性废话！\n\n"
        f"{prompt_content}"
    )
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    # Key goes in the header so it never shows up in URLs or exception messages
    headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
    print(f"[Gemini] prompt length: {len(prompt)} chars")

    max_retries = 5
    backoff = [30, 60, 120, 180]  # seconds to wait after each failed attempt
    last_error = "unknown error"
    for attempt in range(max_retries):
        # Attempts 1-3 use the primary model, 4-5 switch to the lite model
        model = GEMINI_MODELS[0] if attempt < 3 else GEMINI_MODELS[1]
        url = GEMINI_BASE_URL.format(model=model)
        try:
            start = time.time()
            # (connect timeout, read timeout) - model can take 3+ minutes under heavy load
            response = requests.post(url, json=payload, headers=headers, timeout=(10, 300))
            elapsed = time.time() - start
            print(f"[Gemini] attempt {attempt + 1} ({model}): HTTP {response.status_code} in {elapsed:.1f}s")

            try:
                result = response.json()
            except ValueError:
                last_error = f"HTTP {response.status_code}, non-JSON response: {response.text[:200]}"
                result = None

            if result:
                if result.get("candidates"):
                    text = result["candidates"][0]["content"]["parts"][0]["text"]
                    # Mark the report if it came from the fallback model
                    return text if model == GEMINI_MODELS[0] else f"{text}\n\n(备用模型 {model} 生成)"
                if "error" in result:
                    last_error = f"HTTP {response.status_code}: {result['error'].get('message', 'unknown')}"
                else:
                    last_error = f"Unexpected response: {str(result)[:200]}"

        except requests.exceptions.Timeout:
            last_error = "Timed out after 180s"
        except requests.exceptions.RequestException as e:
            last_error = f"{type(e).__name__}: {e}"

        print(f"[Gemini] attempt {attempt + 1} failed: {last_error}")
        if attempt < max_retries - 1:
            time.sleep(backoff[attempt])

    return f"⚠️ Gemini 失败 (已重试{max_retries}次): {last_error}"

def send_tg_msg(text):
    if not TG_BOT_TOKEN: return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def archive_endfield_log(log_dir, archive_dir, keep_days=14):
    """Copy today's go-service.log into the archive folder and prune old copies."""
    try:
        os.makedirs(archive_dir, exist_ok=True)
        src = os.path.join(log_dir, "go-service.log")
        if os.path.exists(src):
            stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
            shutil.copy2(src, os.path.join(archive_dir, f"go-service_{stamp}.log"))
        # Delete archives older than keep_days so the folder doesn't grow forever
        cutoff = time.time() - keep_days * 86400
        for f in glob.glob(os.path.join(archive_dir, "go-service_*.log")):
            if os.path.getmtime(f) < cutoff:
                os.remove(f)
    except Exception as e:
        print(f"⚠️ 日志存档失败: {e}")
# ==========================================
# 3. 主程序逻辑
# ==========================================
if __name__ == "__main__":
    try:
        VK_VOLUME_DOWN = 0xAE
        for _ in range(50):
            ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
            time.sleep(0.01)
        print("🔇 物理静音模式已激活")
    except Exception as e:
        print(f"⚠️ 静音模式激活失败: {e}")

    print("=== Dawnshift 启动 (pagent) ===")
    
    if not check_switch(SWITCH_FILE):
        print("检测到总开关为 [OFF]。准备关机...")
        time.sleep(5)
        subprocess.run(["shutdown", "/s", "/t", "0"])
        exit()
        
    print("检测到总开关为 [ON]。准备打工...")
    
    # ==========================================
    # 1. Endfield: MaaEnd launches the game itself (or fall back to the old launcher click)
    # ==========================================
    if not USE_MAAEND_LAUNCH:
        start_endfield_background_click(ENDFIELD_LAUNCHER_PATH)
    run_and_monitor(MAA_END_PATH, "MaaEnd.exe", "Endfield.exe")
    # MaaEnd starts the launcher too, so still clean it up afterwards
    subprocess.run(["taskkill", "/F", "/IM", "Gryphlink.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)
    archive_endfield_log(MAA_LOG_DIR, ARCHIVE_DIR)
    log_endfield = read_tail_log_endfield(MAA_LOG_DIR)
    log_wuthering = None

        # ==========================================
    # 2. Arknights (MAA, PC client) - runs every day
    # ==========================================
    ark_report = ""
    if check_switch(ARK_SWITCH_FILE):
        print("检测到方舟开关为 [ON]。准备启动 MAA...")
        reason, maa_log = run_until_log_marker(MAA_ARK_PATH, "MAA.exe", MAA_ARK_LOG, MAA_DONE_MARKERS, ARK_GAME_EXE)
        ark_report = parse_maa_log(maa_log, reason)
    else:
        print("方舟开关为 [OFF]，跳过。")

    # 3. 执行鸣潮
    if check_switch(WW_SWITCH_FILE):
        if datetime.datetime.today().weekday() == 0:
            print("检测到鸣潮开关为 [ON] 且今天是 [周一]。准备启动鸣潮...")
            run_and_monitor(OK_WW_PATH, ["ok-ww.exe", "pythonw.exe"], "Client-Win64-Shipping.exe", args=["-t", "GardenTask", "-e"])
            time.sleep(5)
            log_wuthering = read_tail_log_wuthering(WW_LOG_PATH)
        else:
            print(f"今天不是周一，跳过鸣潮。")
            log_wuthering = None
    else:
        print("鸣潮开关为 [OFF]，跳过。")
    
    print("呼叫 AI 总结...")
    report = ai_analyze_logs(log_endfield, log_wuthering)
    # Append the Arknights report (built without AI) after the Gemini report
    full_report = report + (f"\n\n{ark_report}" if ark_report else "")
    final_message = f"<b>⏰ 早晨游戏日常战报 ({datetime.datetime.now().strftime('%m-%d')})</b>\n\n{html.escape(full_report)}"
    print("发送 Telegram...")
    send_tg_msg(final_message)
    
    print("任务全部完成，准备关机。")
    time.sleep(5)
    subprocess.run(["shutdown", "/s", "/t", "0"])