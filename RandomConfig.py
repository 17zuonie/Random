# -*- coding: utf-8 -*-

import os
from qfluentwidgets import qconfig, QConfig, ConfigItem, OptionsConfigItem, BoolValidator, RangeConfigItem, \
    RangeValidator, OptionsValidator, ConfigValidator


class Config(QConfig):
    Value = RangeConfigItem("MainWindow", "Value", 40, RangeValidator(2, 999))
    NoRepeat = ConfigItem("MainWindow", "NoRepeat", True, BoolValidator())
    Theme = OptionsConfigItem("MainWindow", "Theme", "Auto", OptionsValidator(["Light", "Dark", "Auto"]))
    EnableCustomStyleSheet = ConfigItem("MainWindow", "EnableCustomStyleSheet", False, BoolValidator())
    QssPath = ConfigItem("MainWindow", "QssPath", os.path.join(os.path.expanduser('~'), '.Random', 'qss', 'demo.qss'), ConfigValidator())

    Opacity = RangeConfigItem("MainWindow", "Opacity", 75, RangeValidator(1, 100))
    AutoRun = ConfigItem("MainWindow", "AutoRun", True, BoolValidator())
    ShowTime = ConfigItem("MainWindow", "ShowTime", True, BoolValidator())
    dpiScale = OptionsConfigItem("MainWindow", "DpiScale", "Auto", OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]), restart=True)
    Position = OptionsConfigItem("MainWindow", "Position", "TopLeft", OptionsValidator(["TopLeft", "TopCenter", "TopRight", "BottomLeft", "BottomCenter", "BottomRight"]))
    TopMargin = RangeConfigItem("MainWindow", "TopMargin", 50, RangeValidator(0, 1920))
    BottomMargin = RangeConfigItem("MainWindow", "BottomMargin", 50, RangeValidator(0, 1920))
    LeftMargin = RangeConfigItem("MainWindow", "LeftMargin", 10, RangeValidator(0, 1080))
    RightMargin = RangeConfigItem("MainWindow", "RightMargin", 10, RangeValidator(0, 1080))
    IsAutoHide = ConfigItem("MainWindow", "IsAutoHide", True, BoolValidator())
    ScreenShotPath = ConfigItem("MainWindow", "ScreenShotPath", os.path.join(os.path.expanduser('~'), '.Random', 'ScreenShot'), ConfigValidator())
    RunHotKey = ConfigItem("MainWindow", "RunHotKey", "Ctrl+F1", ConfigValidator())
    ShowHotKey = ConfigItem("MainWindow", "ShowHotKey", "Ctrl+F2", ConfigValidator())
    HideHotKey = ConfigItem("MainWindow", "HideHotKey", "Ctrl+F3", ConfigValidator())
    ScreenShotHotKey = ConfigItem("MainWindow", "ScreenShotHotKey", "Ctrl+F5", ConfigValidator())
    EnableRunHotKey = ConfigItem("MainWindow", "EnableRunHotKey", True, BoolValidator())
    EnableShowHotKey = ConfigItem("MainWindow", "EnableShowHotKey", True, BoolValidator())
    EnableHideHotKey = ConfigItem("MainWindow", "EnableHideHotKey", True, BoolValidator())
    EnableScreenShotHotKey = ConfigItem("MainWindow", "EnableScreenShotHotKey", True, BoolValidator())


YEAR = "2025"
VERSION = "5.3.3"
cfg = Config()
qconfig.load(os.path.join(os.path.expanduser('~'), '.Random', 'config', 'config.json'), cfg)
