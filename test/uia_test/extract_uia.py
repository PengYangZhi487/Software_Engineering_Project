import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception as e:
    print("DPI 感知设置失败:", e)

import time
import pywinauto
from pywinauto import Application

# 2.1 连接Chrome窗口
handles = pywinauto.findwindows.find_windows(
    title_re=".*Chrome.*",
    class_name="Chrome_WidgetWin_1"
)
if not handles:
    print("未找到 Chrome 窗口，请确认 Chrome 已打开")
    exit()

app = Application(backend="uia")
app.connect(handle=handles[0])

# ✅ 正确写法：用 handle 直接获取窗口包装对象
dlg = app.window(handle=handles[0])

# 2.2 遍历UIA树提取可点击元素
CLICKABLE_TYPES = {"Button", "Hyperlink", "Edit", "ListItem", "TabItem", "MenuItem"}

def extract_clickable_elements(dlg, max_elements=50, max_depth=15):
    t0 = time.perf_counter()
    elements = []
    
    for ctrl in dlg.descendants():
        try:
            ct = ctrl.element_info.control_type
            if ct not in CLICKABLE_TYPES:
                continue
            rect = ctrl.rectangle()
            # 过滤掉不可见或尺寸异常的元素
            if rect.width() <= 0 or rect.height() <= 0:
                continue
            # 过滤掉屏幕外的元素
            if rect.bottom < 0 or rect.right < 0:
                continue
            elements.append({
                "name": ctrl.window_text(),
                "rect": rect,
                "type": ct,
                "ctrl": ctrl,
            })
            if len(elements) >= max_elements:
                break
        except Exception:
            continue
    
    t1 = time.perf_counter()
    elapsed_ms = (t1 - t0) * 1000
    return elements, elapsed_ms

# 2.3 记录识别耗时并输出
elements, uia_ms = extract_clickable_elements(dlg)
print(f"UIA识别: {uia_ms:.1f}ms, {len(elements)}个元素")
for el in elements:
    print(f"[{el['type']}] {el['name']} - {el['rect']}")

import ctypes
import time

def move_cursor_to_element(rect):
    cx = (rect.left + rect.right) // 2
    cy = (rect.top + rect.bottom) // 2
    ctypes.windll.user32.SetCursorPos(cx, cy)

# 找出第一个“Button”类型的元素，把鼠标移过去
for el in elements:
    if el['type'] == 'Button' and el['name'] != 'Minimize':
        print(f"正在移动鼠标到 '{el['name']}'...")
        move_cursor_to_element(el['rect'])
        time.sleep(2)  # 等2秒，让你肉眼观察
        break