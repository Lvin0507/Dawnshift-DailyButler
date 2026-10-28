import time
import pyautogui

print("Move your mouse over the Shop button in NIKKE within 5 seconds...")
time.sleep(5)

# Test 1: instant click (same as most automation scripts)
print("Test 1: instant click")
pyautogui.click()
time.sleep(3)

# Test 2: click with the button held down for 150 ms
print("Test 2: held click (150 ms)")
pyautogui.mouseDown()
time.sleep(0.15)
pyautogui.mouseUp()
print("Done")