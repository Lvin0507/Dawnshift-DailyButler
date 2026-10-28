import screen_brightness_control as sbc
import ctypes
import time

def force_dark_and_silent():
    print("准备进入赛博潜行模式...")
    
    # 1. 物理级防漏音：模拟狂按 50 次“音量减”键，确保音量彻底归零！
    # 避开直接静音键(Mute)，防止本来就静音的情况下被反向解除静音
    try:
        VK_VOLUME_DOWN = 0xAE
        for _ in range(50):
            ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)     # 按下
            ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)     # 松开
            time.sleep(0.01) # 加一丝丝延迟，防止系统吞按键
        print("🔇 系统主音量已强制归零！")
    except Exception as e:
        print(f"⚠️ 静音失败: {e}")

    # 2. 强制全显示器亮度归零
    try:
        sbc.set_brightness(0)
        print("🌙 所有显示器（含笔记本内屏）已降至极致暗度！")
    except Exception as e:
        print(f"⚠️ 亮度调节失败: {e}")

if __name__ == '__main__':
    force_dark_and_silent()