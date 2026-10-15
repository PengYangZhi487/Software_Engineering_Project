from pywinauto import Desktop

desktop = Desktop(backend="uia")
# 连接 Chrome 窗口
chrome = desktop.window(title_re=".*Chrome.*")
chrome.wait("visible", timeout=10)
chrome.set_focus()

print("=== 开始搜索网页元素 ===")

# 1. 搜索 Button（按钮）
print("\n--- Button ---")
for ctrl in chrome.descendants(control_type="Button"):
    try:
        print(f"文本: {repr(ctrl.window_text())}, 坐标: {ctrl.rectangle()}")
    except Exception:
        pass

# 2. 搜索 Hyperlink（链接）
print("\n--- Hyperlink ---")
for ctrl in chrome.descendants(control_type="Hyperlink"):
    try:
        print(f"文本: {repr(ctrl.window_text())}, 坐标: {ctrl.rectangle()}")
    except Exception:
        pass

# 3. 搜索 Edit（输入框）
print("\n--- Edit ---")
for ctrl in chrome.descendants(control_type="Edit"):
    try:
        print(f"文本: {repr(ctrl.window_text())}, 坐标: {ctrl.rectangle()}")
    except Exception:
        pass