import ctypes
import os

# 1. DPI 感知（必须在导入 Qt/pywinauto 之前）
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception as e:
    print("DPI 感知设置失败:", e)

# 2. 200% 缩放保险
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"

import sys
import time
import pywinauto
from pywinauto import Desktop
from ctypes import wintypes

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QRect, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QGuiApplication

# ============================================================
# 第五步 5.1：SendInput 模拟鼠标点击
# ============================================================
# 在 64 位系统上 dwExtraInfo 是 8 字节，32 位是 4 字节
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUTunion(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUTunion),
    ]


INPUT_MOUSE = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000

def click_at(x, y):
    user32 = ctypes.windll.user32
    screen_w = user32.GetSystemMetrics(0)  # 主屏宽度（物理像素）
    screen_h = user32.GetSystemMetrics(1)

    # 归一化到 0-65535
    nx = int(x * 65535 / screen_w)
    ny = int(y * 65535 / screen_h)

    inputs = (INPUT * 3)()
    # 1. 绝对移动
    inputs[0].type = INPUT_MOUSE
    inputs[0].union.mi = MOUSEINPUT(nx, ny, 0,
                                    MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, 0)
    # 2. 左键按下
    inputs[1].type = INPUT_MOUSE
    inputs[1].union.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, 0)
    # 3. 左键释放
    inputs[2].type = INPUT_MOUSE
    inputs[2].union.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, 0)

    result = user32.SendInput(3, ctypes.byref(inputs), ctypes.sizeof(INPUT))
    if result != 3:
        print(f"SendInput failed. Returned {result}, error: {ctypes.get_last_error()}")


# ============================================================
# 2.2 UIA 元素提取
# ============================================================
CLICKABLE_TYPES = {"Button", "Hyperlink", "Edit", "ListItem", "TabItem", "MenuItem"}


def extract_clickable_elements(dlg, max_elements=50):
    t0 = time.perf_counter()
    elements = []
    for ctrl in dlg.descendants():
        try:
            ct = ctrl.element_info.control_type
            if ct not in CLICKABLE_TYPES:
                continue
            rect = ctrl.rectangle()
            if rect.width() <= 0 or rect.height() <= 0:
                continue
            if rect.bottom < 0 or rect.right < 0:
                continue
            elements.append({
                "name": ctrl.window_text(),
                "rect": rect,
                "type": ct,
            })
            if len(elements) >= max_elements:
                break
        except Exception:
            continue
    t1 = time.perf_counter()
    return elements, (t1 - t0) * 1000


# ============================================================
# 第四步 4.1 + 4.2：覆盖层（含第五步按键触发、第六步计时）
# ============================================================
class Overlay(QWidget):
    def __init__(self, elements):
        super().__init__()
        self.elements = elements
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        # 保存上一轮按下的键，用于识别“新按下”
        self._last_keys = set()

        # 每 50ms 轮询键盘（检测 Esc + A-Z）
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_keys)
        self.timer.start(50)

        screen = QGuiApplication.primaryScreen()
        self.setGeometry(screen.geometry())
        self.show()

    # ---------- 键盘轮询 ----------
    def poll_keys(self):
        user32 = ctypes.windll.user32
        pressed_now = set()

        # Esc（VK = 0x1B）
        if user32.GetAsyncKeyState(0x1B) & 0x8000:
            pressed_now.add("ESC")

        # A-Z（VK = 0x41..0x5A）
        for vk in range(0x41, 0x5B):
            if user32.GetAsyncKeyState(vk) & 0x8000:
                pressed_now.add(chr(vk))

        # 只处理“本轮新按下”的键
        new_pressed = pressed_now - self._last_keys
        self._last_keys = pressed_now

        for key in new_pressed:
            if key == "ESC":
                print("检测到 Esc，退出程序")
                QApplication.quit()
            elif "A" <= key <= "Z":
                self.trigger_click(key)

    # ---------- 第五步 5.2：点击 + 计时 ----------
    def trigger_click(self, letter):
        idx = ord(letter) - ord("A")
        if idx >= len(self.elements):
            print(f"字母 {letter} 没有对应元素（共 {len(self.elements)} 个）")
            return

        el = self.elements[idx]
        r = el["rect"]
        cx = (r.left + r.right) // 2
        cy = (r.top + r.bottom) // 2

        # 临时隐藏覆盖层
        self.hide()
        QApplication.processEvents()
        time.sleep(0.05)

        # 第六步 6.2：点击执行耗时测量
        t0 = time.perf_counter()
        click_at(cx, cy)
        t1 = time.perf_counter()

        self.show()

        print(
            f"已点击 [{el['type']}] {repr(el['name'])} "
            f"@({cx},{cy}) 耗时 {(t1 - t0) * 1000:.2f} ms"
        )

    # ---------- 4.2 绘制高亮 ----------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        for i, el in enumerate(self.elements[:26]):
            r = el["rect"]
            qr = QRect(r.left, r.top, r.right - r.left, r.bottom - r.top)

            painter.setPen(QPen(QColor(0, 120, 255, 200), 2))
            painter.setBrush(QColor(0, 120, 255, 30))
            painter.drawRect(qr)

            label = chr(65 + i)
            painter.setFont(QFont("Consolas", 12, QFont.Bold))
            painter.setPen(QColor(255, 255, 255))
            painter.setBrush(QColor(0, 120, 255, 220))
            label_rect = QRect(qr.left(), qr.top() - 20, 24, 20)
            painter.drawRect(label_rect)
            painter.drawText(label_rect, Qt.AlignCenter, label)


# ============================================================
# 第六步 6.1：端到端流程
# ============================================================
if __name__ == "__main__":
    # 1. 连接 Chrome
    handles = pywinauto.findwindows.find_windows(
        title_re=".*Chrome.*",
        class_name="Chrome_WidgetWin_1"
    )
    if not handles:
        print("未找到 Chrome 窗口")
        sys.exit(1)

    dlg = Desktop(backend="uia").window(handle=handles[0])
    time.sleep(1.0)  # 等待页面稳定
    print("已连接窗口:", dlg.window_text())

    # 2. 识别
    elements, uia_ms = extract_clickable_elements(dlg)
    print(f"UIA识别: {uia_ms:.1f}ms, {len(elements)}个元素")

    # 3. 启动覆盖层
    qapp = QApplication.instance() or QApplication(sys.argv)
    overlay = Overlay(elements)

    print("\n--- KeyMouse 技术原型已启动 ---")
    print("操作说明：")
    print("  A-Z : 点击对应字母高亮框内的元素")
    print("  Esc : 退出程序")
    print("-------------------------------")

    sys.exit(qapp.exec())