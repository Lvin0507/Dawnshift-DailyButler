<div align="center">

<img src="assets/gachashift.png" alt="Gachashift" width="160">

# Gachashift

**你睡觉的时候，帮你把游戏日常做完。**

[![Release](https://img.shields.io/github/v/release/Lvin0507/Gachashift)](https://github.com/Lvin0507/Gachashift/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
![Windows](https://img.shields.io/badge/platform-Windows-0078D6)

[English](README.md) · [中文](README.zh.md) · [下载](https://github.com/Lvin0507/Gachashift/releases/latest)

</div>

Gachashift 是一个 Windows 应用。每天早上，它会依序启动五款游戏的自动化工具，从每个工具自己的日志确认哪些任务真的完成了，把简短的战报发到 Telegram，最后关机。

## 下载

到 [Releases](https://github.com/Lvin0507/Gachashift/releases/latest) 下载 `Gachashift-x.y.z.zip`，解压到一个你有写入权限的文件夹（不要放在 Program Files），然后打开 `Gachashift.exe`。App 会一步步带你完成设置。

因为 exe 没有数字签名，Windows 可能会显示“Windows 已保护你的电脑”：按 **更多信息 → 仍要运行** 即可。

你也需要先装好你玩的每款游戏对应的自动化工具（MaaEnd、MAA、ok-ww、BAAS 或 OneDragon），并确认它们自己能正常运行。App 里有每个工具的链接。

## 支持的游戏

| 游戏 | 工具 | 运行内容 |
|---|---|---|
| 终末地 | [MaaEnd](https://github.com/MaaXYZ/MaaEnd) | 启动游戏，执行所有日常任务 |
| 明日方舟（PC 客户端） | [MAA](https://github.com/MaaAssistantArknights/MaaAssistantArknights) | 公招、基建换班、信用商店、领取奖励 |
| 鸣潮（官方或 Steam） | [ok-ww](https://github.com/ok-oldking/ok-wuthering-waves) | 每周乐园，默认每周一 |
| 蔚蓝档案（日服 PC 客户端） | [BAAS](https://github.com/pur1fying/blue_archive_auto_script) | 咖啡厅、课程表、竞技场、扫荡、制造、领取奖励 |
| 绝区零（官方或 Steam） | [OneDragon](https://github.com/OneDragon-Anything/ZenlessZoneZero-OneDragon) | 兑换码、签到、邮件、录像店、咖啡店、领取奖励 |

每款游戏都可以单独开关，也可以各自设定在星期几运行。全部完成后，Gachashift 会发出战报（默认英文，可改成中文）：

```
🌅 Gachashift 战报 (11-10)

『🪐 终末地』
启动游戏：✅成功
基建任务：✅成功
环境监测：❌失败
抢委托送货：✅成功 (3/3)
...

『🎯 明日方舟』
自动公招：✅成功 (x4)
基建换班：✅成功
...

『📘 蔚蓝档案』
BAAS 日常：✅成功
✅ 已运行完毕（用时 14 分钟）

『⚡ 绝区零』
每日签到：✅成功
邮件：✅成功
✅ 全部结束（用时 6 分钟）
```

## 运作方式

Gachashift 本身不玩游戏。每款游戏它都会打开对应的工具，等它跑完，关掉自己打开的所有程序，再读取那个工具自己的日志。战报来自针对每个工具的“开始、成功、失败”记录所写的固定规则，所以同一份日志永远得到同一份战报；规则还不认识的任务会显示为新任务，而不是被默默忽略。

除此之外，它也处理那些工具留给你的部分：点击启动器的开始按钮、等待服务器每日刷新、用正确的权限重启 Steam、运行期间静音（也可以调暗屏幕），以及结束后把一切恢复原状。

如果排程时间到了而你正在用电脑，它会先询问，给你 60 秒决定是否跳过。运行中随时可以在 App 里停止：正在进行的游戏会关掉它的工具和游戏，声音和亮度会恢复，电脑保持开机，战报会列出停止前已完成的部分。

## 需求

- Windows
- 想在手机收到战报的话，需要一个 Telegram bot（可选）
- 你玩的游戏对应的工具，先装好并确认它自己能跑。依照各工具自己的说明设置后，再确认以下几项 Gachashift 依赖的设置：
  - **MaaEnd**：第一个任务是“启动游戏（PC）”，最后一个是“结束进程”
  - **MAA**：连接设置为 PC 客户端，填好“启动游戏”的路径，开启“启动后直接运行”
  - **ok-ww**：设好游戏路径，配置好 GardenTask
  - **BAAS**：开启“启动时运行”，**关闭**“启动时启动模拟器”（Gachashift 会自己打开日服启动器并点击スタート），选择“完成后退出 BAAS”
  - **OneDragon**：设好游戏路径和账号实例，在一条龙清单里开启你要的应用
- Steam 游戏：Steam 必须能自动登录拥有该游戏的账号
- 电脑整晚必须保持开机并保持登录。关掉屏幕没关系；睡眠和锁定画面不行，因为在锁定画面上，任何工具都看不到也点不到东西
- 运行期间不要碰电脑。BAAS 和启动器的点击用的是真实鼠标，移动鼠标会让 BAAS 停下来

## 从源码运行

1. 安装 Python 3.10 或更新的版本（**64 位**；App 的界面套件没有 32 位版本），然后安装依赖：
   ```
   pip install -r requirements.txt
   ```
2. 双击 `Gachashift App.bat`。

接下来交给 App。首页会显示一份简短的设置清单，每一步都有按钮：打开你玩的游戏、告诉 Gachashift 每个工具在哪里、做一次测试运行、连接 Telegram（可选）、设定每天几点运行。每个设置下面都有一行说明，每款游戏的页面也链接到该工具自己的文档。五个步骤都完成后，清单就会收起。

其他页面：

- **运行**：立即全部运行，或测试单款游戏；输出会即时显示
- **排程**：每天运行的任务计划程序任务（使用最高权限，错过时间不会补跑）
- **历史**：过去的运行记录，战报在最后面
- **通用设置**：语言、运行期间的静音／调暗／关机、Telegram 与测试消息
- **外观**：背景图片、面板不透明度、强调色，以及每款游戏的图片。图片是你电脑上的文件，只留在你的电脑，不会上传也不会被打包

运行期间，每一页都会出现 **停止** 按钮。

### 命令行

App 执行的就是这些命令，所以它们也可以单独使用：

```
python -m gachashift                   # 排程运行（有人在用电脑时会先询问）
python -m gachashift --no-shutdown     # 立即全部运行，结束后不关机
python -m gachashift --only zzz        # 只跑一款：endfield、arknights、wuthering、bluearchive 或 zzz
python -m gachashift --dry-run-endfield logs\go-service_<日期>.log
```

加上 `--lang zh` 就会输出中文战报。

## 日志

- `logs/gachashift_<日期>.log`：每次运行时 Gachashift 输出的所有内容，保留 14 天。排程运行没有可见的视窗，所以战报看起来不对时，先看这里。App 的 **历史** 页显示的就是这些文件。
- `logs/go-service_<日期>.log`：存档的 MaaEnd 日志，保留 14 天（MaaEnd 每次启动都会覆盖自己的日志）。

## 已知限制

- **蔚蓝档案的 ✅ 代表 BAAS 正常跑完，不代表每个每日任务都完成了。** BAAS 不会把任务记录写进文件，所以 Gachashift 只知道 BAAS 运行过并正常结束。实际完成哪些任务，取决于你在 BAAS 里开启的任务。
- **OneDragon 每次启动都会自动更新**，遇到需要安装驱动的更新时，会停下来等人点击。每次游戏更新后，手动打开一次 OneDragon，早上的运行就不会卡在那个视窗。
- **鸣潮目前只跑每周乐园。**
- **只支持 Windows**，因为这些工具都只支持 Windows。

## 项目结构

```
gachashift/           程序本体
  __main__.py         命令行（python -m gachashift）
  ui/                 桌面应用（PySide6；python -m gachashift.ui）
  winutil.py          提权运行、任务计划程序、按钮校准、各游戏的设置项
  runner.py           挑选今天的游戏、等待刷新、停止请求、战报、关机
  prompt.py           排程运行前的“即将开始”视窗
  config.py           config.json、默认值，以及从旧版 .env 迁移
  system.py           进程、日志、启动器点击、Steam、锁定画面、静音与亮度
  report.py           结构化的结果与 Telegram 消息
  i18n.py             所有中英文文字
  games/              每款游戏一个模块
Gachashift App.bat    打开 App
config.example.json   config.json 的范本
logs/                 运行日志与存档的 MaaEnd 日志（不纳入 git）
```

## 开发过程中学到的事

做这个项目时遇到的问题，以及解决方法：

- **战报说“超时”，实际错误却是 503。** 一个不加条件的 `except:` 把所有失败都标成超时。记录实际的 HTTP 状态后才发现，是 Gemini 在尖峰时段过载，于是加上逐步拉长的重试间隔和备用模型。
- **API 密钥可能从错误信息中外泄。** 密钥原本放在网址的查询字符串里，而 `requests` 会把网址写进异常信息，这段文字又被发到 Telegram。后来改放在 `x-goog-api-key` 请求头里。
- **一行吵杂的日志让提示词变成 30 万字。** 一个送货任务每次扫描都输出约 2KB 的 JSON；过滤掉这些行（并限制每行长度）后，减到约 1.3 万字。
- **真正的失败被报成成功。** 有些失败只记录在 `debug` 等级，而我自己的过滤器把所有 debug 行都丢掉了。修好之后暴露出更大的问题：让 LLM 从日志判断成功与否，本身就不可靠。
- **所以解析改成了固定规则。** 每个任务都有明确的开始行和失败行，Gachashift 直接检查这些，并标出没见过的任务，而不是默默忽略。第一版用 Gemini 读日志；现在的版本完全不需要 API 密钥。
- **关键词判断也会骗人。** 鸣潮最早的判断只找“完成”之类的几个词，结果把一次失败的运行报成成功。现在只相信 ok-ww 自己明确的完成和失败记录。
- **测试运行读到错的数据。** MaaEnd 每次启动都会覆盖自己的日志，所以再打开一次就把早上的日志洗掉了。现在每次运行的日志都会存档。
- **MAA 从来不会自己退出。** PC 客户端模式没有“完成后退出”的选项，所以 Gachashift 监看 MAA 日志里的完成信息，然后关掉它，而且只读取这次运行期间写入的部分。
- **密钥一开始是写死在代码里的。** 现在所有敏感信息都放在不纳入 git 的 `config.json`，GitHub 的推送保护也会挡下意外提交的密钥。
- **不是每款游戏都能安全地自动化。** NIKKE 的 PC 客户端会忽略所有模拟输入，在真机上通过 ADB 运行则让账号被封了一小时。我选择放弃，而不是去绕过反作弊。
- **脚本需要 1280x720 的视窗，但我玩的时候用全屏。** 蔚蓝档案（Unity）把视窗大小存在注册表里，所以 Gachashift 在启动前写入 1280x720。之后要恢复全屏，却没办法靠注册表做到：游戏的全屏开关并没有存在 Unity 的标准设置里，而早先“保存再恢复”的做法，也在一次运行中断、留下视窗数值后失效了。所以 Gachashift 只设定它需要的视窗大小，我玩的时候按 Alt+Enter。
- **“等待进程结束”等错了进程。** BAAS 的 `.exe` 只是一个启动器，它启动真正的脚本后就退出了。Gachashift 改为追踪所有从工具文件夹里运行的进程，以路径比对，所以不会碰到它自己的 `python.exe`。后来 BAAS 退出后开始留下 `adb.exe`，所以对 BAAS 来说，现在以它的主程序 `pythonw.exe` 结束为准，留下来的进程再一起关掉。
- **重定向工具的输出让它崩溃。** BAAS 的启动器会印出一个由方块字符组成的横幅。输出被导向文件时，Python 退回使用系统的日文代码页（cp932），无法编码这些字符，启动器在启动 BAAS 前就崩溃了。给它一个独立的主控台视窗就解决了。
- **日服客户端不能直接启动。** 单独运行 `BlueArchive.exe` 会在登录时崩溃，而官方启动器没有自动启动的选项。Gachashift 打开启动器，以进程找到它的视窗，点击スタート（用视窗大小的比例表示位置，所以不受 DPI 缩放影响），直到游戏进程出现。
- **真实鼠标的点击可能落在错的视窗上。** Windows 有时会拒绝把视窗带到最前面，有一天早上，本来要点蔚蓝档案启动器的点击，打开的却是终末地的启动器。现在 Gachashift 点击前会确认启动器真的在最前面，不是的话就跳过这次点击。
- **Steam 版绝区零不能直接启动。** 直接启动游戏 exe，它会退出并要求通过 Steam；Steam 接着打开米哈游启动器，还需要点它的开始按钮。Gachashift 通过 `steam://rungameid/` 启动游戏，用和蔚蓝档案一样的方式点击启动器按钮，等游戏运行后才交给 OneDragon。
- **一个没人点得到的 UAC 提示。** 绝区零需要管理员权限。子进程会继承父进程的权限，所以当已提权的脚本启动 Steam 时，游戏会安静地启动；但如果 Steam 早已以一般用户身份在运行（它开机就会启动），启动游戏就会跳出 UAC 提示。UAC 提示运行在一个独立的安全桌面上，脚本刻意无法与它互动，于是运行就卡住了。现在 Gachashift 会用 `steam://exit` 关掉已在运行的 Steam，再自己重新启动它，让整条链都继承管理员权限。Steam 版鸣潮也需要同样的处理：Steam 没准备好时，游戏会在 ok-ww 启动它一分钟后自己关掉。
- **一个只在成功时才退出的工具。** ok-ww 的 `-e` 参数在成功后会退出，但任务出错时会留着不关，还在背景移动鼠标，干扰了下一款游戏。现在 Gachashift 监看工具日志里它自己的完成和失败记录，不论结果如何，结束后都会关掉工具。
- **排程运行没有留下任何记录。** 任务计划程序启动的运行没有可见的主控台，所以第一次绝区零默默什么都没做时，完全无从得知原因。现在 Gachashift 输出的所有内容，也会写进一份以日期命名的日志文件。
- **锁定画面让所有工具都变成瞎子。** 测试从睡眠唤醒时，Windows 醒来停在锁定画面，截图在那里会失败，所以 MaaEnd 卡在那里启动不了游戏。设成唤醒不需要密码可以解决，但会牺牲安全性，所以改成让电脑开着、只关屏幕，并让 Gachashift 先检查锁定画面：如果停在锁定画面，战报会直接说明，而不是卡上几个小时。
- **在你用电脑时启动的运行。** 第一次排程在我用电脑时启动，游戏和工具一个接一个打开，只能一个一个手动关掉。现在排程运行如果发现最近两分钟内有人用过鼠标或键盘，会先询问；运行中的每个等待都会检查停止请求，所以停止会在一秒内生效，而且照样会收拾干净。

## 未来计划

- 原神（通过 [BetterGI](https://github.com/babalae/better-genshin-impact)）

## 基于以下项目

Gachashift 只负责调度这些工具并读取它们的日志，所有实际的游戏自动化都是它们的成果：

- [MaaEnd](https://github.com/MaaXYZ/MaaEnd)：终末地
- [MaaAssistantArknights](https://github.com/MaaAssistantArknights/MaaAssistantArknights)：明日方舟
- [ok-wuthering-waves](https://github.com/ok-oldking/ok-wuthering-waves)：鸣潮
- [BAAS](https://github.com/pur1fying/blue_archive_auto_script)：蔚蓝档案
- [ZenlessZoneZero-OneDragon](https://github.com/OneDragon-Anything/ZenlessZoneZero-OneDragon)：绝区零

本仓库不包含也不散布它们的任何代码。每个项目都有自己的授权，使用前请自行确认。

## 免责声明

仅供学习用途。游戏自动化可能违反游戏的用户协议，并可能导致账号被封禁，风险请自行承担。

## 授权

[MIT](LICENSE)
