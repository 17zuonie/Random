# -*- coding: utf-8 -*-

import os
import re
import sys
import mss
import random
import win32gui
import win32con
import subprocess
import portalocker
import RandomResource
from RandomConfig import cfg
from darkdetect import isDark
from ctypes.wintypes import MSG
from ctypes import windll, byref
from win32con import MOD_CONTROL, MOD_SHIFT, MOD_ALT
from PyQt5.QtGui import QIcon, QMouseEvent, QCursor, QDesktopServices, QColor
from PyQt5.QtCore import Qt, QTimer, QDateTime, pyqtSignal, QThread, QPropertyAnimation, QUrl
from PyQt5.QtWidgets import QAction, QPushButton, QVBoxLayout, QSystemTrayIcon, QWidget, QApplication, QHBoxLayout, \
    QLabel, QFrame
from qfluentwidgets import RoundMenu, setTheme, Theme, BodyLabel, PrimaryPushButton, TextWrap, FluentStyleSheet, \
    FluentFontIconBase, InfoBar, InfoBarPosition
from qframelesswindow import FramelessDialog


def windowEnumerationHandler(hwnd, windowlist):
    windowlist.append((hwnd, win32gui.GetWindowText(hwnd)))


class Mutex:
    def __init__(self):
        self.file = None

    def __enter__(self):
        self.file = open('RandomMain.lockfile', 'w')
        try:
            portalocker.lock(self.file, portalocker.LOCK_EX | portalocker.LOCK_NB)
        except portalocker.AlreadyLocked:
            sys.exit()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            portalocker.unlock(self.file)
            self.file.close()
            os.remove('RandomMain.lockfile')


class FluentFontIcon(FluentFontIconBase):

    def path(self, theme=Theme.AUTO):
        return "Font/SegoeIcons.ttf"


class Ui_MessageBox:

    yesSignal = pyqtSignal()
    cancelSignal = pyqtSignal()

    def _setUpUi(self, title, content, parent):
        self.content = content
        self.titleLabel = QLabel(title, parent)
        self.contentLabel = BodyLabel(content, parent)

        self.buttonGroup = QFrame(parent)
        self.yesButton = PrimaryPushButton(self.tr('OK'), self.buttonGroup)
        self.cancelButton = QPushButton(self.tr('Cancel'), self.buttonGroup)

        self.vBoxLayout = QVBoxLayout(parent)
        self.textLayout = QVBoxLayout()
        self.buttonLayout = QHBoxLayout(self.buttonGroup)

        self.__initWidget()

    def __initWidget(self):
        self.__setQss()
        self.__initLayout()

        self.yesButton.setAttribute(Qt.WA_LayoutUsesWidgetRect)
        self.cancelButton.setAttribute(Qt.WA_LayoutUsesWidgetRect)

        self.yesButton.setFocus()
        self.buttonGroup.setFixedHeight(81)

        self.contentLabel.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._adjustText()

        self.yesButton.clicked.connect(self.__onYesButtonClicked)
        self.cancelButton.clicked.connect(self.__onCancelButtonClicked)

    def _adjustText(self):
        if self.isWindow():
            if self.parent():
                w = max(self.titleLabel.width(), self.parent().width())
                chars = max(min(w / 9, 140), 30)
            else:
                chars = 100
        else:
            w = max(self.titleLabel.width(), self.window().width())
            chars = max(min(w / 9, 100), 30)

        self.contentLabel.setText(TextWrap.wrap(self.content, chars, False)[0])

    def __initLayout(self):
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.addLayout(self.textLayout, 1)
        self.vBoxLayout.addWidget(self.buttonGroup, 0, Qt.AlignBottom)
        self.vBoxLayout.setSizeConstraint(QVBoxLayout.SetMinimumSize)

        self.textLayout.setSpacing(12)
        self.textLayout.setContentsMargins(24, 24, 24, 24)
        self.textLayout.addWidget(self.titleLabel, 0, Qt.AlignTop)
        self.textLayout.addWidget(self.contentLabel, 0, Qt.AlignTop)

        self.buttonLayout.setSpacing(12)
        self.buttonLayout.setContentsMargins(24, 24, 24, 24)
        self.buttonLayout.addWidget(self.yesButton, 1, Qt.AlignVCenter)
        self.buttonLayout.addWidget(self.cancelButton, 1, Qt.AlignVCenter)

    def __onCancelButtonClicked(self):
        self.reject()
        self.cancelSignal.emit()

    def __onYesButtonClicked(self):
        self.accept()
        self.yesSignal.emit()

    def __setQss(self):
        self.titleLabel.setObjectName("titleLabel")
        self.contentLabel.setObjectName("contentLabel")
        self.buttonGroup.setObjectName('buttonGroup')
        self.cancelButton.setObjectName('cancelButton')

        FluentStyleSheet.DIALOG.apply(self)
        FluentStyleSheet.DIALOG.apply(self.contentLabel)

        self.yesButton.adjustSize()
        self.cancelButton.adjustSize()

    def setContentCopyable(self, isCopyable: bool):
        if isCopyable:
            self.contentLabel.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse)
        else:
            self.contentLabel.setTextInteractionFlags(
                Qt.TextInteractionFlag.NoTextInteraction)


class Dialog(FramelessDialog, Ui_MessageBox):

    yesSignal = pyqtSignal()
    cancelSignal = pyqtSignal()

    def __init__(self, title: str, content: str, parent=None):
        super().__init__(parent=parent)
        self._setUpUi(title, content, self)

        self.windowTitleLabel = QLabel("Random", self)

        self.setResizeEnabled(False)
        self.resize(240, 192)
        self.titleBar.hide()

        self.vBoxLayout.insertWidget(0, self.windowTitleLabel, 0, Qt.AlignTop)
        self.windowTitleLabel.setObjectName('windowTitleLabel')
        FluentStyleSheet.DIALOG.apply(self)
        self.setFixedSize(self.size())


class HotKeyManager(QThread):
    isPressed = pyqtSignal(str)
    showDialogRequested = pyqtSignal(str)

    def __init__(self, hotkey_str, hotkey_name):
        super(HotKeyManager, self).__init__()
        self.hotkeyName = hotkey_name
        self.modifiers = 0
        self.main_key = 0
        self.isListening = True
        self.parse_hotkey(hotkey_str)

    def parse_hotkey(self, hotkey_str):
        key_map = {
            'ctrl': MOD_CONTROL,
            'shift': MOD_SHIFT,
            'alt': MOD_ALT
        }

        parts = re.split(r'\s*\+\s*', hotkey_str.lower())
        for part in parts[:-1]:
            if part in key_map:
                self.modifiers |= key_map[part]

        main_key = parts[-1]
        special_keys = {
            '`': 0xC0,
            '~': 0xC0,
            'esc': 0x1B
        }
        if main_key in special_keys:
            self.main_key = special_keys[main_key]
        elif main_key.startswith('f') and main_key[1:].isdigit():
            self.main_key = 0x70 + int(main_key[1:]) - 1
        elif len(main_key) == 1:
            self.main_key = ord(main_key.upper())
        else:
            self.main_key = 0

    def run(self):
        while self.isListening:
            hotkey_id = int(self.hotkeyName, 36) % 0xBFFF
            if not windll.user32.RegisterHotKey(None, hotkey_id, self.modifiers, self.main_key):
                self.isListening = False
                self.showDialogRequested.emit(self.hotkeyName)
                return
            try:
                msg = MSG()
                if windll.user32.GetMessageA(byref(msg), None, 0, 0) != 0:
                    if msg.message == win32con.WM_HOTKEY:
                        if msg.wParam == hotkey_id:
                            self.isPressed.emit(self.hotkeyName)
            finally:
                windll.user32.UnregisterHotKey(None, hotkey_id)


class Main(QWidget):

    def __init__(self):
        super().__init__()
        self.value = cfg.Value.value
        self.opacity = cfg.Opacity.value / 100
        self.noRepeat = cfg.NoRepeat.value
        self.position = cfg.Position.value
        self.isShowTime = cfg.ShowTime.value
        self.runHotKey = cfg.RunHotKey.value
        self.showHotKey = cfg.ShowHotKey.value
        self.hideHotKey = cfg.HideHotKey.value
        self.screenShotHotKey = cfg.ScreenShotHotKey.value
        self.topMargin = cfg.TopMargin.value
        self.bottomMargin = cfg.BottomMargin.value
        self.leftMargin = cfg.LeftMargin.value
        self.rightMargin = cfg.RightMargin.value

        self.isOnRandom = False
        self.isTracking = False
        self.arr = [x for x in range(1, self.value + 1)]
        self.desktop = QApplication.screens()[0].size()

        self.setWindowTitle("Random")
        self.setWindowIcon(QIcon(':/icon.png'))
        self.button = QPushButton("Rd")
        self.button.setFixedSize(75, 33)
        self.setFixedSize(100, 50)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setBtnStyleSheet()
        self.button.installEventFilter(self)
        self.button.clicked.connect(self.run)
        self.moveWidget(self.position)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.button)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setAlignment(Qt.AlignCenter)
        self.setLayout(self.layout)

        self._restore_action = QAction()
        self._quit_action = QAction()
        self._tray_icon_menu = RoundMenu()
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(":/icon.png"))
        self.tray_icon.setToolTip("Random")
        self.createActions()
        self.createTrayIcon()
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.trayIconActivated)

        self.setWindowOpacity(self.opacity)
        self.opacityAni = QPropertyAnimation(self, b'windowOpacity', self)
        self.opacityAni.setDuration(1000)
        self.opacityAni.setEndValue(self.opacity)
        self.opacityAni.finished.connect(self.opacityAniFinished)

        self.setupTimer()
        self.setupHotKey()
        self.show()

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton:
            self.isTracking = True
        elif e.button() == Qt.RightButton:
            self._tray_icon_menu.exec(QCursor.pos())

    def mouseMoveEvent(self, e: QMouseEvent):
        self.move(e.pos() + self.pos())

    def mouseReleaseEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton:
            self.isTracking = False

    def closeEvent(self, event):
        event.ignore()

    def setupTimer(self):
        self.onRandomTimer = QTimer()
        self.onRandomTimer.timeout.connect(self.opacityAni.start)
        if self.isShowTime:
            self.updateTime()
            self.timer = QTimer()
            self.timer.start(1000)
            self.timer.timeout.connect(self.updateTime)

    def setupHotKey(self):
        self.hotKeyDict = {"Run": "", "Show": "", "Hide": "", "ScreenShot": ""}
        if cfg.EnableRunHotKey.value and self.runHotKey:
            self.hotKeyDict["Run"] = self.runHotKey
        if cfg.EnableShowHotKey.value and self.showHotKey:
            self.hotKeyDict["Show"] = self.showHotKey
        if cfg.EnableHideHotKey.value and self.hideHotKey:
            self.hotKeyDict["Hide"] = self.hideHotKey
        if cfg.EnableScreenShotHotKey.value and self.screenShotHotKey:
            self.hotKeyDict["ScreenShot"] = self.screenShotHotKey

        self.hotkeyManagers = []
        for name, key in self.hotKeyDict.items():
            if key:
                manager = HotKeyManager(key, name)
                manager.isPressed.connect(self.hotKeyEvent)
                manager.showDialogRequested.connect(self.showHotkeyWarning)
                manager.start()
                self.hotkeyManagers.append(manager)

    def setBtnStyleSheet(self):
        startColor = QColor(cfg.ButtonColorStart.value)
        endColor = QColor(cfg.ButtonColorEnd.value)

        midR = (startColor.red() + endColor.red()) / 2
        midG = (startColor.green() + endColor.green()) / 2
        midB = (startColor.blue() + endColor.blue()) / 2

        luminance = 0.299 * midR + 0.587 * midG + 0.114 * midB
        textColor = "rgb(0, 0, 0)" if luminance > 128 else "rgb(255, 255, 255)"

        startHex = startColor.name()
        endHex = endColor.name()

        self.button.setStyleSheet(
            f'QPushButton {{'
            f'background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, '
            f'stop:0 {startHex}, stop:1 {endHex});'
            f'color: {textColor};'
            f'border-radius: 16px;'
            f'border: 0.5px groove gray;'
            f'border-style: outset;'
            f'font-family: "JetBrains Mono";'
            f'font-size: 15pt;'
            f'font-weight: bold;'
            f'}}'
            f'QPushButton:hover {{'
            f'background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, '
            f'stop:0 {startHex}, stop:1 {endHex});'
            f'}}'
            f'QPushButton:pressed {{'
            f'background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, '
            f'stop:0 {startHex}, stop:1 {endHex});'
            f'}}'
        )

    def moveWidget(self, position):
        if position == "TopLeft":
            self.move(self.leftMargin, self.topMargin)
        elif position == "TopCenter":
            self.move(self.desktop.width() // 2 - self.width() // 2, self.topMargin)
        elif position == "TopRight":
            self.move(self.desktop.width() - self.width() - self.rightMargin, self.topMargin)
        elif position == "BottomLeft":
            self.move(self.leftMargin, self.desktop.height() - self.height() - self.bottomMargin)
        elif position == "BottomCenter":
            self.move(self.desktop.width() // 2 - self.width() // 2, self.desktop.height() - self.height() - self.bottomMargin)
        elif position == "BottomRight":
            self.move(self.desktop.width() - self.width() - self.rightMargin, self.desktop.height() - self.height() - self.bottomMargin)

    def restoreFromTray(self):
        if self.isMinimized():
            self.showNormal()
        elif self.isMaximized():
            self.showMaximized()
        else:
            self.show()

    def trayIconActivated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger or reason == QSystemTrayIcon.ActivationReason.Context:
            self._tray_icon_menu.exec(self.tray_icon.geometry().center())

    def createActions(self):
        self._setting_action = QAction(FluentFontIcon("\ue713").icon(), "设置", self)
        self._help_action = QAction(FluentFontIcon("\uea6b").icon(), "帮助", self)
        self._setting_action.triggered.connect(self._openSetting)
        self._help_action.triggered.connect(self._openHelp)

        self._reset_action = QAction(FluentFontIcon("\ue845").icon(), "复位", self)
        self._topleft_action = QAction("左上", self)
        self._topcenter_action = QAction("上中", self)
        self._topright_action = QAction("右上", self)
        self._bottomleft_action = QAction("左下", self)
        self._bottomcenter_action = QAction("下中", self)
        self._bottomright_action = QAction("右下", self)
        self._reset_action.triggered.connect(lambda: self.moveWidget(cfg.Position.value))
        self._topleft_action.triggered.connect(lambda: self.moveWidget("TopLeft"))
        self._topcenter_action.triggered.connect(lambda: self.moveWidget("TopCenter"))
        self._topright_action.triggered.connect(lambda: self.moveWidget("TopRight"))
        self._bottomleft_action.triggered.connect(lambda: self.moveWidget("BottomLeft"))
        self._bottomcenter_action.triggered.connect(lambda: self.moveWidget("BottomCenter"))
        self._bottomright_action.triggered.connect(lambda: self.moveWidget("BottomRight"))

        runShortCut = self.runHotKey if cfg.EnableRunHotKey.value else ""
        hideShortCut = self.hideHotKey if cfg.EnableHideHotKey.value else ""
        showShortCut = self.showHotKey if cfg.EnableShowHotKey.value else ""
        screenShotShortCut = self.screenShotHotKey if cfg.EnableScreenShotHotKey.value else ""
        self._run_action = QAction(FluentFontIcon("\ue724").icon(), "生成随机数", shortcut=runShortCut, parent=self)
        self._hide_action = QAction(FluentFontIcon("\uecc9").icon(), "隐藏", shortcut=hideShortCut, parent=self)
        self._restore_action = QAction(FluentFontIcon("\uecc8").icon(), "显示", shortcut=showShortCut, parent=self)
        self._run_action.triggered.connect(self.run)
        self._hide_action.triggered.connect(self.hide)
        self._restore_action.triggered.connect(self.restoreFromTray)

        self._capture_screen_action = QAction(FluentFontIcon("\ue722").icon(), "屏幕快照", shortcut=screenShotShortCut, parent=self)
        self._capture_screen_action.triggered.connect(self.captureScreen)
        self._open_screenshot_path = QAction(FluentFontIcon("\ue838").icon(), "打开文件夹", parent=self)
        self._open_screenshot_path.triggered.connect(self.openScreenshotPath)

        self._quit_action = QAction(FluentFontIcon("\ue7e8").icon(), "退出", self)
        self._quit_action.triggered.connect(self.quit)

    def createTrayIcon(self):
        self.subMenu = RoundMenu("移动")
        self.subMenu.setIcon(FluentFontIcon("\ue7c2"))
        self.subMenu.addActions([self._topleft_action, self._topcenter_action, self._topright_action, self._bottomleft_action, self._bottomcenter_action, self._bottomright_action])

        self._tray_icon_menu.addAction(self._run_action)
        self._tray_icon_menu.addSeparator()
        self._tray_icon_menu.addAction(self._capture_screen_action)
        self._tray_icon_menu.addAction(self._open_screenshot_path)
        self._tray_icon_menu.addSeparator()
        self._tray_icon_menu.addMenu(self.subMenu)
        self._tray_icon_menu.addAction(self._reset_action)
        self._tray_icon_menu.addSeparator()
        self._tray_icon_menu.addAction(self._setting_action)
        self._tray_icon_menu.addAction(self._help_action)
        self._tray_icon_menu.addSeparator()
        self._tray_icon_menu.addAction(self._restore_action)
        self._tray_icon_menu.addAction(self._hide_action)
        self._tray_icon_menu.addSeparator()
        self._tray_icon_menu.addAction(self._quit_action)
        self.tray_icon.setContextMenu(self._tray_icon_menu)
        self.tray_icon.show()

    def quit(self):
        self.hide()

        if hasattr(self, 'hotkeyManagers'):
            for manager in self.hotkeyManagers:
                manager.isListening = False
                manager.quit()
                manager.wait(1000)

        for manager in self.hotkeyManagers:
            manager.isListening = False
            manager.terminate()
        self.tray_icon.hide()
        self.tray_icon.deleteLater()
        QApplication.quit()
        sys.exit()

    def hotKeyEvent(self, hotkeyName):
        if hotkeyName == "Run":
            self.run()
        elif hotkeyName == "Show":
            self.restoreFromTray()
        elif hotkeyName == "Hide":
            self.hide()
        elif hotkeyName == "ScreenShot":
            self.captureScreen()

    def showHotkeyWarning(self, hotkeyName):
        if hotkeyName == "Run":
            error = "生成随机数"
        elif hotkeyName == "Show":
            error = "显示"
        elif hotkeyName == "Hide":
            error = "隐藏"
        elif hotkeyName == "ScreenShot":
            error = "屏幕快照"

        w = Dialog("警告", f"检测到快捷键冲突: {error}", self)
        w.yesButton.setText("转到设置")
        w.cancelButton.setText("忽略")
        w.setFixedWidth(300)
        w.move(self.desktop.width() // 2 - w.width() // 2, self.desktop.height() // 2 - w.height() // 2)
        if w.exec():
            subprocess.Popen("RandomSetting.exe", shell=True)
        else:
            pass

    def updateTime(self):
        if not self.isOnRandom:
            self.button.setText(QDateTime.currentDateTime().toString('hh:mm'))

    def opacityAniFinished(self):
        self.isOnRandom = False
        self.opacityAni.stop()

    def run(self):
        if self.opacityAni.Running:
            self.opacityAni.stop()
        self.setWindowOpacity(1)

        num = random.choice(self.arr)
        self.button.setText(str(num))
        if self.noRepeat:
            self.arr.remove(num)
            if not self.arr:
                self.arr = [x for x in range(1, self.value + 1)]

        self.isOnRandom = True
        if self.onRandomTimer.isActive():
            self.onRandomTimer.stop()
            self.onRandomTimer.start(5000)
        else:
            self.onRandomTimer.start(5000)

        windowlist = []
        win32gui.EnumWindows(windowEnumerationHandler, windowlist)
        for i in windowlist:
            if "幻灯片放映" in i[1].lower():
                win32gui.ShowWindow(i[0], 4)
                win32gui.SetForegroundWindow(i[0])
                break

    def captureScreen(self):
        WDA_EXCLUDEFROMCAPTURE = 0x00000011
        hwnd = int(self.winId())

        affinity_ok = False
        if cfg.IsAutoHide.value:
            try:
                affinity_ok = bool(windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE))
            except Exception:
                affinity_ok = False
            if not affinity_ok:
                self.hide()
                QApplication.processEvents()

        with mss.mss() as sct:
            monitor = sct.monitors[0]
            screenshot = sct.grab(monitor)

            fileName = QDateTime.currentDateTime().toString('yyyyMMddhhmmsszzz') + ".png"
            path = os.path.join(cfg.ScreenShotPath.value, fileName)
            if not os.path.exists(cfg.ScreenShotPath.value):
                os.makedirs(cfg.ScreenShotPath.value, exist_ok=True)

            mss.tools.to_png(screenshot.rgb, screenshot.size, output=path)

        if cfg.IsAutoHide.value:
            if affinity_ok:
                windll.user32.SetWindowDisplayAffinity(hwnd, 0)
            else:
                self.show()

        InfoBar.success(
            title='截图成功',
            content="",
            orient=Qt.Horizontal,
            isClosable=False,
            duration=2000,
            position=InfoBarPosition.TOP,
            parent=InfoBar.desktopView()
        )

    def _restoreTopMost(self):
        try:
            hwnd = int(self.winId())
            HWND_TOPMOST = -1
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            SWP_SHOWWINDOW = 0x0040
            windll.user32.SetWindowPos(
                hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            )
        except Exception:
            pass

    def _openSetting(self):
        subprocess.Popen("RandomSetting.exe", shell=True)
        QTimer.singleShot(100, self._restoreTopMost)

    def _openHelp(self):
        os.startfile(os.path.abspath("./Doc/RandomHelp.html"))
        QTimer.singleShot(100, self._restoreTopMost)

    def openScreenshotPath(self):
        path = cfg.ScreenShotPath.value
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        QTimer.singleShot(100, self._restoreTopMost)


if __name__ == "__main__":
    if (len(sys.argv) == 2 and sys.argv[1] == '--force-start') or cfg.AutoRun.value:
        with Mutex():
            QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
            if isDark():
                setTheme(Theme.DARK)
            else:
                setTheme(Theme.LIGHT)
            app = QApplication(sys.argv)
            widget = Main()
            widget.show()
            sys.exit(app.exec())
    else:
        sys.exit()
