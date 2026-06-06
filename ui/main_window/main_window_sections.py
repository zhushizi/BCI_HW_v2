"""
主窗口拆分模块：导航、用户信息、设备状态、治疗流程。
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, QRect, QSize, QTimer, QObject, QEvent, QPoint
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QMessageBox, QGraphicsDropShadowEffect, QVBoxLayout, QFrame, QLabel

from ui.core.utils import get_ui_attr, safe_call, safe_connect
from ui.dialogs.tips_dialog import TipsDialog
from ui.main_window.patient_select_panel import PatientSelectPanel


class MainWindowNavigation:
    def __init__(self, host):
        self._host = host
        self.ui = host.ui
        self.logger = host.logger

    def bind(self) -> None:
        def connect_click(name: str, slot: Callable[[], None]) -> None:
            button = get_ui_attr(self.ui, name)
            safe_connect(self.logger, getattr(button, "clicked", None), slot)

        connect_click("pushButton_treat", lambda: self.switch_tab(0))
        connect_click("pushButton_patient", lambda: self.switch_tab(1))
        connect_click("pushButton_plan", lambda: self.switch_tab(2))
        connect_click("pushButton_set", lambda: self.switch_tab(3))
        connect_click("pushButton_report", self._on_report_clicked)
        connect_click("pushButton_tab2home", self.switch_treat_tab_to_first)

        tab_widget = get_ui_attr(self.ui, "tabWidget")
        if tab_widget:
            safe_connect(self.logger, getattr(tab_widget, "currentChanged", None), self.on_tab_changed)
            safe_call(self.logger, tab_widget.tabBar().hide)
        tab_main = get_ui_attr(self.ui, "tabWidget_main")
        if tab_main:
            safe_call(self.logger, tab_main.tabBar().hide)
            safe_connect(self.logger, getattr(tab_main, "currentChanged", None), lambda _: self._update_line2_visibility())
        plan_btn = get_ui_attr(self.ui, "pushButton_plan")
        safe_call(self.logger, getattr(plan_btn, "setVisible", None), False)

    def init_ui(self) -> None:
        self._host.setWindowTitle("BCI硬件控制系统")
        self._host._report_selected = False
        tab_widget = get_ui_attr(self.ui, "tabWidget")
        if tab_widget:
            tab_widget.setCurrentIndex(0)
            self._host._current_tab_index = 0
        tab_widget2 = get_ui_attr(self.ui, "tabWidget_2")
        if tab_widget2:
            safe_call(self.logger, tab_widget2.tabBar().hide)
            tab_widget2.setCurrentIndex(0)
        tab_main = get_ui_attr(self.ui, "tabWidget_main")
        if tab_main:
            tab_main.setCurrentIndex(0)
        label_patient = get_ui_attr(self.ui, "label_patient")
        safe_call(self.logger, getattr(label_patient, "setAlignment", None), Qt.AlignCenter)
        self._host._treat_flow.refresh_patient_select_panel()
        self._update_line2_visibility()

    def switch_tab(self, tab_index: int) -> None:
        tab_widget = get_ui_attr(self.ui, "tabWidget")
        if tab_widget is None:
            return
        if getattr(self._host, "_current_tab_index", 0) == 0 and tab_index != 0:
            self._host.treat_controller.on_exit_treat_page()
        if 0 <= tab_index < tab_widget.count():
            self._host._report_selected = False
            tab_widget.setCurrentIndex(tab_index)
            self._host._current_tab_index = tab_index
            self._update_line2_visibility()
            self.update_button_states()
            if tab_index == 0:
                self._host._treat_flow.refresh_patient_select_panel()
            elif tab_index == 1:
                self._host.patient_controller.refresh()
            elif tab_index == 2:
                self._host.plan_controller.refresh()
            elif tab_index == 3:
                self._host.set_controller.refresh()
            elif tab_index == getattr(getattr(self._host, "report_controller", None), "REPORT_TAB_INDEX", -1):
                self._host.report_controller.refresh()

    def on_tab_changed(self, index: int) -> None:
        previous_index = getattr(self._host, "_current_tab_index", 0)
        self._host._current_tab_index = index
        self._update_line2_visibility()
        report_tab_index = getattr(getattr(self._host, "report_controller", None), "REPORT_TAB_INDEX", -1)
        self._host._report_selected = index == report_tab_index
        if previous_index == 0 and index != 0:
            self._host.treat_controller.on_exit_treat_page()
        self.update_button_states()
        if index == 0:
            self._host._treat_flow.refresh_patient_select_panel()
        elif index == 1:
            self._host.patient_controller.refresh()
        elif index == 2:
            self._host.plan_controller.refresh()
        elif index == 3:
            self._host.set_controller.refresh()
        elif index == report_tab_index:
            self._host.report_controller.refresh()

    def switch_treat_tab_to_first(self) -> None:
        tab_widget = get_ui_attr(self.ui, "tabWidget")
        if tab_widget:
            tab_widget.setCurrentIndex(0)
        tab_main = get_ui_attr(self.ui, "tabWidget_main")
        if tab_main:
            tab_main.setCurrentIndex(0)
        self._host._current_tab_index = 0
        self._host._report_selected = False
        self._update_line2_visibility()
        self.update_button_states()
        self._host._treat_flow.refresh_patient_select_panel()

    def _update_line2_visibility(self) -> None:
        line_2 = get_ui_attr(self.ui, "line_2")
        if line_2 is None:
            return
        tab_widget_main = get_ui_attr(self.ui, "tabWidget_main")
        tab_2 = get_ui_attr(self.ui, "tab_2")
        in_preprocess_page = False
        if tab_widget_main is not None and tab_2 is not None:
            try:
                in_preprocess_page = tab_widget_main.currentWidget() is tab_2
            except Exception:
                in_preprocess_page = False
        safe_call(self.logger, getattr(line_2, "setVisible", None), not in_preprocess_page)

    def update_button_states(self) -> None:
        button_configs = [
            ("pushButton_treat", "main_treat_on.png", "main_treat_off.png"),
            ("pushButton_patient", "main_patient_on.png", "main_patient_off.png"),
            ("pushButton_plan", "main_plan_on.png", "main_plan_off.png"),
            ("pushButton_set", "main_set_on.png", "main_set_off.png"),
        ]
        for idx, (button_name, on_image, off_image) in enumerate(button_configs):
            button = get_ui_attr(self.ui, button_name)
            if button is None:
                continue
            image_path = f":/main/pic/{on_image}" if idx == self._host._current_tab_index else f":/main/pic/{off_image}"
            button.setStyleSheet(
                f"QPushButton#{button_name} {{"
                f"    border-image: url({image_path});"
                f"    background: transparent;"
                f"    border: none;"
                f"}}"
            )
        self._update_report_button_state(bool(getattr(self._host, "_report_selected", False)))

    def _on_report_clicked(self) -> None:
        tab_widget = get_ui_attr(self.ui, "tabWidget")
        report_tab_index = getattr(getattr(self._host, "report_controller", None), "REPORT_TAB_INDEX", -1)
        if tab_widget is not None and 0 <= report_tab_index < tab_widget.count():
            self._host._report_selected = True
            tab_widget.setCurrentIndex(report_tab_index)
            self._host.report_controller.refresh()
        self._update_report_button_state(True)

    def _update_report_button_state(self, selected: bool) -> None:
        button_name = "pushButton_report"
        button = get_ui_attr(self.ui, button_name)
        if button is None:
            return
        image_name = "main_report_on.png" if selected else "main_report_off.png"
        button.setStyleSheet(
            f"QPushButton#{button_name} {{"
            f"    border-image: url(:/main/pic/{image_name});"
            f"    background: transparent;"
            f"    border: none;"
            f"}}"
        )


class MainWindowUserInfo:
    _CONFIG_KEY_HOSPITAL = "hospital_name"
    _CONFIG_KEY_DEPARTMENT = "department_name"
    _MAX_HOSPITAL_TEXT_LEN = 18
    _MAX_DEPARTMENT_TEXT_LEN = 9

    def __init__(self, host):
        self._host = host
        self.ui = host.ui

    def bind(self) -> None:
        self._init_org_inputs()
        btn_confirm = get_ui_attr(self.ui, "pushButton_other_confirm")
        safe_connect(
            self._host.logger,
            getattr(btn_confirm, "clicked", None),
            self._on_other_confirm,
        )
        btn_reset = get_ui_attr(self.ui, "pushButton_other_reset")
        safe_connect(
            self._host.logger,
            getattr(btn_reset, "clicked", None),
            self._on_other_reset,
        )

    def _init_org_inputs(self) -> None:
        hospital_edit = get_ui_attr(self.ui, "lineEdit_hospital_name")
        if hospital_edit:
            safe_call(
                self._host.logger,
                getattr(hospital_edit, "setMaxLength", None),
                self._MAX_HOSPITAL_TEXT_LEN,
            )
        department_edit = get_ui_attr(self.ui, "lineEdit_department_name")
        if department_edit:
            safe_call(
                self._host.logger,
                getattr(department_edit, "setMaxLength", None),
                self._MAX_DEPARTMENT_TEXT_LEN,
            )
        for label_name in ("label_hosipital", "label_department"):
            label = get_ui_attr(self.ui, label_name)
            if label:
                safe_call(self._host.logger, getattr(label, "setWordWrap", None), True)

    @classmethod
    def _normalize_org_text(cls, text: str, max_len: int) -> str:
        return str(text or "").strip()[:max_len]

    @classmethod
    def _format_org_display_text(cls, text: str, max_len: int) -> str:
        normalized = cls._normalize_org_text(text, max_len)
        if not normalized:
            return ""
        return "\n".join(
            normalized[i : i + max_len]
            for i in range(0, len(normalized), max_len)
        )

    def init_org_info(self) -> None:
        config_app = getattr(self._host, "config_app", None)
        if not config_app:
            return
        hospital = self._normalize_org_text(
            config_app.get(self._CONFIG_KEY_HOSPITAL, ""),
            self._MAX_HOSPITAL_TEXT_LEN,
        )
        department = self._normalize_org_text(
            config_app.get(self._CONFIG_KEY_DEPARTMENT, ""),
            self._MAX_DEPARTMENT_TEXT_LEN,
        )
        self._apply_org_info(hospital, department)

    def _apply_org_info(self, hospital: str, department: str) -> None:
        hospital = self._normalize_org_text(hospital, self._MAX_HOSPITAL_TEXT_LEN)
        department = self._normalize_org_text(department, self._MAX_DEPARTMENT_TEXT_LEN)
        hospital_edit = get_ui_attr(self.ui, "lineEdit_hospital_name")
        hospital_label = get_ui_attr(self.ui, "label_hosipital")
        if hospital_edit:
            safe_call(self._host.logger, getattr(hospital_edit, "setText", None), hospital)
        if hospital_label:
            safe_call(
                self._host.logger,
                getattr(hospital_label, "setText", None),
                self._format_org_display_text(hospital, self._MAX_HOSPITAL_TEXT_LEN),
            )
        department_edit = get_ui_attr(self.ui, "lineEdit_department_name")
        department_label = get_ui_attr(self.ui, "label_department")
        if department_edit:
            safe_call(self._host.logger, getattr(department_edit, "setText", None), department)
        if department_label:
            safe_call(
                self._host.logger,
                getattr(department_label, "setText", None),
                self._format_org_display_text(department, self._MAX_DEPARTMENT_TEXT_LEN),
            )

    def _read_org_inputs(self) -> tuple[str, str]:
        hospital_edit = get_ui_attr(self.ui, "lineEdit_hospital_name")
        department_edit = get_ui_attr(self.ui, "lineEdit_department_name")
        hospital = self._normalize_org_text(
            hospital_edit.text() if hospital_edit else "",
            self._MAX_HOSPITAL_TEXT_LEN,
        )
        department = self._normalize_org_text(
            department_edit.text() if department_edit else "",
            self._MAX_DEPARTMENT_TEXT_LEN,
        )
        return hospital, department

    def _save_org_info(self, hospital: str, department: str) -> None:
        config_app = getattr(self._host, "config_app", None)
        if not config_app:
            return
        ok = config_app.update(
            {
                self._CONFIG_KEY_HOSPITAL: hospital,
                self._CONFIG_KEY_DEPARTMENT: department,
            }
        )
        if not ok:
            self._host.logger.warning("保存医院/科室配置失败")

    def _on_other_confirm(self) -> None:
        hospital, department = self._read_org_inputs()
        self._apply_org_info(hospital, department)
        self._save_org_info(hospital, department)

    def _on_other_reset(self) -> None:
        self._apply_org_info("", "")
        self._save_org_info("", "")


class MainWindowDeviceStatus:
    def __init__(self, host):
        self._host = host
        self.ui = host.ui
        self._ws_timer: Optional[QTimer] = None
        self._status_tip_filter: Optional[_StatusIndicatorTipFilter] = None

    def init_device_status(self) -> None:
        label_pingpong = get_ui_attr(self.ui, "label_pingpong")
        if label_pingpong:
            label_pingpong.setText("")
            label_pingpong.setToolTip("")
            label_pingpong.setProperty("status_ok", False)
            self.set_pingpong_indicator(is_alive=False)
            self.update_treat_controls_by_pingpong()
        label_wifi = get_ui_attr(self.ui, "label_wifi")
        safe_call(self._host.logger, getattr(label_wifi, "setText", None), "")
        safe_call(self._host.logger, getattr(label_wifi, "setToolTip", None), "")
        safe_call(self._host.logger, getattr(label_wifi, "setProperty", None), "status_ok", False)
        self._install_status_tips()
        self._init_ws_status()

        if self._host.pingpong_service:
            try:
                interval_sec = 3.0
                if getattr(self._host, "config_app", None):
                    try:
                        interval_sec = float(self._host.config_app.get("pingpong_interval_sec", 3.0))
                    except Exception:
                        interval_sec = 3.0
                self._host.pingpong_service.configure(interval_sec=interval_sec, timeout_sec=5.0)

                def _cb(alive: bool, last_seen_sec):
                    self._host.pingpong_status_changed.emit(bool(alive), last_seen_sec)

                self._host.pingpong_service.set_status_callback(_cb)
                self._host.pingpong_service.enable()
                alive, last_seen_sec = self._host.pingpong_service.get_current_status()
                self._host.pingpong_status_changed.emit(alive, last_seen_sec)
            except Exception as e:
                self._host.logger.error(f"心跳服务初始化失败: {e}")

    def set_pingpong_indicator(self, is_alive: bool) -> None:
        label_pingpong = get_ui_attr(self.ui, "label_pingpong")
        if label_pingpong is None:
            return
        label_pingpong.setProperty("status_ok", bool(is_alive))
        if is_alive:
            label_pingpong.setStyleSheet("border-image: url(:/main/pic/main_pingpong_on.png);")
        else:
            label_pingpong.setStyleSheet("border-image: url(:/main/pic/main_pingpong_off.png);")

    def _init_ws_status(self) -> None:
        self._set_wifi_indicator(False)
        if not self._host.ws_service:
            return
        if self._ws_timer is None:
            self._ws_timer = QTimer(self.ui)
            self._ws_timer.setInterval(1000)
            safe_connect(self._host.logger, self._ws_timer.timeout, self._poll_ws_status)
        if not self._ws_timer.isActive():
            self._ws_timer.start()

    def _poll_ws_status(self) -> None:
        if not self._host.ws_service:
            self._set_wifi_indicator(False)
            return
        try:
            self._set_wifi_indicator(self._host.ws_service.is_connected())
        except Exception:
            self._set_wifi_indicator(False)

    def _set_wifi_indicator(self, is_connected: bool) -> None:
        label_wifi = get_ui_attr(self.ui, "label_wifi")
        if label_wifi is None:
            return
        label_wifi.setProperty("status_ok", bool(is_connected))
        if is_connected:
            label_wifi.setStyleSheet("border-image: url(:/main/pic/main_wifi_on.png);")
        else:
            label_wifi.setStyleSheet("border-image: url(:/main/pic/main_wifi_off.png);")

    def on_pingpong_status_changed(self, is_alive: bool, last_seen_sec) -> None:
        self.set_pingpong_indicator(bool(is_alive))
        self.update_treat_controls_by_pingpong()

    def is_pingpong_online(self) -> bool:
        label_pingpong = get_ui_attr(self.ui, "label_pingpong")
        if label_pingpong is None:
            return True
        try:
            return bool(label_pingpong.property("status_ok"))
        except Exception:
            return True

    def update_treat_controls_by_pingpong(self) -> None:
        try:
            is_online = self.is_pingpong_online()
            if self._host.treat_controller and self._host.treat_controller.stim_ctrl:
                self._host.treat_controller.stim_ctrl.set_hardware_online(is_online)
        except Exception:
            pass

    def _install_status_tips(self) -> None:
        if self._status_tip_filter is None:
            self._status_tip_filter = _StatusIndicatorTipFilter(self.ui)
        label_pingpong = get_ui_attr(self.ui, "label_pingpong")
        label_wifi = get_ui_attr(self.ui, "label_wifi")
        if label_pingpong is not None:
            label_pingpong.installEventFilter(self._status_tip_filter)
        if label_wifi is not None:
            label_wifi.installEventFilter(self._status_tip_filter)


class _StatusIndicatorTipFilter(QObject):
    """状态图标专用悬浮提示（独立样式，不使用父级/全局 tooltip 样式）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._popup = QFrame(None, Qt.ToolTip | Qt.FramelessWindowHint)
        self._popup.setObjectName("statusIndicatorPopup")
        self._popup.setStyleSheet(
            "QFrame#statusIndicatorPopup {"
            "background: #FFFFFF;"
            "border: 1px solid #D0D5DD;"
            "border-radius: 8px;"
            "}"
            "QLabel {"
            "color: #1F2937;"
            "font-size: 12px;"
            "padding: 6px 10px;"
            "background: transparent;"
            "}"
        )
        layout = QVBoxLayout(self._popup)
        layout.setContentsMargins(0, 0, 0, 0)
        self._label = QLabel("")
        layout.addWidget(self._label)

    def eventFilter(self, watched, event):
        name = getattr(watched, "objectName", lambda: "")()
        if name not in ("label_wifi", "label_pingpong"):
            return super().eventFilter(watched, event)
        if event.type() == QEvent.Enter:
            self._show_tip(watched, name)
        elif event.type() in (QEvent.Leave, QEvent.Hide):
            self._popup.hide()
        return super().eventFilter(watched, event)

    def _show_tip(self, widget, name: str) -> None:
        is_ok = bool(widget.property("status_ok"))
        if name == "label_wifi":
            text = "上位机通讯正常" if is_ok else "上位机通讯不正常"
        else:
            text = "下位机连接正常" if is_ok else "下位机连接不正常"
        self._label.setText(text)
        self._popup.adjustSize()
        x = max(0, (widget.width() - self._popup.width()) // 2)
        pos = widget.mapToGlobal(QPoint(x, widget.height() + 8))
        self._popup.move(pos)
        self._popup.show()


_PARADIGM_OVERLAY_LABELS = (
    "label_23",
    "label_24",
    "label_25",
    "label_27",
    "label_28",
    "label_29",
    "label_ssvep_up_icon",
    "label_ssvep_down_icon",
    "label_ssmvep_up_icon",
    "label_ssmvep_down_icon",
    "label_mi_up_icon",
    "label_mi_down_icon",
)


class MainWindowTreatFlow:
    def __init__(self, host):
        self._host = host
        self.ui = host.ui
        self.logger = host.logger
        self._hover_filters: list[_HoverShadowFilter] = []
        self._patient_select_panel: Optional[PatientSelectPanel] = None
        self._paradigm_icon_rects: dict[str, QRect] = {}

    def bind(self) -> None:
        def connect_click(name: str, slot: Callable[[], None]) -> None:
            button = get_ui_attr(self.ui, name)
            safe_connect(self.logger, getattr(button, "clicked", None), slot)

        self._ensure_patient_select_panel()
        connect_click("pushButton_tab1select", self.open_patient_select_dialog)
        self._set_paradigm_overlays_mouse_transparent()

        treat_buttons = [
            "pushButton_up_ssvep",
            "pushButton_up_ssmvep",
            "pushButton_up_mi",
            "pushButton_up_mix",
            "pushButton_down_ssvep",
            "pushButton_down_ssmvep",
            "pushButton_down_mi",
            "pushButton_down_mix",
        ]
        for button_name in treat_buttons:
            button = get_ui_attr(self.ui, button_name)
            if button:
                self._attach_hover_shadow(
                    button,
                    lambda hovered, name=button_name: self._set_paradigm_label_hovered(name, hovered),
                )
                safe_connect(
                    self.logger,
                    getattr(button, "clicked", None),
                    lambda checked=False, name=button_name: self.open_treat_page(name),
                )
        if not any(get_ui_attr(self.ui, name) for name in treat_buttons):
            connect_click("pushButton", self.open_treat_page)
            connect_click("pushButton_3", self.open_treat_page)

        start_evaluate_btn = get_ui_attr(self.ui, "pushButton_startevaluate")
        safe_connect(self.logger, getattr(start_evaluate_btn, "clicked", None), self.on_start_evaluate_clicked)

    def _set_paradigm_overlays_mouse_transparent(self) -> None:
        for name in _PARADIGM_OVERLAY_LABELS:
            label = get_ui_attr(self.ui, name)
            if label is not None:
                label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def _ensure_patient_select_panel(self) -> None:
        if self._patient_select_panel is not None:
            return

        container = get_ui_attr(self.ui, "widget_patient_select")
        if container is None:
            return

        layout = container.layout()
        if layout is None:
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

        self._patient_select_panel = PatientSelectPanel(
            patient_app=self._host.patient_app,
            parent=container,
            logger=self.logger,
        )
        layout.addWidget(self._patient_select_panel)
        safe_connect(self.logger, self._patient_select_panel.patient_selected, self.on_patient_selected)
        safe_connect(self.logger, self._patient_select_panel.patient_cleared, self.on_patient_deselected)

    def _attach_hover_shadow(self, button, on_hover_changed: Optional[Callable[[bool], None]] = None) -> None:
        effect = QGraphicsDropShadowEffect(button)
        effect.setBlurRadius(18)
        effect.setOffset(0, 0)
        effect.setColor(QColor(0, 0, 0, 45))
        effect.setEnabled(False)
        button.setGraphicsEffect(effect)
        hover_filter = _HoverShadowFilter(button, effect, on_hover_changed=on_hover_changed)
        button.installEventFilter(hover_filter)
        self._hover_filters.append(hover_filter)

    def _set_paradigm_label_hovered(self, button_name: str, hovered: bool) -> None:
        label_map = {
            "pushButton_up_ssvep": "label_23",
            "pushButton_up_ssmvep": "label_24",
            "pushButton_up_mi": "label_25",
            "pushButton_down_ssvep": "label_27",
            "pushButton_down_ssmvep": "label_28",
            "pushButton_down_mi": "label_29",
        }
        label = get_ui_attr(self.ui, label_map.get(button_name, ""))
        if label is None:
            return
        color = "rgb(88, 122, 244)" if hovered else "rgb(31, 31, 31)"
        safe_call(self.logger, getattr(label, "setStyleSheet", None), f"color: {color};")
        self._set_paradigm_icon_hovered(button_name, hovered)

    def _set_paradigm_icon_hovered(self, button_name: str, hovered: bool) -> None:
        icon_map = {
            "pushButton_up_ssvep": "label_ssvep_up_icon",
            "pushButton_down_ssvep": "label_ssvep_down_icon",
            "pushButton_up_ssmvep": "label_ssmvep_up_icon",
            "pushButton_down_ssmvep": "label_ssmvep_down_icon",
            "pushButton_up_mi": "label_mi_up_icon",
            "pushButton_down_mi": "label_mi_down_icon",
        }
        icon_name = icon_map.get(button_name)
        if not icon_name:
            return
        icon_label = get_ui_attr(self.ui, icon_name)
        if icon_label is None:
            return

        if icon_name not in self._paradigm_icon_rects:
            self._paradigm_icon_rects[icon_name] = icon_label.geometry()
        base_rect = self._paradigm_icon_rects[icon_name]

        if not hovered:
            icon_label.setGeometry(base_rect)
            return

        scale = 1.1
        new_w = int(round(base_rect.width() * scale))
        new_h = int(round(base_rect.height() * scale))
        # 用浮点中心点计算，避免 QRect.center() 在偶数尺寸时向左上偏 1px
        center_x = base_rect.x() + base_rect.width() / 2.0
        center_y = base_rect.y() + base_rect.height() / 2.0
        new_x = int(round(center_x - new_w / 2.0))
        new_y = int(round(center_y - new_h / 2.0))
        icon_label.setGeometry(new_x, new_y, new_w, new_h)


    def open_patient_select_dialog(self) -> None:
        self.refresh_patient_select_panel()
        if self._patient_select_panel:
            self._patient_select_panel.focus_search()

    def on_patient_selected(self, patient: dict) -> None:
        patient_name = patient.get("Name", "")
        label_patient = get_ui_attr(self.ui, "label_patient")
        if label_patient:
            label_patient.setText(patient_name)
        else:
            label_fallback = get_ui_attr(self.ui, "label_11")
            safe_call(self.logger, getattr(label_fallback, "setText", None), patient_name)
        self._fill_patient_info_labels(patient)
        self._host._selected_patient = patient
        if self._patient_select_panel:
            self._patient_select_panel.refresh_patients(selected_patient=patient)
        self._host.treat_controller.set_current_patient(patient)

    def refresh_patient_select_panel(self) -> None:
        self._ensure_patient_select_panel()
        if self._patient_select_panel:
            self._patient_select_panel.refresh_patients(selected_patient=self._host._selected_patient)

    def on_patient_deselected(self) -> None:
        if not self._host._selected_patient:
            return
        self._apply_no_patient_selected()

    def clear_patient_selection(self) -> None:
        self._apply_no_patient_selected()

    def _apply_no_patient_selected(self) -> None:
        self._host._selected_patient = None
        label_patient = get_ui_attr(self.ui, "label_patient")
        if label_patient:
            label_patient.setText("未选择患者")
        else:
            label_fallback = get_ui_attr(self.ui, "label_11")
            safe_call(self.logger, getattr(label_fallback, "setText", None), "未选择患者")
        if self._patient_select_panel:
            self._patient_select_panel.set_selected_patient(None)
        self._fill_patient_info_labels(None)
        if getattr(self._host, "treat_controller", None):
            self._host.treat_controller.set_current_patient(None)

    @staticmethod
    def extract_patient_id(patient: dict | None) -> str | None:
        if not patient:
            return None
        pid = patient.get("PatientId") or patient.get("Name") or ""
        pid = str(pid).strip()
        return pid or None

    def open_treat_page(self, button_name: str | None = None) -> None:
        if not self._host._selected_patient:
            TipsDialog.show_tips(self._host, "请先选择患者")
            return
        if getattr(self._host, "treat_flow_app", None) and button_name:
            self._host.treat_flow_app.start_treat_from_button(self._host._selected_patient, button_name)
        self._host.treat_controller.set_current_patient(self._host._selected_patient)
        self._host.treat_controller.enter_preprocess_page()

    def _fill_patient_info_labels(self, patient: dict | None) -> None:
        patient = patient or {}

        def _txt(value) -> str:
            text = str(value or "").strip()
            return text if text else "--"

        def _birthday_text() -> str:
            for key in ("Birthday", "BirthDay", "birth_day", "birthdate"):
                value = patient.get(key)
                if value not in (None, ""):
                    return _txt(value)
            return "--"

        def _height_weight_text() -> str:
            height_raw = patient.get("Height")
            weight_raw = patient.get("Weight")
            height = "" if height_raw in (None, "") else str(height_raw).strip()
            weight = "" if weight_raw in (None, "") else str(weight_raw).strip()
            if height and weight:
                return f"{height}/{weight}"
            if height:
                return height
            if weight:
                return weight
            return "--"

        label_values = {
            "label_patient_id": _txt(patient.get("PatientId")),
            "label_sex": _txt(patient.get("Sex")),
            "label_birthday": _birthday_text(),
            "label_height_weight": _height_weight_text(),
            "label_visit_time": _txt(patient.get("VisitTime")).replace("/", "-"),
            "label_age": _txt(patient.get("Age")),
        }
        for label_name, text in label_values.items():
            label = get_ui_attr(self.ui, label_name)
            safe_call(self.logger, getattr(label, "setText", None), f"  {text}")

    def start_treatment_both_channels(self) -> None:
        try:
            if self._host.hardware_app:
                self._host.hardware_app.start_treatment_dual()
        except Exception as e:
            self.logger.error(f"发送治疗开始命令失败: {e}")

    def on_start_evaluate_clicked(self) -> None:
        try:
            if self._host.treat_controller and self._host.treat_controller.impedance_ctrl:
                self._host.treat_controller.impedance_ctrl.stop_impedance()
        except Exception:
            pass
        if getattr(self._host, "treat_flow_app", None):
            self._host.treat_flow_app.send_impedance_close()
            exe_path, paradigm_class = self._host.treat_flow_app.resolve_paradigm_exe_from_session()
        else:
            exe_path, paradigm_class = None, None
        if exe_path and self._host.treat_controller and self._host.treat_controller.training_sub_ctrl:
            self._host.treat_controller.training_sub_ctrl.set_paradigm_exe_path(exe_path)
        # if self._host.ws_service:
        #     try:
        #         self._host.ws_service.send_notification(
        #             "paradigm.paradigm_class",
        #             {"paradigm_class": paradigm_class or "SSVEP", "target_class": [9, 12]},
        #         )
        #     except Exception:
        #         pass
        tab_widget2 = get_ui_attr(self.ui, "tabWidget_2")
        if tab_widget2:
            tab_widget2.setCurrentIndex(2)
        try:
            if self._host.treat_controller and self._host.treat_controller.training_sub_ctrl:
                self._host.treat_controller.training_sub_ctrl.start_paradigm_service(
                    switch_tab=False,
                    show_screen=False,
                )
        except Exception:
            pass
        self.update_title_to_practising()

    def update_title_to_practising(self) -> None:
        label_title = get_ui_attr(self.ui, "label_title")
        if label_title is None:
            return
        label_title.setText("训练中")
        label_title.setStyleSheet("")


class _HoverShadowFilter(QObject):
    def __init__(
        self,
        target,
        effect: QGraphicsDropShadowEffect,
        on_hover_changed: Optional[Callable[[bool], None]] = None,
    ):
        super().__init__(target)
        self._target = target
        self._effect = effect
        self._on_hover_changed = on_hover_changed

    def eventFilter(self, obj, event):
        if obj is self._target:
            if event.type() == QEvent.Enter:
                self._effect.setEnabled(True)
                if callable(self._on_hover_changed):
                    self._on_hover_changed(True)
            elif event.type() == QEvent.Leave:
                self._effect.setEnabled(False)
                if callable(self._on_hover_changed):
                    self._on_hover_changed(False)
        return super().eventFilter(obj, event)
