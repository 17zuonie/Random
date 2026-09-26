# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import darkdetect
from typing import Union
from RandomConfig import cfg
from psutil import process_iter, Process
from PyQt5.QtGui import QColor, QDesktopServices, QIcon, QPainter
from PyQt5.QtCore import Qt, pyqtSignal, QUrl
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFrame
from qfluentwidgets import Dialog, setTheme, Theme, setThemeColor, FluentStyleSheet, TextWrap, PrimaryPushButton, \
    BodyLabel, HyperlinkButton, qconfig, FluentFontIconBase, isDarkTheme, SpinBox
from qfluentwidgets.components.settings.setting_card import SettingIconWidget
from qframelesswindow import FramelessDialog


class FluentFontIcon(FluentFontIconBase):

    def path(self, theme=Theme.AUTO):
        return "Font/SegoeIcons.ttf"


class SettingCard(QFrame):
    def __init__(self, icon: Union[str, QIcon], title, content=None, parent=None):
        super().__init__(parent=parent)
        self.iconLabel = SettingIconWidget(icon, self)
        self.titleLabel = QLabel(title, self)
        self.contentLabel = QLabel(content or '', self)
        self.hBoxLayout = QHBoxLayout(self)
        self.vBoxLayout = QVBoxLayout()

        if not content:
            self.contentLabel.hide()

        self.setFixedHeight(70 if content else 50)
        self.iconLabel.setFixedSize(16, 16)

        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.setContentsMargins(16, 0, 0, 0)
        self.hBoxLayout.setAlignment(Qt.AlignVCenter)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setAlignment(Qt.AlignVCenter)

        self.hBoxLayout.addWidget(self.iconLabel, 0, Qt.AlignLeft)
        self.hBoxLayout.addSpacing(16)

        self.hBoxLayout.addLayout(self.vBoxLayout)
        self.vBoxLayout.addWidget(self.titleLabel, 0, Qt.AlignLeft)
        self.vBoxLayout.addWidget(self.contentLabel, 0, Qt.AlignLeft)

        self.hBoxLayout.addSpacing(16)
        self.hBoxLayout.addStretch(1)

        self.contentLabel.setObjectName('contentLabel')
        FluentStyleSheet.SETTING_CARD.apply(self)

    def setTitle(self, title: str):
        self.titleLabel.setText(title)

    def setContent(self, content: str):
        self.contentLabel.setText(content)
        self.contentLabel.setVisible(bool(content))

    def setValue(self, value):
        pass

    def setIconSize(self, width: int, height: int):
        self.iconLabel.setFixedSize(width, height)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)

        if isDarkTheme():
            painter.setBrush(QColor(255, 255, 255, 13))
            painter.setPen(QColor(0, 0, 0, 50))
        else:
            painter.setBrush(QColor(255, 255, 255, 170))
            painter.setPen(QColor(0, 0, 0, 19))

        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)


class SimpleSpinBoxSettingCard(SettingCard):

    def __init__(self, icon: Union[str, QIcon], title, content=None, parent=None,
                 value=40, minimum=2, maximum=999):
        super().__init__(icon, title, content, parent)
        self.spinBox = SpinBox(self)
        self.spinBox.setFixedWidth(130)
        self.spinBox.setAccelerated(True)
        self.spinBox.setMaximum(maximum)
        self.spinBox.setMinimum(minimum)
        self.spinBox.setValue(value)

        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.spinBox, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

    @property
    def value(self):
        return self.spinBox.value()

    @value.setter
    def value(self, v):
        self.spinBox.setValue(v)


class Ui_MessageBox:

    yesSignal = pyqtSignal()
    cancelSignal = pyqtSignal()

    def _setUpUi(self, title, content, parent):
        self.content = content
        self.titleLabel = QLabel(title, parent)
        self.contentLabel = BodyLabel(content, parent)

        self.buttonGroup = QFrame(parent)
        self.yesButton = PrimaryPushButton("确定", self.buttonGroup)
        self.cancelButton = QPushButton("取消", self.buttonGroup)

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
        """ set whether the content is copyable """
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


class WelcomeDialog(FramelessDialog, Ui_MessageBox):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._setUpUi("欢迎使用 Random", "\n设置随机总数以继续。", self)

        self.valueCard = SimpleSpinBoxSettingCard(
            FluentFontIcon("\ue716"),
            "人数",
            "更改随机总数",
            self,
            value=cfg.Value.value,
            minimum=2,
            maximum=999
        )

        self.helpBtn = HyperlinkButton(self)
        self.helpBtn.setIcon(FluentFontIcon("\uea6b"))
        self.helpBtn.setText("查看完整帮助")
        self.helpBtn.clicked.connect(self.onHelpBtn)

        self.textLayout.addWidget(self.valueCard)
        self.textLayout.addWidget(self.helpBtn, alignment=Qt.AlignHCenter)

        self.yesButton.setText("保存")
        self.cancelButton.setText("跳过")

        self.setMinimumSize(500, 300)
        self.resize(500, 300)

        self.windowTitleLabel = QLabel("Random", self)
        self.vBoxLayout.insertWidget(0, self.windowTitleLabel, 0, Qt.AlignTop)
        self.windowTitleLabel.setObjectName('windowTitleLabel')

        self.setResizeEnabled(False)
        self.titleBar.hide()
        FluentStyleSheet.DIALOG.apply(self)

    @property
    def value(self):
        return self.valueCard.value

    def onHelpBtn(self):
        if os.path.exists(os.path.abspath("./Doc/RandomHelp.html")):
            os.startfile(os.path.abspath("./Doc/RandomHelp.html"))
        else:
            QDesktopServices.openUrl(QUrl("https://sudo0015.github.io/post/Random%20-bang-zhu.html"))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Random")
        self.resize(400, 300)


class App:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.main_window = MainWindow()
        setThemeColor(QColor(9, 81, 41))
        self.checkFirstRun()
        if str(subprocess.run(['tasklist'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, shell=True)).find("RandomMain.exe") != -1:
            self.showDialog()
        else:
            subprocess.run(["RandomMain.exe", "--force-start"], shell=True)
            sys.exit()

    def checkFirstRun(self):
        if not os.path.exists(os.path.join(os.path.expanduser('~'), '.Random', 'config', 'config.json')):
            w = WelcomeDialog()
            if w.exec():
                qconfig.set(cfg.Value, w.value)
                cfg.save()

    def killProcess(self, process_name):
        for proc in process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == process_name.lower():
                    pid = proc.info['pid']
                    p = Process(pid)
                    p.kill()
            except:
                pass

    def showDialog(self):
        w = Dialog("提示", "Random 已在后台运行")
        w.yesButton.setText("重启")
        w.cancelButton.setText("取消")
        if w.exec():
            self.killProcess("RandomMain.exe")
            subprocess.run(["RandomMain.exe", "--force-start"], shell=True)
            sys.exit()
        else:
            sys.exit()

    def run(self):
        sys.exit(self.app.exec())


if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    if darkdetect.isDark():
        setTheme(Theme.DARK)
    else:
        setTheme(Theme.LIGHT)
    app = App()
    app.run()