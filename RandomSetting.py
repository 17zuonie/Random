# -*- coding: utf-8 -*-

import os
import re
import sys
import subprocess
import darkdetect
import portalocker
import RandomResource
from enum import Enum
from typing import Union
from psutil import process_iter, Process
from RandomConfig import cfg, VERSION, YEAR
from pygetwindow import getWindowsWithTitle as GetWindow
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QEasingCurve, QEvent, QTimer, QModelIndex, QObject, QRunnable, \
    QThreadPool, QUrl
from PyQt5.QtGui import QColor, QIcon, QPainter, QTextCursor, QPainterPath, QKeySequence, QDesktopServices
from PyQt5.QtWidgets import QFrame, QApplication, QWidget, QHBoxLayout, QLabel, QVBoxLayout, QPushButton, \
    QTextBrowser, QTextEdit, QLineEdit, QSpinBox, QScrollArea, QScroller, QAction, QFileDialog, QCompleter, QSizePolicy
from qfluentwidgets import NavigationItemPosition, SubtitleLabel, MessageBox, ExpandLayout, MaskDialogBase, \
    SettingCardGroup, ComboBox, SwitchButton, IndicatorPosition, qconfig, TextWrap, InfoBarIcon, PrimaryPushButton, \
    isDarkTheme, ConfigItem, OptionsConfigItem, FluentStyleSheet, HyperlinkButton, IconWidget, drawIcon, \
    setThemeColor, ImageLabel, MessageBoxBase, SmoothScrollDelegate, setFont, themeColor, setTheme, Theme, qrouter, \
    NavigationBar, NavigationBarPushButton, SplashScreen, Slider, OptionsSettingCard, InfoBar, TransparentToolButton, \
    BodyLabel, InfoBarPosition, CheckBox, PushButton, ExpandSettingCard, ToolTipFilter, ToolTipPosition, FluentFontIconBase
from qfluentwidgets.components.widgets.line_edit import EditLayer, LineEditButton, CompleterMenu
from qfluentwidgets.components.widgets.menu import MenuAnimationType, RoundMenu
from qfluentwidgets.components.widgets.spin_box import SpinButton, SpinIcon
from qfluentwidgets.window.fluent_window import FluentWindowBase
from qframelesswindow.titlebar import MinimizeButton, CloseButton, MaximizeButton
from qframelesswindow import TitleBarButton
from qframelesswindow.utils import startSystemMove


class Mutex:
    def __init__(self):
        self.file = None

    def __enter__(self):
        self.file = open('RandomSetting.lockfile', 'w')
        try:
            portalocker.lock(self.file, portalocker.LOCK_EX | portalocker.LOCK_NB)
        except portalocker.AlreadyLocked:
            try:
                window = GetWindow("Random 设置")[0]
                if window.isMinimized:
                    window.restore()
                window.activate()
            except:
                pass
            sys.exit()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            try:
                portalocker.unlock(self.file)
            finally:
                try:
                    self.file.close()
                except:
                    pass
                try:
                    os.remove('RandomSetting.lockfile')
                except:
                    pass


class FluentFontIcon(FluentFontIconBase):

    def path(self, theme=Theme.AUTO):
        return "Font/SegoeIcons.ttf"


class SmoothScrollArea(QScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.delegate = SmoothScrollDelegate(self, True)
        QScroller.grabGesture(self.viewport(), QScroller.TouchGesture)

    def setScrollAnimation(self, orient, duration, easing=QEasingCurve.OutCubic):
        """ set scroll animation

        Parameters
        ----------
        orient: Orient
            scroll orientation

        duration: int
            scroll duration

        easing: QEasingCurve
            animation type
        """
        bar = self.delegate.hScrollBar if orient == Qt.Horizontal else self.delegate.vScrollBar
        bar.setScrollAnimation(duration, easing)

    def enableTransparentBackground(self):
        self.setStyleSheet("QScrollArea{border: none; background: transparent}")

        if self.widget():
            self.widget().setStyleSheet("QWidget{background: transparent}")


class EditMenu(RoundMenu):
    """ Edit menu """

    # noinspection PyArgumentList
    def createActions(self):
        self.cutAct = QAction(
            FluentFontIcon("\ue8c6").icon(),
            self.tr("剪切"),
            self,
            shortcut="Ctrl+X",
            triggered=self.parent().cut,
        )
        self.copyAct = QAction(
            FluentFontIcon("\ue8c8").icon(),
            self.tr("复制"),
            self,
            shortcut="Ctrl+C",
            triggered=self.parent().copy,
        )
        self.pasteAct = QAction(
            FluentFontIcon("\ue77f").icon(),
            self.tr("粘贴"),
            self,
            shortcut="Ctrl+V",
            triggered=self.parent().paste,
        )
        self.cancelAct = QAction(
            FluentFontIcon("\ue7a7").icon(),
            self.tr("撤销"),
            self,
            shortcut="Ctrl+Z",
            triggered=self.parent().undo,
        )
        self.selectAllAct = QAction(
            self.tr("全选"),
            self,
            shortcut="Ctrl+A",
            triggered=self.parent().selectAll
        )
        self.action_list = [self.cutAct, self.copyAct, self.pasteAct, self.cancelAct, self.selectAllAct]

    def _parentText(self):
        raise NotImplementedError

    def _parentSelectedText(self):
        raise NotImplementedError

    def exec(self, pos, ani=True, aniType=MenuAnimationType.DROP_DOWN):
        self.clear()
        self.createActions()

        if QApplication.clipboard().mimeData().hasText():
            if self._parentText():
                if self._parentSelectedText():
                    if self.parent().isReadOnly():
                        self.addActions([self.copyAct, self.selectAllAct])
                    else:
                        self.addActions(self.action_list)
                else:
                    if self.parent().isReadOnly():
                        self.addAction(self.selectAllAct)
                    else:
                        self.addActions(self.action_list[2:])
            elif not self.parent().isReadOnly():
                self.addAction(self.pasteAct)
            else:
                return
        else:
            if not self._parentText():
                return

            if self._parentSelectedText():
                if self.parent().isReadOnly():
                    self.addActions([self.copyAct, self.selectAllAct])
                else:
                    self.addActions(
                        self.action_list[:2] + self.action_list[3:])
            else:
                if self.parent().isReadOnly():
                    self.addAction(self.selectAllAct)
                else:
                    self.addActions(self.action_list[3:])

        super().exec(pos, ani, aniType)


class LineEditMenu(EditMenu):
    """ Line edit menu """

    def __init__(self, parent: QLineEdit):
        super().__init__("", parent)
        self.selectionStart = parent.selectionStart()
        self.selectionLength = parent.selectionLength()

    def _onItemClicked(self, item):
        if self.selectionStart >= 0:
            self.parent().setSelection(self.selectionStart, self.selectionLength)

        super()._onItemClicked(item)

    def _parentText(self):
        return self.parent().text()

    def _parentSelectedText(self):
        return self.parent().selectedText()

    def exec(self, pos, ani=True, aniType=MenuAnimationType.DROP_DOWN):
        return super().exec(pos, ani, aniType)


class LineEdit(QLineEdit):
    """ Line edit """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._isClearButtonEnabled = False
        self._completer = None  # type: QCompleter
        self._completerMenu = None  # type: CompleterMenu
        self._isError = False

        self.leftButtons = []   # type: List[LineEditButton]
        self.rightButtons = []  # type: List[LineEditButton]

        self.setProperty("transparent", True)
        FluentStyleSheet.LINE_EDIT.apply(self)
        self.setFixedHeight(33)
        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        setFont(self)

        self.hBoxLayout = QHBoxLayout(self)
        self.clearButton = LineEditButton(FluentFontIcon("\ue711"), self)

        self.clearButton.setFixedSize(29, 25)
        self.clearButton.hide()

        self.hBoxLayout.setSpacing(3)
        self.hBoxLayout.setContentsMargins(4, 4, 4, 4)
        self.hBoxLayout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.hBoxLayout.addWidget(self.clearButton, 0, Qt.AlignRight)

        self.clearButton.clicked.connect(self.clear)
        self.textChanged.connect(self.__onTextChanged)
        self.textEdited.connect(self.__onTextEdited)

    def isError(self):
        return self._isError

    def setError(self, isError: bool):
        if isError == self.isError():
            return

        self._isError = isError
        self.update()

    def focusedBorderColor(self):
        if not self.isError():
            return themeColor()

        return QColor("#ff99a4") if isDarkTheme() else QColor("#c42b1c")

    def setClearButtonEnabled(self, enable: bool):
        self._isClearButtonEnabled = enable
        self._adjustTextMargins()

    def isClearButtonEnabled(self) -> bool:
        return self._isClearButtonEnabled

    def setCompleter(self, completer: QCompleter):
        self._completer = completer

    def completer(self):
        return self._completer

    def addAction(self, action: QAction, position=QLineEdit.ActionPosition.TrailingPosition):
        QWidget.addAction(self, action)

        button = LineEditButton(action.icon())
        button.setAction(action)
        button.setFixedWidth(29)

        if position == QLineEdit.ActionPosition.LeadingPosition:
            self.hBoxLayout.insertWidget(len(self.leftButtons), button, 0, Qt.AlignLeading)
            if not self.leftButtons:
                self.hBoxLayout.insertStretch(1, 1)

            self.leftButtons.append(button)
        else:
            self.rightButtons.append(button)
            self.hBoxLayout.addWidget(button, 0, Qt.AlignRight)

        self._adjustTextMargins()

    def addActions(self, actions, position=QLineEdit.ActionPosition.TrailingPosition):
        for action in actions:
            self.addAction(action, position)

    def _adjustTextMargins(self):
        left = len(self.leftButtons) * 30
        right = len(self.rightButtons) * 30 + 28 * self.isClearButtonEnabled()
        m = self.textMargins()
        self.setTextMargins(left, m.top(), right, m.bottom())

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self.clearButton.hide()

    def focusInEvent(self, e):
        super().focusInEvent(e)
        if self.isClearButtonEnabled():
            self.clearButton.setVisible(bool(self.text()))

    def __onTextChanged(self, text):
        """ text changed slot """
        if self.isClearButtonEnabled():
            self.clearButton.setVisible(bool(text) and self.hasFocus())

    def __onTextEdited(self, text):
        if not self.completer():
            return

        if self.text():
            QTimer.singleShot(50, self._showCompleterMenu)
        elif self._completerMenu:
            self._completerMenu.close()

    def setCompleterMenu(self, menu):
        """ set completer menu

        Parameters
        ----------
        menu: CompleterMenu
            completer menu
        """
        menu.activated.connect(self._completer.activated)
        menu.indexActivated.connect(lambda idx: self._completer.activated[QModelIndex].emit(idx))
        self._completerMenu = menu

    def _showCompleterMenu(self):
        if not self.completer() or not self.text():
            return

        # create menu
        if not self._completerMenu:
            self.setCompleterMenu(CompleterMenu(self))

        # add menu items
        self.completer().setCompletionPrefix(self.text())
        changed = self._completerMenu.setCompletion(self.completer().completionModel(), self.completer().completionColumn())
        self._completerMenu.setMaxVisibleItems(self.completer().maxVisibleItems())

        # show menu
        if changed:
            self._completerMenu.popup()

    def contextMenuEvent(self, e):
        menu = LineEditMenu(self)
        menu.exec_(e.globalPos())

    def paintEvent(self, e):
        super().paintEvent(e)
        if not self.hasFocus():
            return

        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        m = self.contentsMargins()
        path = QPainterPath()
        w, h = self.width()-m.left()-m.right(), self.height()
        path.addRoundedRect(QRectF(m.left(), h-10, w, 10), 5, 5)

        rectPath = QPainterPath()
        rectPath.addRect(m.left(), h-10, w, 8)
        path = path.subtracted(rectPath)

        painter.fillPath(path, self.focusedBorderColor())


class SpinBoxBase:
    """ Spin box ui """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.hBoxLayout = QHBoxLayout(self)

        self.setProperty('transparent', True)
        FluentStyleSheet.SPIN_BOX.apply(self)
        self.setButtonSymbols(QSpinBox.NoButtons)
        self.setFixedHeight(33)
        setFont(self)

        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._showContextMenu)

    def setReadOnly(self, isReadOnly: bool):
        super().setReadOnly(isReadOnly)
        self.setSymbolVisible(not isReadOnly)

    def setSymbolVisible(self, isVisible: bool):
        """ set whether the spin symbol is visible """
        self.setProperty("symbolVisible", isVisible)
        self.setStyle(QApplication.style())

    def _showContextMenu(self, pos):
        menu = LineEditMenu(self.lineEdit())
        menu.exec_(self.mapToGlobal(pos))

    def _drawBorderBottom(self):
        if not self.hasFocus():
            return

        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        path = QPainterPath()
        w, h = self.width(), self.height()
        path.addRoundedRect(QRectF(0, h-10, w, 10), 5, 5)

        rectPath = QPainterPath()
        rectPath.addRect(0, h-10, w, 8)
        path = path.subtracted(rectPath)

        painter.fillPath(path, themeColor())

    def paintEvent(self, e):
        super().paintEvent(e)
        self._drawBorderBottom()


class HotkeyEdit(LineEdit):
    hotkeyChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("输入快捷键")
        self.setClearButtonEnabled(True)

    def contextMenuEvent(self, event):
        pass

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if modifiers & Qt.MetaModifier or (event.text() and ord(event.text()) > 127):
            self.clear()
            return
        if key in (Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta):
            return

        sequence = QKeySequence(modifiers | key).toString()
        if sequence:
            self.setText(sequence)
            self.hotkeyChanged.emit(sequence)

    def mousePressEvent(self, event):
        self.clear()
        super().mousePressEvent(event)


class InlineSpinBoxBase(SpinBoxBase):
    """ Inline spin box base """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.upButton = SpinButton(SpinIcon.UP, self)
        self.downButton = SpinButton(SpinIcon.DOWN, self)

        self.hBoxLayout.setContentsMargins(0, 4, 4, 4)
        self.hBoxLayout.setSpacing(5)
        self.hBoxLayout.addWidget(self.upButton, 0, Qt.AlignRight)
        self.hBoxLayout.addWidget(self.downButton, 0, Qt.AlignRight)
        self.hBoxLayout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.upButton.clicked.connect(self.stepUp)
        self.downButton.clicked.connect(self.stepDown)

    def setSymbolVisible(self, isVisible: bool):
        super().setSymbolVisible(isVisible)
        self.upButton.setVisible(isVisible)
        self.downButton.setVisible(isVisible)

    def setAccelerated(self, on: bool):
        super().setAccelerated(on)
        self.upButton.setAutoRepeat(on)
        self.downButton.setAutoRepeat(on)


class SpinBox(InlineSpinBoxBase, QSpinBox):
    """ Spin box """


class TextEditMenu(EditMenu):
    def __init__(self, parent: QTextEdit):
        super().__init__("", parent)
        cursor = parent.textCursor()
        self.selectionStart = cursor.selectionStart()
        self.selectionLength = cursor.selectionEnd() - self.selectionStart + 1

    def _parentText(self):
        return self.parent().toPlainText()

    def _parentSelectedText(self):
        return self.parent().textCursor().selectedText()

    def _onItemClicked(self, item):
        if self.selectionStart >= 0:
            cursor = self.parent().textCursor()
            cursor.setPosition(self.selectionStart)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, self.selectionLength)

        super()._onItemClicked(item)

    def exec(self, pos, ani=True, aniType=MenuAnimationType.DROP_DOWN):
        return super().exec(pos, ani, aniType)


class TextBrowser(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layer = EditLayer(self)
        self.scrollDelegate = SmoothScrollDelegate(self)
        FluentStyleSheet.LINE_EDIT.apply(self)
        setFont(self)

    def contextMenuEvent(self, e):
        menu = TextEditMenu(self)
        menu.exec(e.globalPos())


class SettingIconWidget(IconWidget):

    def paintEvent(self, e):
        painter = QPainter(self)

        if not self.isEnabled():
            painter.setOpacity(0.36)

        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        drawIcon(self._icon, painter, self.rect())


class SettingCard(QFrame):
    def __init__(self, icon: Union[str, QIcon], title, content=None, parent=None):
        """
        Parameters
        ----------
        icon: str | QIcon | FluentIconBase
            the icon to be drawn

        title: str
            the title of card

        content: str
            the content of card

        parent: QWidget
            parent widget
        """
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

        # initialize layout
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


class SpinBoxItem(QWidget):
    def __init__(self, index: int, parent=None):
        super().__init__(parent=parent)
        self.hBoxLayout = QHBoxLayout(self)
        self.hintLabel = BodyLabel(["上边距", "下边距", "左边距", "右边距"][index], self)
        if darkdetect.isDark():
            self.hintLabel.setStyleSheet("font: 13px 'Segoe UI', 'Microsoft YaHei', 'PingFang SC'; padding: 0; border: none; background-color: transparent; color: white;")
        else:
            self.hintLabel.setStyleSheet("font: 13px 'Segoe UI', 'Microsoft YaHei', 'PingFang SC'; padding: 0; border: none; background-color: transparent; color: black;")

        self.spinBox = SpinBox(self)
        self.spinBox.setAccelerated(True)

        self.setFixedHeight(53)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.hBoxLayout.setContentsMargins(20, 0, 18, 0)
        self.hBoxLayout.addWidget(self.hintLabel, 0, Qt.AlignLeft)
        self.hBoxLayout.addSpacing(16)
        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.spinBox, 0, Qt.AlignRight)
        self.hBoxLayout.setAlignment(Qt.AlignVCenter)


class ShowFolderItem(QWidget):
    def __init__(self, folder: str, parent=None):
        super().__init__(parent=parent)

        self.titleLabel = BodyLabel("自动保存的位置", self)
        self.folderLabel = BodyLabel(self)
        self.folderLabel.setText(folder)
        self.applyStyleSheet()

        self.changeButton = HyperlinkButton(self)
        self.changeButton.setText("更改")
        self.openButton = HyperlinkButton(self)
        self.openButton.setText("打开")
        self.openButton.clicked.connect(self.openFolder)

        self.textLayout = QVBoxLayout()
        self.buttonLayout = QHBoxLayout()
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setSpacing(0)
        self.textLayout.setContentsMargins(20, 0, 20, 10)
        self.buttonLayout.setContentsMargins(20, 10, 20, 0)
        self.vBoxLayout.setContentsMargins(0, 18, 0, 16)
        self.textLayout.addWidget(self.titleLabel)
        self.textLayout.addWidget(self.folderLabel)
        self.textLayout.setAlignment(Qt.AlignVCenter)
        self.buttonLayout.addStretch(1)
        self.buttonLayout.addWidget(self.changeButton)
        self.buttonLayout.addSpacing(16)
        self.buttonLayout.addWidget(self.openButton)
        self.vBoxLayout.addLayout(self.textLayout)
        self.vBoxLayout.addLayout(self.buttonLayout)

    def setFolder(self, folder):
        self.folderLabel.setText(folder)
        self.applyStyleSheet()

    def openFolder(self):
        try:
            os.startfile(cfg.ScreenShotPath.value)
        except:
            pass

    def applyStyleSheet(self):
        if darkdetect.isDark():
            self.titleLabel.setStyleSheet("font: 14px 'Segoe UI', 'Microsoft YaHei', 'PingFang SC'; padding: 0; border: none; background-color: transparent; color: white;")
            self.folderLabel.setStyleSheet("font: 11px 'Segoe UI', 'Microsoft YaHei', 'PingFang SC'; padding: 0; border: none; background-color: transparent; color: rgb(208, 208, 208);")
        else:
            self.titleLabel.setStyleSheet("font: 14px 'Segoe UI', 'Microsoft YaHei', 'PingFang SC'; padding: 0; border: none; background-color: transparent; color: black;")
            self.folderLabel.setStyleSheet("font: 11px 'Segoe UI', 'Microsoft YaHei', 'PingFang SC'; padding: 0; border: none; background-color: transparent; color: rgb(96, 96, 96);")


class CustomPathSettingCard(ExpandSettingCard):

    def __init__(self, title: str, content: str = None, parent=None):
        """
        Parameters
        ----------
        title: str
            the title of card

        content: str
            the content of card

        parent: QWidget
            parent widget
        """
        super().__init__(FluentFontIcon("\ue722"), title, content, parent)
        self.__initWidget()

    def __initWidget(self):
        self.viewLayout.setSpacing(0)
        self.viewLayout.setAlignment(Qt.AlignTop)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)

        self.showFolderItem = ShowFolderItem(cfg.ScreenShotPath.value, self.view)
        self.showFolderItem.changeButton.clicked.connect(self.showFolderDialog)
        self.viewLayout.addWidget(self.showFolderItem)

        self.updateContent()
        self._adjustViewSize()

    def showFolderDialog(self):
        folder = QFileDialog.getExistingDirectory(self, self.tr("选择文件夹"), os.path.join(os.path.expanduser('~'), '.Random'))
        if not folder:
            return

        cfg.set(cfg.ScreenShotPath, folder)
        self.showFolderItem.setFolder(cfg.ScreenShotPath.value)

    def updateContent(self):
        self.showFolderItem.setFolder(cfg.ScreenShotPath.value)


class CustomScreenMarginSettingCard(ExpandSettingCard):

    def __init__(self, title: str, content: str = None, parent=None):
        """
        Parameters
        ----------
        title: str
            the title of card

        content: str
            the content of card

        parent: QWidget
            parent widget
        """
        super().__init__(FluentFontIcon("\ue9a6"), title, content, parent)
        self.__initWidget()

    def __initWidget(self):
        self.viewLayout.setSpacing(0)
        self.viewLayout.setAlignment(Qt.AlignTop)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)

        self.topMargin = SpinBoxItem(0, parent=self)
        self.bottomMargin = SpinBoxItem(1, parent=self)
        self.leftMargin = SpinBoxItem(2, parent=self)
        self.rightMargin = SpinBoxItem(3, parent=self)

        self.topMargin.spinBox.valueChanged.connect(lambda: self.setValue(0))
        self.bottomMargin.spinBox.valueChanged.connect(lambda: self.setValue(1))
        self.leftMargin.spinBox.valueChanged.connect(lambda: self.setValue(2))
        self.rightMargin.spinBox.valueChanged.connect(lambda: self.setValue(3))

        self.viewLayout.addWidget(self.topMargin)
        self.viewLayout.addWidget(self.bottomMargin)
        self.viewLayout.addWidget(self.leftMargin)
        self.viewLayout.addWidget(self.rightMargin)

        self._adjustViewSize()

    def setValue(self, index):
        if index == 0:
            cfg.set(cfg.TopMargin, self.topMargin.spinBox.value())
        elif index == 1:
            cfg.set(cfg.BottomMargin, self.bottomMargin.spinBox.value())
        elif index == 2:
            cfg.set(cfg.LeftMargin, self.leftMargin.spinBox.value())
        elif index == 3:
            cfg.set(cfg.RightMargin, self.rightMargin.spinBox.value())

    def updateValue(self):
        self.topMargin.spinBox.setValue(cfg.TopMargin.value)
        self.bottomMargin.spinBox.setValue(cfg.BottomMargin.value)
        self.leftMargin.spinBox.setValue(cfg.LeftMargin.value)
        self.rightMargin.spinBox.setValue(cfg.RightMargin.value)


class SwitchSettingCard(SettingCard):
    checkedChanged = pyqtSignal(bool)

    def __init__(self, icon: Union[str, QIcon], title, content=None,
                 configItem: ConfigItem = None, parent=None):
        """
        Parameters
        ----------
        icon: str | QIcon | FluentIconBase
            the icon to be drawn

        title: str
            the title of card

        content: str
            the content of card

        configItem: ConfigItem
            configuration item operated by the card

        parent: QWidget
            parent widget
        """
        super().__init__(icon, title, content, parent)
        self.configItem = configItem
        self.switchButton = SwitchButton(
            self.tr('关'), self, IndicatorPosition.RIGHT)

        if configItem:
            self.setValue(qconfig.get(configItem))
            configItem.valueChanged.connect(self.setValue)

        # add switch button to layout
        self.hBoxLayout.addWidget(self.switchButton, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.switchButton.checkedChanged.connect(self.__onCheckedChanged)

    def __onCheckedChanged(self, isChecked: bool):
        self.setValue(isChecked)
        self.checkedChanged.emit(isChecked)

    def setValue(self, isChecked: bool):
        if self.configItem:
            qconfig.set(self.configItem, isChecked)

        self.switchButton.setChecked(isChecked)
        self.switchButton.setText(
            self.tr('开') if isChecked else self.tr('关'))

    def setChecked(self, isChecked: bool):
        self.setValue(isChecked)

    def isChecked(self):
        return self.switchButton.isChecked()


class PushSettingCard(SettingCard):
    clicked = pyqtSignal()

    def __init__(self, text, icon: Union[str, QIcon], title, content=None, parent=None):
        """
        Parameters
        ----------
        text: str
            the text of push button

        icon: str | QIcon | FluentIconBase
            the icon to be drawn

        title: str
            the title of card

        content: str
            the content of card

        parent: QWidget
            parent widget
        """
        super().__init__(icon, title, content, parent)
        self.button = QPushButton(text, self)
        self.hBoxLayout.addWidget(self.button, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)
        self.button.clicked.connect(self.clicked)


class PrimaryPushSettingCard(PushSettingCard):
    def __init__(self, text, icon, title, content=None, parent=None):
        super().__init__(text, icon, title, content, parent)
        self.button.setObjectName('primaryButton')


class HotkeySettingCard(SettingCard):
    clicked = pyqtSignal()

    def __init__(self, icon: Union[str, QIcon], title, content=None,
                 hotKey=None, enableHotKey=None, parent=None):
        """
        Parameters
        ----------
        icon: str | QIcon | FluentIconBase
            the icon to be drawn

        title: str
            the title of card

        content: str
            the content of card

        hotKey: ConfigItem

        enableHotKey: ConfigItem

        parent: QWidget
            parent widget
        """
        super().__init__(icon, title, content, parent)
        self.hotKey = hotKey
        self.enableHotKey = enableHotKey
        self.button = TransparentToolButton(self)
        self.button.setIcon(FluentFontIcon("\ue70f"))
        self.button.setToolTip("设置快捷键")
        self.button.installEventFilter(ToolTipFilter(self.button, 0, ToolTipPosition.BOTTOM))
        self.hBoxLayout.addWidget(self.button, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)
        self.button.clicked.connect(self.clicked)
        self.contentLabel.setText(self.hotKey.value if self.enableHotKey.value else self.tr("未启用"))

        if hotKey and enableHotKey:
            self.setValue(qconfig.get(hotKey), qconfig.get(enableHotKey))
            hotKey.valueChanged.connect(lambda: self.setValue(self.hotKey.value, self.enableHotKey.value))
            enableHotKey.valueChanged.connect(lambda: self.setValue(self.hotKey.value, self.enableHotKey.value))
        else:
            self.contentLabel.setText(self.tr("未启用"))

    def setValue(self, hotKey=None, enableHotKey=None):
        if hotKey is not None and self.hotKey:
            qconfig.set(self.hotKey, hotKey)
        if enableHotKey is not None and self.enableHotKey:
            qconfig.set(self.enableHotKey, enableHotKey)

        if self.hotKey and self.enableHotKey:
            text = hotKey if enableHotKey else self.tr("未启用")
            self.contentLabel.setText(text)


class SpinBoxSettingCard(SettingCard):
    valueChanged = pyqtSignal(int)

    def __init__(self, configItem: ConfigItem, icon: Union[str, QIcon], title, content=None, parent=None):
        """
        Parameters
        ----------
        configItem: ConfigItem
            configuration item operated by the card

        icon: str | QIcon | FluentIconBase
            the icon to be drawn

        title: str
            the title of card

        content: str
            the content of card

        parent: QWidget
            parent widget
        """
        super().__init__(icon, title, content, parent)
        self.configItem = configItem
        self.spinBox = SpinBox(self)
        self.spinBox.setFixedWidth(130)
        self.spinBox.setAccelerated(True)
        self.spinBox.setMaximum(999)
        self.spinBox.setMinimum(2)
        self.spinBox.setValue(configItem.value)

        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.spinBox, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        configItem.valueChanged.connect(self.setValue)
        self.spinBox.valueChanged.connect(self.__onValueChanged)

    def __onValueChanged(self, value: int):
        self.setValue(value)
        self.valueChanged.emit(value)

    def setValue(self, value):
        qconfig.set(self.configItem, value)
        self.spinBox.setValue(value)


class RangeSettingCard(SettingCard):
    """ Setting card with a slider """

    valueChanged = pyqtSignal(int)

    def __init__(self, configItem, icon: Union[str, QIcon], title, content=None, parent=None):
        """
        Parameters
        ----------
        configItem: RangeConfigItem
            configuration item operated by the card

        icon: str | QIcon | FluentIconBase
            the icon to be drawn

        title: str
            the title of card

        content: str
            the content of card

        parent: QWidget
            parent widget
        """
        super().__init__(icon, title, content, parent)
        self.configItem = configItem
        self.slider = Slider(Qt.Horizontal, self)
        self.valueLabel = QLabel(self)
        self.slider.setMinimumWidth(150)

        self.slider.setSingleStep(1)
        self.slider.setRange(*configItem.range)
        self.slider.setValue(configItem.value)
        self.valueLabel.setNum(configItem.value)

        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.valueLabel, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(6)
        self.hBoxLayout.addWidget(self.slider, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.valueLabel.setObjectName('valueLabel')
        configItem.valueChanged.connect(self.setValue)
        self.slider.valueChanged.connect(self.__onValueChanged)

    def __onValueChanged(self, value: int):
        """ slider value changed slot """
        self.setValue(value)
        self.valueChanged.emit(value)

    def setValue(self, value):
        qconfig.set(self.configItem, value)
        self.valueLabel.setNum(value)
        self.valueLabel.adjustSize()
        self.slider.setValue(value)


class ComboBoxSettingCard(SettingCard):
    def __init__(self, configItem: OptionsConfigItem, icon: Union[str, QIcon], title, content=None, texts=None, parent=None):
        """
        Parameters
        ----------
        configItem: OptionsConfigItem
            configuration item operated by the card

        icon: str | QIcon | FluentIconBase
            the icon to be drawn

        title: str
            the title of card

        content: str
            the content of card

        texts: List[str]
            the text of items

        parent: QWidget
            parent widget
        """
        super().__init__(icon, title, content, parent)
        self.configItem = configItem
        self.comboBox = ComboBox(self)
        self.hBoxLayout.addWidget(self.comboBox, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.optionToText = {o: t for o, t in zip(configItem.options, texts)}
        for text, option in zip(texts, configItem.options):
            self.comboBox.addItem(text, userData=option)

        self.comboBox.setCurrentText(self.optionToText[qconfig.get(configItem)])
        self.comboBox.currentIndexChanged.connect(self._onCurrentIndexChanged)
        configItem.valueChanged.connect(self.setValue)

    def _onCurrentIndexChanged(self, index: int):
        qconfig.set(self.configItem, self.comboBox.itemData(index))

    def setValue(self, value):
        if value not in self.optionToText:
            return

        self.comboBox.setCurrentText(self.optionToText[value])
        qconfig.set(self.configItem, value)


class RestartSignals(QObject):
    restartFinished = pyqtSignal(bool)


class RestartTask(QRunnable):
    def __init__(self, parent=None):
        super().__init__()
        self.signals = RestartSignals()
        self.parent = parent
        self.signals.moveToThread(QApplication.instance().thread())
        self.setAutoDelete(True)

    def killProcess(self, process_name):
        for proc in process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == process_name.lower():
                    pid = proc.info['pid']
                    p = Process(pid)
                    p.kill()
            except:
                pass

    def run(self):
        self.killProcess("RandomMain.exe")
        subprocess.Popen(["RandomMain.exe", "--force-start"], shell=True)
        self.signals.restartFinished.emit(True)


class WorkSpaceInterface(SmoothScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.scrollWidget = QWidget()
        self.stateTooltip = None
        self.expandLayout = ExpandLayout(self.scrollWidget)
        self.enableTransparentBackground()
        self.settingLabel = QLabel("工作区", self)
        self.applyBtn = PrimaryPushButton("应用", self)
        self.applyBtn.setFixedWidth(80)
        self.applyBtn.clicked.connect(self.onApplyBtn)
        if darkdetect.isDark():
            self.scrollWidget.setStyleSheet("background-color: rgba(39, 39, 39, 0);")
            self.settingLabel.setStyleSheet("font: 33px 'Microsoft YaHei Light'; background-color: transparent; color: white;")
        else:
            self.scrollWidget.setStyleSheet("background-color: rgba(249, 249, 249, 0);")
            self.settingLabel.setStyleSheet("font: 33px 'Microsoft YaHei Light'; background-color: transparent;")

        self.elementGroup = SettingCardGroup('', self.scrollWidget)

        self.valueCard = SpinBoxSettingCard(
            cfg.Value,
            FluentFontIcon("\ue716"),
            self.tr('人数'),
            self.tr('更改随机总数'),
            parent=self.elementGroup)
        self.noRepeatCard = SwitchSettingCard(
            FluentFontIcon("\uf5e7"),
            self.tr("去重"),
            self.tr("随机数不重复"),
            configItem=cfg.NoRepeat,
            parent=self.elementGroup)

        self.__initWidget()

    def __initWidget(self):
        self.resize(500, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 60, 0, 5)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

        self.__initLayout()

    def __initLayout(self):
        self.settingLabel.move(30, 10)
        self.applyBtn.move(285, 15)

        self.elementGroup.addSettingCard(self.valueCard)
        self.elementGroup.addSettingCard(self.noRepeatCard)

        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(25, 20, 25, 20)
        self.expandLayout.addWidget(self.elementGroup)

    def onApplyBtn(self):
        w = MessageBox(
            '重启 Random',
            '重启 Random 以应用更改',
            self.window())
        w.yesButton.setText('立即重启')
        w.cancelButton.setText('暂不重启')
        if w.exec():
            task = RestartTask()
            task.signals.restartFinished.connect(self.restartThreadFinished)
            self.threadPool.start(task)


class SettingInterface(SmoothScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.scrollWidget = QWidget()
        self.stateTooltip = None
        self.expandLayout = ExpandLayout(self.scrollWidget)
        self.enableTransparentBackground()
        self.settingLabel = QLabel("设置", self)
        self.applyBtn = PrimaryPushButton("应用", self)
        self.applyBtn.setFixedWidth(80)
        self.applyBtn.clicked.connect(self.onApplyBtn)
        if darkdetect.isDark():
            self.scrollWidget.setStyleSheet("background-color: rgba(39, 39, 39, 0);")
            self.settingLabel.setStyleSheet("font: 33px 'Microsoft YaHei Light'; background-color: transparent; color: white;")
        else:
            self.scrollWidget.setStyleSheet("background-color: rgba(249, 249, 249, 0);")
            self.settingLabel.setStyleSheet("font: 33px 'Microsoft YaHei Light'; background-color: transparent;")

        self.appearanceGroup = SettingCardGroup(self.tr('外观'), self.scrollWidget)
        self.actGroup = SettingCardGroup(self.tr('行为'), self.scrollWidget)
        self.toolGroup = SettingCardGroup(self.tr('工具'), self.scrollWidget)
        self.hotkeyGroup = SettingCardGroup(self.tr('快捷键'), self.scrollWidget)
        self.advanceGroup = SettingCardGroup(self.tr('高级'), self.scrollWidget)

        self.themeCard = ComboBoxSettingCard(
            cfg.Theme,
            FluentFontIcon("\ue793"),
            self.tr('主题'),
            self.tr('更改按钮的颜色主题'),
            texts=[self.tr("浅色"), self.tr("深色"), self.tr("使用系统设置")],
            parent=self.appearanceGroup)
        self.opacityCard = RangeSettingCard(
            cfg.Opacity,
            FluentFontIcon("\uf1ba"),
            self.tr('不透明度'),
            self.tr('更改按钮的不透明度'),
            parent=self.appearanceGroup)
        self.zoomCard = OptionsSettingCard(
            cfg.dpiScale,
            FluentFontIcon("\ue93a"),
            self.tr("缩放"),
            self.tr("调整界面尺寸"),
            texts=["100%", "125%", "150%", "175%", "200%", self.tr("使用系统设置")],
            parent=self.appearanceGroup)

        self.autoRunCard = SwitchSettingCard(
            FluentFontIcon("\ue7e8"),
            self.tr("开机时启动"),
            self.tr(""),
            configItem=cfg.AutoRun,
            parent=self.actGroup)
        self.showTimeCard = SwitchSettingCard(
            FluentFontIcon("\ue917"),
            self.tr("闲时显示时间"),
            self.tr(""),
            configItem=cfg.ShowTime,
            parent=self.actGroup)
        self.positionCard = OptionsSettingCard(
            cfg.Position,
            FluentFontIcon("\ue7c2"),
            self.tr("位置"),
            self.tr("按钮启动时的出现位置"),
            texts=["左上", "上中", "右上", "左下", "下中", "右下"],
            parent=self.actGroup)
        self.marginCard = CustomScreenMarginSettingCard(
            title="屏幕边距",
            content="展开选项卡以设置",
            parent=self.actGroup)

        self.autoHideCard = SwitchSettingCard(
            FluentFontIcon("\ued1a"),
            "自动隐藏",
            "捕获屏幕时自动隐藏按钮",
            configItem=cfg.IsAutoHide,
            parent=self.toolGroup)
        self.screenShotPathCard = CustomPathSettingCard(
            title="屏幕快照",
            content="展开选项卡以设置",
            parent=self.toolGroup)

        self.runHotKeyCard = HotkeySettingCard(
            FluentFontIcon("\ue724"),
            self.tr('生成随机数'),
            cfg.RunHotKey.value if cfg.EnableRunHotKey.value else self.tr("未启用"),
            hotKey=cfg.RunHotKey,
            enableHotKey=cfg.EnableRunHotKey,
            parent=self.hotkeyGroup)
        self.showHotKeyCard = HotkeySettingCard(
            FluentFontIcon("\uecc8"),
            self.tr('显示'),
            cfg.ShowHotKey.value if cfg.EnableShowHotKey.value else self.tr("未启用"),
            hotKey=cfg.ShowHotKey,
            enableHotKey=cfg.EnableShowHotKey,
            parent=self.hotkeyGroup)
        self.hideHotKeyCard = HotkeySettingCard(
            FluentFontIcon("\uecc9"),
            self.tr('隐藏'),
            cfg.HideHotKey.value if cfg.EnableHideHotKey.value else self.tr("未启用"),
            hotKey=cfg.HideHotKey,
            enableHotKey=cfg.EnableHideHotKey,
            parent=self.hotkeyGroup)
        self.screenShotHotKeyCard = HotkeySettingCard(
            FluentFontIcon("\ue722"),
            self.tr("屏幕快照"),
            cfg.ScreenShotHotKey.value if cfg.EnableScreenShotHotKey.value else self.tr("未启用"),
            hotKey=cfg.ScreenShotHotKey,
            enableHotKey=cfg.EnableScreenShotHotKey,
            parent=self.hotkeyGroup)

        self.recoverCard = PushSettingCard(
            self.tr('恢复'),
            FluentFontIcon("\uebc4"),
            self.tr('恢复默认设置'),
            self.tr('重置所有参数为初始值'),
            self.advanceGroup)
        self.devCard = PushSettingCard(
            self.tr('打开'),
            FluentFontIcon("\uec7a"),
            self.tr('开发者选项'),
            self.tr('打开配置文件'),
            self.advanceGroup)
        self.helpCard = PrimaryPushSettingCard(
            self.tr('转到帮助'),
            FluentFontIcon("\uea6b"),
            self.tr('帮助'),
            self.tr('提示与常见问题'),
            self.advanceGroup)

        self.__initWidget()

    def __initWidget(self):
        self.resize(500, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 60, 0, 5)
        self.setWidget(self.scrollWidget)
        self.threadPool = QThreadPool.globalInstance()
        self.threadPool.setMaxThreadCount(1)
        self.setWidgetResizable(True)

        self.__initLayout()
        self.__connectSignalToSlot()

    def __initLayout(self):
        self.settingLabel.move(30, 10)
        self.applyBtn.move(285, 15)

        self.appearanceGroup.addSettingCard(self.themeCard)
        self.appearanceGroup.addSettingCard(self.opacityCard)
        self.appearanceGroup.addSettingCard(self.zoomCard)
        self.actGroup.addSettingCard(self.autoRunCard)
        self.actGroup.addSettingCard(self.showTimeCard)
        self.actGroup.addSettingCard(self.positionCard)
        self.actGroup.addSettingCard(self.marginCard)
        self.toolGroup.addSettingCard(self.autoHideCard)
        self.toolGroup.addSettingCard(self.screenShotPathCard)
        self.hotkeyGroup.addSettingCard(self.runHotKeyCard)
        self.hotkeyGroup.addSettingCard(self.showHotKeyCard)
        self.hotkeyGroup.addSettingCard(self.hideHotKeyCard)
        self.hotkeyGroup.addSettingCard(self.screenShotHotKeyCard)
        self.advanceGroup.addSettingCard(self.recoverCard)
        self.advanceGroup.addSettingCard(self.devCard)
        self.advanceGroup.addSettingCard(self.helpCard)

        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(25, 20, 25, 20)
        self.expandLayout.addWidget(self.appearanceGroup)
        self.expandLayout.addWidget(self.actGroup)
        self.expandLayout.addWidget(self.toolGroup)
        self.expandLayout.addWidget(self.hotkeyGroup)
        self.expandLayout.addWidget(self.advanceGroup)

    def recoverConfig(self):
        w = MessageBox(
            '恢复默认设置',
            '点击确定以重置所有设置为默认值。',
            self.window())
        w.yesButton.setText('确定')
        w.cancelButton.setText('取消')
        if w.exec():
            self.valueCard.setValue(40)
            self.noRepeatCard.setValue(True)
            self.themeCard.setValue("Auto")
            self.opacityCard.setValue(75)
            self.zoomCard.setValue("Auto")
            self.autoRunCard.setValue(True)
            self.showTimeCard.setValue(True)
            self.positionCard.setValue("TopLeft")
            self.runHotKeyCard.setValue("Ctrl+F1", True)
            self.showHotKeyCard.setValue("Ctrl+F2", True)
            self.hideHotKeyCard.setValue("Ctrl+F3", True)
            self.screenShotHotKeyCard.setValue("Ctrl+F5", True)

            cfg.set(cfg.TopMargin, 50)
            cfg.set(cfg.BottomMargin, 50)
            cfg.set(cfg.LeftMargin, 10)
            cfg.set(cfg.RightMargin, 10)
            self.marginCard.updateValue()
            cfg.set(cfg.EnableCustomStyleSheet, False)

            self.positionCard.adjustSize()

    def restartThreadFinished(self):
        InfoBar.success(
            '',
            self.tr('Random 已重启'),
            position=InfoBarPosition.TOP,
            duration=2000,
            isClosable=False,
            parent=self.window()
        )

    def openConfig(self):
        w = MessageBox(
            '打开配置文件',
            '随意修改配置文件可能导致程序异常。点击确定以继续。',
            self.window())
        w.yesButton.setText('确定')
        w.cancelButton.setText('取消')
        if w.exec():
            os.startfile(os.path.join(os.path.expanduser('~'), '.Random', 'config', 'config.json'))

    def onHotkeyCardClicked(self, index):
        w = HotkeyMessageBox(index=index, parent=self.window())
        if w.exec():
            if index == 1:
                self.runHotKeyCard.setValue(w.hotkeyEdit.text(), w.enableCheckBox.isChecked())
            elif index == 2:
                self.showHotKeyCard.setValue(w.hotkeyEdit.text(), w.enableCheckBox.isChecked())
            elif index == 3:
                self.hideHotKeyCard.setValue(w.hotkeyEdit.text(), w.enableCheckBox.isChecked())
            elif index == 4:
                self.screenShotHotKeyCard.setValue(w.hotkeyEdit.text(), w.enableCheckBox.isChecked())

    def onApplyBtn(self):
        w = MessageBox(
            '重启 Random',
            '重启 Random 以应用更改',
            self.window())
        w.yesButton.setText('立即重启')
        w.cancelButton.setText('暂不重启')
        if w.exec():
            task = RestartTask()
            task.signals.restartFinished.connect(self.restartThreadFinished)
            self.threadPool.start(task)

    def __showRestartTooltip(self):
        """ show restart tooltip """
        InfoBar.warning(
            '',
            self.tr('软件重启后生效'),
            position=InfoBarPosition.TOP,
            duration=2000,
            isClosable=False,
            parent=self.window()
        )

    def __connectSignalToSlot(self):
        cfg.appRestartSig.connect(self.__showRestartTooltip)
        self.recoverCard.clicked.connect(self.recoverConfig)
        self.devCard.clicked.connect(self.openConfig)
        self.helpCard.clicked.connect(lambda: os.startfile(os.path.abspath("./Doc/RandomHelp.html")))

        self.runHotKeyCard.clicked.connect(lambda: self.onHotkeyCardClicked(1))
        self.showHotKeyCard.clicked.connect(lambda: self.onHotkeyCardClicked(2))
        self.hideHotKeyCard.clicked.connect(lambda: self.onHotkeyCardClicked(3))
        self.screenShotHotKeyCard.clicked.connect(lambda: self.onHotkeyCardClicked(4))


class StyleSheetInterface(SmoothScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.scrollWidget = QWidget()
        self.stateTooltip = None
        self.expandLayout = ExpandLayout(self.scrollWidget)
        self.enableTransparentBackground()
        self.settingLabel = QLabel("样式表", self)
        self.applyBtn = PrimaryPushButton("应用", self)
        self.applyBtn.setFixedWidth(80)
        self.applyBtn.clicked.connect(self.onApplyBtn)
        if darkdetect.isDark():
            self.scrollWidget.setStyleSheet("background-color: rgba(39, 39, 39, 0);")
            self.settingLabel.setStyleSheet("font: 33px 'Microsoft YaHei Light'; background-color: transparent; color: white;")
        else:
            self.scrollWidget.setStyleSheet("background-color: rgba(249, 249, 249, 0);")
            self.settingLabel.setStyleSheet("font: 33px 'Microsoft YaHei Light'; background-color: transparent;")

        self.styleSheetGroup = SettingCardGroup('', self.scrollWidget)

        self.enableStyleSheetCard = SwitchSettingCard(
            FluentFontIcon("\ue943"),
            self.tr("自定义样式表"),
            self.tr("启用或关闭自定义样式表"),
            configItem=cfg.EnableCustomStyleSheet,
            parent=self.styleSheetGroup)
        self.selectQssCard = PushSettingCard(
            self.tr('选择文件'),
            FluentFontIcon("\ue8a5"),
            self.tr("样式表文件"),
            os.path.basename(cfg.QssPath.value),
            self.styleSheetGroup)
        self.newQssCard = PushSettingCard(
            self.tr('新建'),
            FluentFontIcon("\uecc8"),
            self.tr("新建样式表"),
            self.tr("创建新的样式表"),
            self.styleSheetGroup)
        self.editQssCard = PushSettingCard(
            self.tr('编辑'),
            FluentFontIcon("\ue70f"),
            self.tr("编辑样式表"),
            self.tr("编辑选择的的样式表"),
            self.styleSheetGroup)
        self.qssFolderCard = PushSettingCard(
            self.tr('打开'),
            FluentFontIcon("\ue8b7"),
            self.tr("样式表文件夹"),
            self.tr("打开默认的样式表文件夹"),
            self.styleSheetGroup)

        self.__initWidget()

    def __initWidget(self):
        self.resize(500, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 60, 0, 5)
        self.setWidget(self.scrollWidget)
        self.infoBar = InformationBar(title="", content="自定义样式表需要了解QSS", parent=self)
        self.threadPool = QThreadPool.globalInstance()
        self.threadPool.setMaxThreadCount(1)
        self.setWidgetResizable(True)

        self.__initLayout()
        self.__connectSignalToSlot()

    def __initLayout(self):
        self.settingLabel.move(30, 10)
        self.applyBtn.move(285, 15)

        self.styleSheetGroup.addSettingCard(self.infoBar)
        self.styleSheetGroup.addSettingCard(self.enableStyleSheetCard)
        self.styleSheetGroup.addSettingCard(self.selectQssCard)
        self.styleSheetGroup.addSettingCard(self.newQssCard)
        self.styleSheetGroup.addSettingCard(self.editQssCard)
        self.styleSheetGroup.addSettingCard(self.qssFolderCard)

        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(25, 20, 25, 20)
        self.expandLayout.addWidget(self.styleSheetGroup)

    def __onSelectQssCardClicked(self):
        file = QFileDialog.getOpenFileName(self, self.tr("选择文件"), os.path.join(os.path.expanduser('~'), '.Random', 'qss'), self.tr("样式表文件 (*.qss)"))[0]
        if not file or cfg.get(cfg.QssPath) == file:
            return

        self.selectQssCard.setContent(os.path.basename(file))
        cfg.set(cfg.QssPath, file)

    def __onNewQssCardClicked(self):
        w = NewQssMessageBox(parent=self.window())
        if w.exec():
            try:
                filepath = os.path.join(os.path.expanduser('~'), '.Random', 'qss', f'{w.nameEdit.text()}.qss')
                content = ''
                if w.templateCheckBox.isChecked():
                    content = 'QPushButton {\n    background-color: rgb(249, 249, 249);\n    color: rgb(0, 0, 0);\n    border-radius: 16px;\n    border: 0.5px groove gray;\n    border-style: outset;\n    font-family: "Microsoft YaHei";\n    font-size: 15pt;\n}\nQPushButton:hover {\n    background-color: rgba(249, 249, 249, 255);\n}\nQPushButton:pressed {\n    background-color: rgba(249, 249, 249, 255);\n}\n'
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                InfoBar.success(
                    '',
                    self.tr('新建文件成功'),
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    isClosable=False,
                    parent=self.window()
                )
                os.startfile(os.path.join(os.path.expanduser('~'), '.Random', 'qss', f'{w.nameEdit.text()}.qss'))
            except:
                InfoBar.error(
                    '',
                    self.tr('新建文件失败'),
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    isClosable=False,
                    parent=self.window()
                )


    def __onQssFolderCardClicked(self):
        os.startfile(os.path.join(os.path.expanduser('~'), '.Random', 'qss'))

    def restartThreadFinished(self):
        InfoBar.success(
            '',
            self.tr('Random 已重启'),
            position=InfoBarPosition.TOP,
            duration=2000,
            isClosable=False,
            parent=self.window()
        )

    def onApplyBtn(self):
        w = MessageBox(
            '重启 Random',
            '重启 Random 以应用更改',
            self.window())
        w.yesButton.setText('立即重启')
        w.cancelButton.setText('暂不重启')
        if w.exec():
            task = RestartTask()
            task.signals.restartFinished.connect(self.restartThreadFinished)
            self.threadPool.start(task)

    def __showRestartTooltip(self):
        """ show restart tooltip """
        InfoBar.warning(
            '',
            self.tr('软件重启后生效'),
            position=InfoBarPosition.TOP,
            duration=2000,
            isClosable=False,
            parent=self.window()
        )

    def __connectSignalToSlot(self):
        cfg.appRestartSig.connect(self.__showRestartTooltip)
        self.selectQssCard.clicked.connect(self.__onSelectQssCardClicked)
        self.newQssCard.clicked.connect(self.__onNewQssCardClicked)
        self.editQssCard.clicked.connect(lambda: os.startfile(cfg.QssPath.value))
        self.qssFolderCard.clicked.connect(self.__onQssFolderCardClicked)


class DetailMessageBox(MessageBoxBase):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel('关于 Random', self)
        self.textBox = TextBrowser(self)
        self.textBox.setText(
            f'Random v{VERSION}\nCopyright © {YEAR} BUG STUDIO\n\n' +
            'MIT License\nPermission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:\n' +
            'The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.\n' +
            'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.\n'
        )

        self.githubBtn = HyperlinkButton(self)
        self.websiteBtn = HyperlinkButton(self)
        self.onlineDocBtn = HyperlinkButton(self)
        self.githubBtn.setText('源代码')
        self.websiteBtn.setText('网站主页')
        self.onlineDocBtn.setText('在线文档')
        self.githubBtn.setIcon(FluentFontIcon("\ue71b"))
        self.websiteBtn.setIcon(FluentFontIcon("\ue774"))
        self.onlineDocBtn.setIcon(FluentFontIcon("\ue8a5"))
        self.githubBtn.setUrl("https://github.com/sudo0015/Random")
        self.websiteBtn.setUrl("https://sudo0015.github.io/")
        self.onlineDocBtn.setUrl("https://sudo0015.github.io/post/Random%20-bang-zhu.html")

        self.btnLayout = QHBoxLayout(self)
        self.btnLayout.addWidget(self.githubBtn)
        self.btnLayout.addWidget(self.websiteBtn)
        self.btnLayout.addWidget(self.onlineDocBtn)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.textBox)
        self.viewLayout.addLayout(self.btnLayout)

        self.yesButton.setText('确定')
        self.hideCancelButton()

        self.widget.setMinimumWidth(350)


class InfoIconWidget(QWidget):
    """ Icon widget """

    def __init__(self, icon: InfoBarIcon, parent=None):
        super().__init__(parent=parent)
        self.setFixedSize(36, 36)
        self.icon = icon

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

        rect = QRectF(10, 10, 15, 15)
        if self.icon:
            drawIcon(self.icon, painter, rect)


class WarningBar(QFrame):

    def __init__(self, title: str, content: str, parent=None):
        super().__init__(parent=parent)
        self.title = title
        self.content = content
        self.icon = InfoBarIcon.WARNING

        self.titleLabel = QLabel(self)
        self.contentLabel = QLabel(self)
        self.titleLabel.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.contentLabel.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.iconWidget = InfoIconWidget(self.icon)

        self.hBoxLayout = QHBoxLayout(self)
        self.textLayout = QHBoxLayout()
        self.widgetLayout = QHBoxLayout()

        self.lightBackgroundColor = QColor(255, 244, 206)
        self.darkBackgroundColor = QColor(67, 53, 25)

        self.__setQss()
        self.__initLayout()

    def __initLayout(self):
        self.hBoxLayout.setContentsMargins(6, 6, 6, 6)
        self.hBoxLayout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        self.textLayout.setSizeConstraint(QHBoxLayout.SetMinimumSize)
        self.textLayout.setAlignment(Qt.AlignTop)
        self.textLayout.setContentsMargins(1, 8, 0, 8)

        self.hBoxLayout.setSpacing(0)
        self.textLayout.setSpacing(5)
        self.hBoxLayout.addWidget(self.iconWidget, 0, Qt.AlignTop | Qt.AlignLeft)

        self.titleLabel.setVisible(bool(self.title))
        self.contentLabel.setVisible(bool(self.content))
        self.textLayout.addWidget(self.titleLabel, 1, Qt.AlignLeft | Qt.AlignTop)
        self.textLayout.addSpacing(7)
        self.textLayout.addWidget(self.contentLabel, 1, Qt.AlignLeft | Qt.AlignTop)

        self.hBoxLayout.addLayout(self.textLayout)
        self.hBoxLayout.addLayout(self.widgetLayout)
        self.widgetLayout.setSpacing(10)
        self.hBoxLayout.addSpacing(12)

        self._adjustText()

    def __setQss(self):
        self.titleLabel.setObjectName('titleLabel')
        self.contentLabel.setObjectName('contentLabel')
        if isinstance(self.icon, Enum):
            self.setProperty('type', self.icon.value)

        FluentStyleSheet.INFO_BAR.apply(self)

    def _adjustText(self):
        w = 900 if not self.parent() else (self.parent().width() - 50)
        chars = max(min(w / 10, 120), 30)
        self.titleLabel.setText(TextWrap.wrap(self.title, chars, False)[0])
        chars = max(min(w / 9, 120), 30)
        self.contentLabel.setText(TextWrap.wrap(self.content, chars, False)[0])
        self.adjustSize()

    def addWidget(self, widget: QWidget, stretch=0):
        """ add widget to info bar """
        self.widgetLayout.addSpacing(6)
        self.widgetLayout.addWidget(widget, stretch, Qt.AlignLeft | Qt.AlignTop)

    def eventFilter(self, obj, e: QEvent):
        if obj is self.parent():
            if e.type() in [QEvent.Resize, QEvent.WindowStateChange]:
                self._adjustText()

        return super().eventFilter(obj, e)

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.lightBackgroundColor is None:
            return

        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        if isDarkTheme():
            painter.setBrush(self.darkBackgroundColor)
        else:
            painter.setBrush(self.lightBackgroundColor)

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 6, 6)


class InformationBar(QFrame):

    def __init__(self, title: str, content: str, parent=None):
        super().__init__(parent=parent)
        self.title = title
        self.content = content
        self.icon = InfoBarIcon.INFORMATION

        self.titleLabel = QLabel(self)
        self.contentLabel = QLabel(self)
        self.titleLabel.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.contentLabel.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.iconWidget = InfoIconWidget(self.icon)
        self.helpBtn = PushButton("详情", self)
        self.helpBtn.clicked.connect(lambda: os.startfile(os.path.abspath("./Doc/RandomHelp.html")))

        self.hBoxLayout = QHBoxLayout(self)
        self.textLayout = QHBoxLayout()
        self.widgetLayout = QHBoxLayout()

        self.lightBackgroundColor = QColor(211, 231, 247)
        self.darkBackgroundColor = QColor(52, 66, 77)

        self.__setQss()
        self.__initLayout()

    def __initLayout(self):
        self.hBoxLayout.setContentsMargins(6, 6, 6, 6)
        self.hBoxLayout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        self.textLayout.setSizeConstraint(QHBoxLayout.SetMinimumSize)
        self.textLayout.setAlignment(Qt.AlignTop)
        self.textLayout.setContentsMargins(1, 8, 0, 8)

        self.hBoxLayout.setSpacing(0)
        self.textLayout.setSpacing(5)
        self.hBoxLayout.addWidget(self.iconWidget, 0, Qt.AlignTop | Qt.AlignLeft)

        self.titleLabel.setVisible(bool(self.title))
        self.contentLabel.setVisible(bool(self.content))
        self.textLayout.addWidget(self.titleLabel, 1, Qt.AlignLeft | Qt.AlignTop)
        self.textLayout.addSpacing(7)
        self.textLayout.addWidget(self.contentLabel, 1, Qt.AlignLeft | Qt.AlignTop)
        self.widgetLayout.addWidget(self.helpBtn)

        self.hBoxLayout.addLayout(self.textLayout)
        self.hBoxLayout.addLayout(self.widgetLayout)
        self.widgetLayout.setSpacing(10)
        self.hBoxLayout.addSpacing(12)

        self._adjustText()

    def __setQss(self):
        self.titleLabel.setObjectName('titleLabel')
        self.contentLabel.setObjectName('contentLabel')
        if isinstance(self.icon, Enum):
            self.setProperty('type', self.icon.value)

        FluentStyleSheet.INFO_BAR.apply(self)

    def _adjustText(self):
        w = 900 if not self.parent() else (self.parent().width() - 50)
        chars = max(min(w / 10, 120), 30)
        self.titleLabel.setText(TextWrap.wrap(self.title, chars, False)[0])
        chars = max(min(w / 9, 120), 30)
        self.contentLabel.setText(TextWrap.wrap(self.content, chars, False)[0])
        self.adjustSize()

    def addWidget(self, widget: QWidget, stretch=0):
        """ add widget to info bar """
        self.widgetLayout.addSpacing(6)
        self.widgetLayout.addWidget(widget, stretch, Qt.AlignLeft | Qt.AlignTop)

    def eventFilter(self, obj, e: QEvent):
        if obj is self.parent():
            if e.type() in [QEvent.Resize, QEvent.WindowStateChange]:
                self._adjustText()

        return super().eventFilter(obj, e)

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.lightBackgroundColor is None:
            return

        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        if isDarkTheme():
            painter.setBrush(self.darkBackgroundColor)
        else:
            painter.setBrush(self.lightBackgroundColor)

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 6, 6)


class CustomMessageBoxBase(MaskDialogBase):
    """ Message box base """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.buttonGroup = QFrame(self.widget)
        self.yesButton = PrimaryPushButton(self.tr('确定'), self.buttonGroup)
        self.cancelButton = QPushButton(self.tr('取消'), self.buttonGroup)

        self.vBoxLayout = QVBoxLayout(self.widget)
        self.viewLayout = QVBoxLayout()
        self.buttonLayout = QHBoxLayout(self.buttonGroup)

        self.__initWidget()

    def __initWidget(self):
        self.__setQss()
        self.__initLayout()

        self.setShadowEffect(60, (0, 10), QColor(0, 0, 0, 50))
        self.setMaskColor(QColor(0, 0, 0, 76))

        self.yesButton.setAttribute(Qt.WA_LayoutUsesWidgetRect)
        self.cancelButton.setAttribute(Qt.WA_LayoutUsesWidgetRect)

        self.yesButton.setAttribute(Qt.WA_MacShowFocusRect, False)

        self.yesButton.setFocus()
        self.buttonGroup.setFixedHeight(81)

        self.cancelButton.clicked.connect(self.__onCancelButtonClicked)

    def __initLayout(self):
        self._hBoxLayout.removeWidget(self.widget)
        self._hBoxLayout.addWidget(self.widget, 1, Qt.AlignCenter)

        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.addLayout(self.viewLayout, 1)
        self.vBoxLayout.addWidget(self.buttonGroup, 0, Qt.AlignBottom)

        self.viewLayout.setSpacing(12)
        self.viewLayout.setContentsMargins(24, 24, 24, 24)

        self.buttonLayout.setSpacing(12)
        self.buttonLayout.setContentsMargins(24, 24, 24, 24)
        self.buttonLayout.addWidget(self.yesButton, 1, Qt.AlignVCenter)
        self.buttonLayout.addWidget(self.cancelButton, 1, Qt.AlignVCenter)

    def __onCancelButtonClicked(self):
        self.reject()

    def __setQss(self):
        self.buttonGroup.setObjectName('buttonGroup')
        self.cancelButton.setObjectName('cancelButton')
        FluentStyleSheet.DIALOG.apply(self)
        self.buttonGroup.setStyleSheet("border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;")

    def hideYesButton(self):
        self.yesButton.hide()
        self.buttonLayout.insertStretch(0, 1)

    def hideCancelButton(self):
        self.cancelButton.hide()
        self.buttonLayout.insertStretch(0, 1)


class HotkeyMessageBox(CustomMessageBoxBase):

    def __init__(self, index=None, parent=None):
        super().__init__(parent)

        self.titleLabel = SubtitleLabel('设置快捷键', self)
        self.bodyLabel = BodyLabel('按下键盘按键以设置快捷键', self)
        self.hotkeyEdit = HotkeyEdit(self)
        self.hotkeyEdit.textChanged.connect(self.onTextChange)
        self.enableCheckBox = CheckBox(self)
        self.enableCheckBox.setText("启用快捷键")
        self.warningBar = WarningBar(title="", content="无效的快捷键", parent=self)
        self.warningBar.setFixedHeight(48)
        self.warningBar.setVisible(False)

        if index == 1:
            self.hotkeyEdit.setText(cfg.RunHotKey.value)
            self.enableCheckBox.setChecked(cfg.EnableRunHotKey.value)
        elif index == 2:
            self.hotkeyEdit.setText(cfg.ShowHotKey.value)
            self.enableCheckBox.setChecked(cfg.EnableShowHotKey.value)
        elif index == 3:
            self.hotkeyEdit.setText(cfg.HideHotKey.value)
            self.enableCheckBox.setChecked(cfg.EnableHideHotKey.value)
        elif index == 4:
            self.hotkeyEdit.setText(cfg.ScreenShotHotKey.value)
            self.enableCheckBox.setChecked(cfg.EnableScreenShotHotKey.value)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.bodyLabel)
        self.viewLayout.addWidget(self.hotkeyEdit)
        self.viewLayout.addWidget(self.warningBar)
        self.viewLayout.addWidget(self.enableCheckBox)

        self.yesButton.clicked.connect(self.onYesBtn)
        self.widget.setMinimumWidth(350)

    def onTextChange(self):
        if self.warningBar.isVisible():
            self.warningBar.setVisible(False)

    def validate(self, hotkey: str) -> bool:
        if not hotkey:
            return False
        else:
            keys = hotkey.split('+')
            modifiers = {'Ctrl', 'Alt', 'Shift'}
            isModifier = any(key in modifiers for key in keys)
            isRegular = any(key not in modifiers for key in keys)
            return isModifier and isRegular

    def onYesBtn(self):
        if not self.validate(self.hotkeyEdit.text()):
            self.hotkeyEdit.clear()
            self.warningBar.setVisible(True)
            return

        self.warningBar.setVisible(False)
        self.accept()


class NewQssMessageBox(CustomMessageBoxBase):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.titleLabel = SubtitleLabel('新建样式表', self)
        self.nameEdit = LineEdit(self)
        self.nameEdit.textChanged.connect(self.onTextChange)
        self.textLabel = BodyLabel('.qss', self)
        self.templateCheckBox = CheckBox(self)
        self.templateCheckBox.setText("从模板创建")
        self.errorBar = WarningBar(title="", content="无效的文件名", parent=self)
        self.errorBar.setFixedHeight(48)
        self.errorBar.setVisible(False)

        self.editLayout = QHBoxLayout(self)
        self.editLayout.setContentsMargins(0, 0, 0, 0)
        self.editLayout.addWidget(self.nameEdit)
        self.editLayout.addWidget(self.textLabel)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addLayout(self.editLayout)
        self.viewLayout.addWidget(self.errorBar)
        self.viewLayout.addWidget(self.templateCheckBox)

        self.yesButton.clicked.connect(self.onYesBtn)
        self.widget.setMinimumWidth(350)

    def onTextChange(self):
        if self.errorBar.isVisible():
            self.errorBar.setVisible(False)

    def validate(self, filename: str) -> bool:
        if not filename or filename.isspace():
            return False

        if os.path.basename(filename) != filename:
            return False

        invalid_chars = '<>:"/\\|?*' + ''.join(chr(i) for i in range(32))
        if any(char in invalid_chars for char in filename):
            return False

        reserved_names = r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$'
        if re.match(reserved_names, filename, re.IGNORECASE):
            return False

        if filename[-1] in (' ', '.'):
            return False

        if len(filename) > 255:
            return False

        return True

    def onYesBtn(self):
        if os.path.exists(os.path.join(os.path.expanduser('~'), '.Random', 'qss', f'{self.nameEdit.text()}.qss')):
            self.nameEdit.clear()
            self.errorBar.contentLabel.setText("文件已存在")
            self.errorBar.setVisible(True)
            return

        if not self.validate(self.nameEdit.text()):
            self.nameEdit.clear()
            self.errorBar.contentLabel.setText("无效的文件名")
            self.errorBar.setVisible(True)
            return

        self.errorBar.setVisible(False)
        self.accept()


class AboutInterface(SmoothScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.scrollWidget = QWidget()
        self.stateTooltip = None
        self.expandLayout = ExpandLayout(self.scrollWidget)
        self.enableTransparentBackground()
        if darkdetect.isDark():
            self.scrollWidget.setStyleSheet("background-color: rgba(39, 39, 39, 0);")
        else:
            self.scrollWidget.setStyleSheet("background-color: rgba(249, 249, 249, 0);")

        self.aboutGroup = SettingCardGroup(self.tr(''), self.scrollWidget)
        self.aboutESCard = PushSettingCard(
            self.tr('详细信息'),
            FluentFontIcon("\ue946"),
            self.tr('关于 Random'),
            self.tr(f'版本 {VERSION}'),
            self.aboutGroup)
        self.aboutBSCard = PushSettingCard(
            self.tr('了解更多'),
            FluentFontIcon("\ue716"),
            self.tr('关于作者'),
            self.tr('BUG STUDIO'),
            self.aboutGroup)
        self.helpCard = PrimaryPushSettingCard(
            self.tr('转到帮助'),
            FluentFontIcon("\uea6b"),
            self.tr('帮助'),
            self.tr('提示与常见问题'),
            self.aboutGroup)
        self.feedbackCard = PrimaryPushSettingCard(
            self.tr('提供反馈'),
            FluentFontIcon("\ued15"),
            self.tr('反馈'),
            self.tr('报告问题或提出建议'),
            self.aboutGroup)
        self.__initWidget()

    def __initWidget(self):
        self.resize(1000, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 0, 0, 0)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

        self.imgLabel = ImageLabel(self)
        if isDarkTheme():
            self.imgLabel.setImage(':/BannerDark.png')
        else:
            self.imgLabel.setImage(':/BannerLight.png')
        self.imgLabel.setFixedSize(350, 131)

        self.__initLayout()
        self.__connectSignalToSlot()

    def __initLayout(self):
        self.aboutGroup.addSettingCard(self.aboutESCard)
        self.aboutGroup.addSettingCard(self.aboutBSCard)
        self.aboutGroup.addSettingCard(self.helpCard)
        self.aboutGroup.addSettingCard(self.feedbackCard)

        self.expandLayout.setContentsMargins(25, 20, 25, 20)
        self.expandLayout.addWidget(self.imgLabel)
        self.expandLayout.addWidget(self.aboutGroup)

    def onAboutESCardClicked(self):
        w = DetailMessageBox(self.window())
        if w.exec():
            pass

    def __connectSignalToSlot(self):
        self.aboutESCard.clicked.connect(self.onAboutESCardClicked)
        self.aboutBSCard.clicked.connect(lambda: os.startfile(os.path.abspath("./Doc/AboutBugStudio.html")))
        self.helpCard.clicked.connect(lambda: os.startfile(os.path.abspath("./Doc/RandomHelp.html")))
        self.feedbackCard.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/sudo0015/Random/issues")))


class TitleBarBase(QWidget):
    """ Title bar base class """

    def __init__(self, parent):
        super().__init__(parent)
        self.minBtn = MinimizeButton(parent=self)
        self.closeBtn = CloseButton(parent=self)
        self.maxBtn = MaximizeButton(parent=self)

        self._isDoubleClickEnabled = True

        self.resize(200, 32)
        self.setFixedHeight(32)

        self.minBtn.clicked.connect(self.window().showMinimized)
        self.maxBtn.clicked.connect(self.__toggleMaxState)
        self.closeBtn.clicked.connect(self.quit)

        self.window().installEventFilter(self)

    def quit(self):
        self.hide()
        sys.exit()

    def eventFilter(self, obj, e):
        if obj is self.window():
            if e.type() == QEvent.WindowStateChange:
                self.maxBtn.setMaxState(self.window().isMaximized())
                return False

        return super().eventFilter(obj, e)

    def mouseDoubleClickEvent(self, event):
        """ Toggles the maximization state of the window """
        if event.button() != Qt.LeftButton or not self._isDoubleClickEnabled:
            return

        self.__toggleMaxState()

    def mouseMoveEvent(self, e):
        if sys.platform != "win32" or not self.canDrag(e.pos()):
            return

        startSystemMove(self.window(), e.globalPos())

    def mousePressEvent(self, e):
        if sys.platform == "win32" or not self.canDrag(e.pos()):
            return

        startSystemMove(self.window(), e.globalPos())

    def __toggleMaxState(self):
        """ Toggles the maximization state of the window and change icon """
        if self.window().isMaximized():
            self.window().showNormal()
        else:
            self.window().showMaximized()

        if sys.platform == "win32":
            from qframelesswindow.utils.win32_utils import releaseMouseLeftButton
            releaseMouseLeftButton(self.window().winId())

    def _isDragRegion(self, pos):
        """ Check whether the position belongs to the area where dragging is allowed """
        width = 0
        for button in self.findChildren(TitleBarButton):
            if button.isVisible():
                width += button.width()

        return 0 < pos.x() < self.width() - width

    def _hasButtonPressed(self):
        """ whether any button is pressed """
        return any(btn.isPressed() for btn in self.findChildren(TitleBarButton))

    def canDrag(self, pos):
        """ whether the position is draggable """
        return self._isDragRegion(pos) and not self._hasButtonPressed()

    def setDoubleClickEnabled(self, isEnabled):
        """ whether to switch window maximization status when double clicked

        Parameters
        ----------
        isEnabled: bool
            whether to enable double click
        """
        self._isDoubleClickEnabled = isEnabled


class TitleBarBase(QWidget):
    """ Title bar base class """

    def __init__(self, parent):
        super().__init__(parent)
        self.minBtn = MinimizeButton(parent=self)
        self.closeBtn = CloseButton(parent=self)
        self.maxBtn = MaximizeButton(parent=self)

        self._isDoubleClickEnabled = True

        self.resize(200, 32)
        self.setFixedHeight(32)

        self.minBtn.clicked.connect(self.window().showMinimized)
        self.maxBtn.clicked.connect(self.__toggleMaxState)
        self.closeBtn.clicked.connect(self.window().close)

        self.window().installEventFilter(self)

    def eventFilter(self, obj, e):
        if obj is self.window():
            if e.type() == QEvent.WindowStateChange:
                self.maxBtn.setMaxState(self.window().isMaximized())
                return False

        return super().eventFilter(obj, e)

    def mouseDoubleClickEvent(self, event):
        """ Toggles the maximization state of the window """
        if event.button() != Qt.LeftButton or not self._isDoubleClickEnabled:
            return

        self.__toggleMaxState()

    def mouseMoveEvent(self, e):
        if sys.platform != "win32" or not self.canDrag(e.pos()):
            return

        startSystemMove(self.window(), e.globalPos())

    def mousePressEvent(self, e):
        if sys.platform == "win32" or not self.canDrag(e.pos()):
            return

        startSystemMove(self.window(), e.globalPos())

    def __toggleMaxState(self):
        """ Toggles the maximization state of the window and change icon """
        if self.window().isMaximized():
            self.window().showNormal()
        else:
            self.window().showMaximized()

        if sys.platform == "win32":
            from qframelesswindow.utils.win32_utils import releaseMouseLeftButton
            releaseMouseLeftButton(self.window().winId())

    def _isDragRegion(self, pos):
        """ Check whether the position belongs to the area where dragging is allowed """
        width = 0
        for button in self.findChildren(TitleBarButton):
            if button.isVisible():
                width += button.width()

        return 0 < pos.x() < self.width() - width

    def _hasButtonPressed(self):
        """ whether any button is pressed """
        return any(btn.isPressed() for btn in self.findChildren(TitleBarButton))

    def canDrag(self, pos):
        """ whether the position is draggable """
        return self._isDragRegion(pos) and not self._hasButtonPressed()

    def setDoubleClickEnabled(self, isEnabled):
        """ whether to switch window maximization status when double clicked

        Parameters
        ----------
        isEnabled: bool
            whether to enable double click
        """
        self._isDoubleClickEnabled = isEnabled


class TitleBar(TitleBarBase):
    """ Title bar with minimize, maximum and close button """

    def __init__(self, parent):
        super().__init__(parent)
        self.hBoxLayout = QHBoxLayout(self)

        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.hBoxLayout.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.minBtn, 0, Qt.AlignRight)
        self.hBoxLayout.addWidget(self.maxBtn, 0, Qt.AlignRight)
        self.hBoxLayout.addWidget(self.closeBtn, 0, Qt.AlignRight)


class FluentTitleBar(TitleBar):
    """ Fluent title bar"""

    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.hBoxLayout.removeWidget(self.minBtn)
        self.hBoxLayout.removeWidget(self.maxBtn)
        self.hBoxLayout.removeWidget(self.closeBtn)

        # add window icon
        self.iconLabel = QLabel(self)
        self.iconLabel.setFixedSize(18, 18)
        self.hBoxLayout.insertWidget(0, self.iconLabel, 0, Qt.AlignLeft | Qt.AlignVCenter)
        self.window().windowIconChanged.connect(self.setIcon)

        # add title label
        self.titleLabel = QLabel(self)
        self.hBoxLayout.insertWidget(1, self.titleLabel, 0, Qt.AlignLeft | Qt.AlignVCenter)
        self.titleLabel.setObjectName('titleLabel')
        self.window().windowTitleChanged.connect(self.setTitle)

        self.vBoxLayout = QVBoxLayout()
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setSpacing(0)
        self.buttonLayout.setContentsMargins(0, 0, 0, 0)
        self.buttonLayout.setAlignment(Qt.AlignTop)
        self.buttonLayout.addWidget(self.minBtn)
        self.buttonLayout.addWidget(self.maxBtn)
        self.buttonLayout.addWidget(self.closeBtn)
        self.vBoxLayout.addLayout(self.buttonLayout)
        self.vBoxLayout.addStretch(1)
        self.hBoxLayout.addLayout(self.vBoxLayout, 0)

        FluentStyleSheet.FLUENT_WINDOW.apply(self)

    def setTitle(self, title):
        self.titleLabel.setText(title)
        self.titleLabel.adjustSize()

    def setIcon(self, icon):
        self.iconLabel.setPixmap(QIcon(icon).pixmap(18, 18))


class MSFluentTitleBar(FluentTitleBar):

    def __init__(self, parent):
        super().__init__(parent)
        self.hBoxLayout.insertSpacing(0, 20)
        self.hBoxLayout.insertSpacing(2, 2)


class MSFluentWindow(FluentWindowBase):
    """ Fluent window in Microsoft Store style """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitleBar(MSFluentTitleBar(self))

        self.navigationInterface = NavigationBar(self)

        self.hBoxLayout.setContentsMargins(0, 48, 0, 0)
        self.hBoxLayout.addWidget(self.navigationInterface)
        self.hBoxLayout.addWidget(self.stackedWidget, 1)

        self.titleBar.raise_()
        self.titleBar.setAttribute(Qt.WA_StyledBackground)

    def addSubInterface(self, interface: QWidget, icon: Union[QIcon, str], text: str,
                        selectedIcon=None, position=NavigationItemPosition.TOP, isTransparent=False) -> NavigationBarPushButton:
        """ add sub interface, the object name of `interface` should be set already
        before calling this method

        Parameters
        ----------
        interface: QWidget
            the subinterface to be added

        icon: FluentIconBase | QIcon | str
            the icon of navigation item

        text: str
            the text of navigation item

        selectedIcon: str | QIcon | FluentIconBase
            the icon of navigation item in selected state

        position: NavigationItemPosition
            the position of navigation item
        """
        if not interface.objectName():
            raise ValueError("The object name of `interface` can't be empty string.")

        interface.setProperty("isStackedTransparent", isTransparent)
        self.stackedWidget.addWidget(interface)

        routeKey = interface.objectName()
        item = self.navigationInterface.addItem(
            routeKey=routeKey,
            icon=icon,
            text=text,
            onClick=lambda: self.switchTo(interface),
            selectedIcon=selectedIcon,
            position=position
        )

        if self.stackedWidget.count() == 1:
            self.stackedWidget.currentChanged.connect(self._onCurrentInterfaceChanged)
            self.navigationInterface.setCurrentItem(routeKey)
            qrouter.setDefaultRouteKey(self.stackedWidget, routeKey)

        self._updateStackedBackground()

        return item


class Main(MSFluentWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        setThemeColor(QColor(9, 81, 41))
        self.setFixedSize(470, 630)
        self.setWindowTitle('Random 设置')
        self.setWindowIcon(QIcon(':/icon.png'))
        self.titleBar.raise_()
        self.titleBar.maxBtn.setVisible(False)
        self.desktop = QApplication.screens()[0].size()
        self.move(self.desktop.width() - self.width() - 5, self.desktop.height() - self.height() - 53)

        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.raise_()

        self.workspaceInterface = WorkSpaceInterface(self)
        self.settingInterface = SettingInterface(self)
        self.styleSheetInterface = StyleSheetInterface(self)
        self.aboutInterface = AboutInterface(self)
        self.workspaceInterface.setObjectName('workspaceInterface')
        self.settingInterface.setObjectName('settingInterface')
        self.styleSheetInterface.setObjectName('styleSheetInterface')
        self.aboutInterface.setObjectName('aboutInterface')
        self.addSubInterface(self.workspaceInterface, FluentFontIcon("\ue80f"), '工作区', FluentFontIcon("\uea8a"))
        self.addSubInterface(self.settingInterface, FluentFontIcon("\ue713"), '设置', FluentFontIcon("\uf8b0"))
        self.addSubInterface(self.styleSheetInterface, FluentFontIcon("\ue943"), "样式表", FluentFontIcon("\ue943"))
        self.navigationInterface.addItem(
            routeKey='Help',
            icon=FluentFontIcon("\uea6b"),
            text='帮助',
            onClick=self.onHelpBtn,
            selectable=False,
            position=NavigationItemPosition.BOTTOM,
        )
        self.addSubInterface(self.aboutInterface, FluentFontIcon("\ue946"), '关于', FluentFontIcon("\uf167"), NavigationItemPosition.BOTTOM)
        self.navigationInterface.setCurrentItem(self.workspaceInterface.objectName())

        self.splashScreen.finish()

    def onHelpBtn(self):
        os.startfile(os.path.abspath("./Doc/RandomHelp.html"))


if __name__ == '__main__':
    with Mutex():
        if cfg.get(cfg.dpiScale) == "Auto":
            QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
        else:
            os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
            os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))
        if darkdetect.isDark():
            setTheme(Theme.DARK)
        else:
            setTheme(Theme.LIGHT)
        app = QApplication(sys.argv)
        w = Main()
        w.show()
        app.exec()
