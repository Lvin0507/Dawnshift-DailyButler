"""All user-facing text in one place. English is the primary language; Chinese is optional.

Task labels: tools log their own task names (MaaEnd uses English ids, MAA/OneDragon log
Chinese names). LABELS maps those raw names to display text per language; anything not
listed is shown as-is, so a new task in a tool never breaks the report.
"""

LANGUAGES = ("en", "zh")

STRINGS = {
    "en": {
        "report.title": "🌅 Dawnshift report ({date})",
        "status.ok": "✅ Done",
        "status.fail": "❌ Failed",
        "status.skipped": "⚠️ Not run",
        "status.already": "✅ Already done today",
        "status.partial": "⚠️ Partly done",
        "status.warn": "⚠️ Check",
        "status.nothing": "✅ Nothing to pick up (probably done already)",
        "note.no_records": "⚠️ No task records in the log (did the tool run?)",
        "note.no_done_marker": "⚠️ Completion marker not found (ended by: {reason})",
        "note.not_started": "❌ The game did not start ({hint})",
        "note.timeout": "⚠️ Timed out and was stopped after {minutes} min",
        "note.quick_exit": "⚠️ Exited after {minutes} min - probably nothing was due yet",
        "note.finished": "✅ Finished in {minutes} min",
        "note.interrupted": "❌ Interrupted ({reason})",
        "note.error": "⚠️ Unexpected error: {error}",
        "note.new_task": "(new task)",
        "hint.launcher": "check the launcher button position",
        "hint.steam": "check Steam auto-login and the launcher button",
        "hint.baas": "the BAAS launcher may have failed to update",
        "log.skip_day": "{game}: not scheduled today, skipped.",
        "log.skip_off": "{game}: turned off, skipped.",
        "log.wait_reset": "{game}: waiting {minutes} min for the daily reset...",
    },
    "zh": {
        "report.title": "🌅 Dawnshift 战报 ({date})",
        "status.ok": "✅成功",
        "status.fail": "❌失败",
        "status.skipped": "⚠️未执行",
        "status.already": "✅今日已完成",
        "status.partial": "⚠️部分完成",
        "status.warn": "⚠️需确认",
        "status.nothing": "✅无可接委托（今日可能已完成）",
        "note.no_records": "⚠️ 日志里没有任务记录（工具可能没有运行）",
        "note.no_done_marker": "⚠️ 未检测到完成标记（结束原因: {reason}）",
        "note.not_started": "❌ 游戏没有启动（{hint}）",
        "note.timeout": "⚠️ 超时，已在 {minutes} 分钟后强制结束",
        "note.quick_exit": "⚠️ {minutes} 分钟就退出了，可能还没有到期的任务",
        "note.finished": "✅ 已运行完毕（用时 {minutes} 分钟）",
        "note.interrupted": "❌ 中断（{reason}）",
        "note.error": "⚠️ 意外错误: {error}",
        "note.new_task": "（新任务）",
        "hint.launcher": "检查启动器按钮的位置",
        "hint.steam": "检查 Steam 自动登录和启动器按钮",
        "hint.baas": "BAAS 启动器可能更新失败",
        "log.skip_day": "{game}：今天不在排程内，跳过。",
        "log.skip_off": "{game}：已关闭，跳过。",
        "log.wait_reset": "{game}：等待每日刷新（约 {minutes} 分钟）...",
    },
}

GAME_NAMES = {
    "endfield": {"en": "🪐 Arknights: Endfield", "zh": "🪐 终末地"},
    "arknights": {"en": "🎯 Arknights", "zh": "🎯 明日方舟"},
    "wuthering": {"en": "🌊 Wuthering Waves", "zh": "🌊 鸣潮"},
    "bluearchive": {"en": "📘 Blue Archive", "zh": "📘 蔚蓝档案"},
    "zzz": {"en": "⚡ Zenless Zone Zero", "zh": "⚡ 绝区零"},
}

LABELS = {
    "endfield": {
        "LaunchGamePC": {"en": "Launch game", "zh": "启动游戏"},
        "StashBackpackMain": {"en": "Stash backpack", "zh": "存放背包"},
        "DijiangRewards": {"en": "Base rewards", "zh": "基建任务"},
        "OutpostTradingSchedule": {"en": "Outpost trading", "zh": "据点贸易"},
        "AutoStockStapleSchedule": {"en": "Buy staple goods", "zh": "购买稳定物资"},
        "AutoStockpileMain": {"en": "Auto stockpile", "zh": "自动囤货"},
        "DeliveryJobsMain": {"en": "Hand in deliveries", "zh": "转交委托"},
        "AutoSellMain": {"en": "Sell products", "zh": "出售类产品"},
        "EnvironmentMonitoringMain": {"en": "Environment monitoring", "zh": "环境监测"},
        "TrialOfSwordmancyMain": {"en": "Trial of Swordmancy", "zh": "选剑演武"},
        "SeizeDeliveryJobs": {"en": "Delivery jobs", "zh": "抢委托送货"},
        "VisitFriendsMain": {"en": "Visit friends", "zh": "拜访好友"},
        "CreditShoppingMain": {"en": "Credit shop", "zh": "信用点购物"},
        "GiftOperatorMain": {"en": "Gift operators", "zh": "赠送礼物"},
        "DailyRewardStart": {"en": "Daily rewards", "zh": "日常奖励领取"},
        "MXU_KILLPROC": {"en": "Close game", "zh": "结束进程"},
    },
    "arknights": {
        "开始唤醒": {"en": "Start up"},
        "自动公招": {"en": "Recruitment"},
        "基建换班": {"en": "Base shifts"},
        "信用收支": {"en": "Credit store"},
        "理智作战": {"en": "Combat (sanity)"},
        "领取奖励": {"en": "Rewards"},
        "刷理智": {"en": "Sanity farming"},
        "自动肉鸽": {"en": "Integrated Strategies"},
    },
    "wuthering": {
        "garden": {"en": "Weekly garden", "zh": "每周花园"},
    },
    "bluearchive": {
        "baas": {"en": "BAAS dailies", "zh": "BAAS 日常"},
    },
    "zzz": {
        "兑换码": {"en": "Redeem codes"},
        "邮件": {"en": "Mail"},
        "每日签到": {"en": "Daily check-in"},
        "录像店营业": {"en": "Video store"},
        "咖啡店": {"en": "Coffee shop"},
        "活跃度奖励": {"en": "Activity rewards"},
        "丽都城募": {"en": "Inter-knot rewards"},
        "丽都周纪 (领奖励)": {"en": "Weekly rewards"},
        "体力刷本": {"en": "Stamina farming"},
        "一条龙": {"en": "One-dragon run", "zh": "一条龙"},
    },
}


def t(lang, key, **kwargs):
    """Look up a UI/report string, falling back to English, then to the key itself."""
    text = STRINGS.get(lang, {}).get(key) or STRINGS["en"].get(key) or key
    return text.format(**kwargs) if kwargs else text


def game_name(game, lang):
    names = GAME_NAMES.get(game, {})
    return names.get(lang) or names.get("en") or game


def task_label(game, raw, lang):
    """Display name for a task. Chinese tool names fall back to themselves for zh."""
    entry = LABELS.get(game, {}).get(raw, {})
    return entry.get(lang) or (raw if lang == "zh" else entry.get("en")) or raw
