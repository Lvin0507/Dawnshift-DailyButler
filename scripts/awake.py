import screen_brightness_control as sbc
import ctypes
import time

def wake_up():
    print("准备解除潜行模式...")
    
    # 1. 恢复 100% 亮度
    try:
        sbc.set_brightness(100)
        print("☀️ 所有显示器亮度已恢复至 100%！")
    except Exception as e:
        print(f"⚠️ 亮度调节失败: {e}")

    # 2. 物理级音量恢复：模拟按“音量加”键
    # Windows 按一次音量加通常是 +2%。
    # 循环 35 次大约恢复到 70% 音量。如果你想拉满到 100%，把 35 改成 50 即可。
    try:
        VK_VOLUME_UP = 0xAF
        for _ in range(50): 
            ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)     # 按下
            ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)     # 松开
            time.sleep(0.01) # 加一丝丝延迟，防止系统吞按键
        print("🔊 系统主音量已恢复！")
    except Exception as e:
        print(f"⚠️ 音量恢复失败: {e}")

    print("☀️ 欢迎回来，声音与亮度已恢复！")

if __name__ == '__main__':
    wake_up()