"""
提示框对话框：单按钮用 tips_sigle.ui，双按钮（取消+确认）用 tips.ui。
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path

from PySide6.QtCore import Qt, QFile, QIODevice
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtUiTools import QUiLoader

from ui.core.dialog_overlay import OverlayDialog
from ui.core.resource_loader import ensure_resources_loaded
from ui.core.utils import get_ui_attr, safe_connect

UI_ROOT = Path(__file__).resolve().parents[1]
UI_PATH_SINGLE = UI_ROOT / "tips_sigle.ui"   # 仅「确认」
UI_PATH_QUESTION = UI_ROOT / "tips.ui"       # 「取消」+「确认」

ICON_GANTAN = ":/main/pic/icon_dialog_gantan.png"
ICON_CHENGGONG = ":/main/pic/icon_dialog_chengong.png"


class TipsIconType(Enum):
    """提示弹窗图标类型。"""

    WARNING = "warning"
    SUCCESS = "success"


def _resolve_icon_type(message: str, success: bool | None) -> TipsIconType:
    if success is not None:
        return TipsIconType.SUCCESS if success else TipsIconType.WARNING
    if "成功" in str(message or ""):
        return TipsIconType.SUCCESS
    return TipsIconType.WARNING


class TipsDialog(OverlayDialog):
    """单按钮提示用 tips_sigle.ui，双按钮确认用 tips.ui。"""

    def __init__(
        self,
        parent=None,
        message: str = "",
        question: bool = False,
        success: bool | None = None,
        title: str = "提示",
    ):
        super().__init__(parent)
        ensure_resources_loaded()
        self._logger = logging.getLogger(__name__)
        ui_path = UI_PATH_QUESTION if question else UI_PATH_SINGLE
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QIODevice.ReadOnly):
            raise FileNotFoundError(f"无法打开 UI 文件: {ui_path}")
        loader = QUiLoader()
        self.ui = loader.load(ui_file)
        ui_file.close()
        if self.ui is None:
            raise RuntimeError(f"无法加载 UI 文件: {ui_path}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        close_btn = get_ui_attr(self.ui, "pushButton_close")
        safe_connect(self._logger, getattr(close_btn, "clicked", None), self.reject)
        confirm_btn = get_ui_attr(self.ui, "pushButton_confirm")
        if question:
            cancel_btn = get_ui_attr(self.ui, "pushButton_cancel")
            if cancel_btn is not None:
                safe_connect(self._logger, getattr(cancel_btn, "clicked", None), self.reject)
            safe_connect(self._logger, getattr(confirm_btn, "clicked", None), self.accept)
            self.set_icon(TipsIconType.WARNING)
        else:
            safe_connect(self._logger, getattr(confirm_btn, "clicked", None), self.reject)
            self.set_icon(_resolve_icon_type(message, success))

        self.set_title(title)
        self.set_message(message)

    def set_title(self, text: str) -> None:
        title_label = get_ui_attr(self.ui, "label_title")
        if title_label is not None:
            title_label.setText(str(text or "提示"))

    def set_message(self, text: str) -> None:
        msg_label = get_ui_attr(self.ui, "label_message")
        if msg_label is not None:
            msg_label.setText(str(text or ""))

    def set_icon(self, icon_type: TipsIconType) -> None:
        icon_label = get_ui_attr(self.ui, "label_icon")
        if icon_label is None:
            return
        icon_path = ICON_CHENGGONG if icon_type == TipsIconType.SUCCESS else ICON_GANTAN
        pixmap = QPixmap(icon_path)
        if pixmap.isNull():
            self._logger.warning("提示弹窗图标加载失败: %s", icon_path)
            return
        icon_label.setStyleSheet("")
        icon_label.setPixmap(
            pixmap.scaled(
                55,
                55,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    @staticmethod
    def show_tips(
        parent=None,
        message: str = "",
        title: str = "提示",
        success: bool | None = None,
    ) -> None:
        """显示单按钮提示框（点击确认/关闭后返回）。"""
        d = TipsDialog(parent, message=message, question=False, success=success, title=title)
        d.exec()

    @staticmethod
    def show_confirm(
        parent=None,
        message: str = "",
        confirm_text: str = "确认",
        cancel_text: str = "取消",
        title: str = "提示",
    ) -> bool:
        """显示双按钮确认框，使用 tips.ui。返回 True 表示点击确认按钮，False 表示取消或关闭。"""
        d = TipsDialog(parent, message=message, question=True, title=title)
        cancel_btn = get_ui_attr(d.ui, "pushButton_cancel")
        confirm_btn = get_ui_attr(d.ui, "pushButton_confirm")
        if cancel_btn is not None:
            cancel_btn.setText(str(cancel_text or "取消"))
        if confirm_btn is not None:
            confirm_btn.setText(str(confirm_text or "确认"))
        return d.exec() == QDialog.DialogCode.Accepted
