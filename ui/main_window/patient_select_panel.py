from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class _PatientCard(QFrame):
    clicked = Signal(dict)

    def __init__(self, patient: Dict[str, Any], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._patient = patient
        self._selected = False
        self._build_ui()
        self._apply_style()

    def patient(self) -> Dict[str, Any]:
        return self._patient

    def set_selected(self, selected: bool) -> None:
        self._selected = bool(selected)
        self._apply_style()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._patient)
        super().mousePressEvent(event)

    def _build_ui(self) -> None:
        self.setObjectName("patientCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(96)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        avatar = QLabel(self._get_avatar_text())
        avatar.setFixedSize(34, 34)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(
            "background-color: #F2F4F7;"
            "border-radius: 10px;"
            "color: #8E8E93;"
            "font-size: 15px;"
            "font-weight: 600;"
        )
        avatar.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(avatar, 0, Qt.AlignTop)

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(6)

        name_row = QHBoxLayout()
        name_row.setContentsMargins(0, 0, 0, 0)
        name_row.setSpacing(6)

        name_label = QLabel(str(self._patient.get("Name", "") or "未命名"))
        name_label.setStyleSheet("color: #1F1F1F; font-size: 15px; font-weight: 600;")
        name_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        name_row.addWidget(name_label)

        meta_text = self._build_meta_text()
        if meta_text:
            meta_label = QLabel(meta_text)
            meta_label.setStyleSheet("color: #8E8E93; font-size: 12px;")
            meta_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            name_row.addWidget(meta_label)

        name_row.addStretch()
        info_layout.addLayout(name_row)

        visit_label = QLabel(f"入院时间：{self._format_visit_time()}")
        visit_label.setStyleSheet("color: #6B7280; font-size: 12px;")
        visit_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        info_layout.addWidget(visit_label)

        info_layout.addStretch()
        layout.addLayout(info_layout, 1)

    def _get_avatar_text(self) -> str:
        name = str(self._patient.get("Name", "") or "").strip()
        return name[:1] or "?"

    def _build_meta_text(self) -> str:
        sex = str(self._patient.get("Sex", "") or "").strip()
        age = self._patient.get("Age")
        age_text = ""
        if age not in (None, ""):
            age_text = f"{age}岁"
        return " ".join(part for part in (sex, age_text) if part)

    def _format_visit_time(self) -> str:
        visit_time = str(self._patient.get("VisitTime", "") or "").strip()
        if not visit_time:
            return "--"
        return visit_time.replace("/", "-")

    def _apply_style(self) -> None:
        if self._selected:
            self.setStyleSheet(
                "QFrame#patientCard {"
                "background-color: #FFFFFF;"
                "border: 2px solid #4B86FC;"
                "border-radius: 16px;"
                "}"
            )
        else:
            self.setStyleSheet(
                "QFrame#patientCard {"
                "background-color: #FFFFFF;"
                "border: 1px solid #E8ECF3;"
                "border-radius: 16px;"
                "}"
                "QFrame#patientCard:hover {"
                "border: 1px solid #C8D7FF;"
                "}"
            )


class PatientSelectPanel(QWidget):
    patient_selected = Signal(dict)

    def __init__(self, patient_app=None, parent: Optional[QWidget] = None, logger: Optional[logging.Logger] = None) -> None:
        super().__init__(parent)
        self._logger = logger or logging.getLogger(__name__)
        self.patient_app = patient_app
        self._cards: List[_PatientCard] = []
        self._all_patients: List[Dict[str, Any]] = []
        self._selected_patient_id: Optional[str] = None
        self._build_ui()
        self.refresh_patients()

    def focus_search(self) -> None:
        self._search_input.setFocus()
        self._search_input.selectAll()

    def refresh_patients(self, keyword: Optional[str] = None, selected_patient: Optional[Dict[str, Any]] = None) -> None:
        if selected_patient is not None:
            self._selected_patient_id = self._patient_key(selected_patient)

        text = self._search_input.text().strip()
        search_keyword = text if keyword is None else str(keyword).strip()

        patients: List[Dict[str, Any]] = []
        if self.patient_app:
            try:
                if search_keyword:
                    patients = self.patient_app.search_patients(search_keyword)
                else:
                    patients = self.patient_app.get_patients()
            except Exception:
                self._logger.exception("加载患者列表失败")
                patients = []

        self._all_patients = list(patients or [])
        self._render_cards()

    def set_selected_patient(self, patient: Optional[Dict[str, Any]]) -> None:
        self._selected_patient_id = self._patient_key(patient)
        self._update_card_selection()

    def _build_ui(self) -> None:
        self.setObjectName("patientSelectPanel")
        self.setStyleSheet(
            "QWidget#patientSelectPanel {"
            "background: #F7F8FC;"
            "border-radius: 24px;"
            "}"
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(14)

        search_wrap = QFrame()
        search_wrap.setObjectName("searchWrap")
        search_wrap.setStyleSheet(
            "QFrame#searchWrap {"
            "background: #FFFFFF;"
            "border: 1px solid #EEF1F5;"
            "border-radius: 16px;"
            "}"
        )
        search_layout = QHBoxLayout(search_wrap)
        search_layout.setContentsMargins(14, 10, 14, 10)
        search_layout.setSpacing(8)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索患者姓名")
        self._search_input.setFrame(False)
        self._search_input.setStyleSheet(
            "QLineEdit {"
            "background: transparent;"
            "border: none;"
            "color: #1F1F1F;"
            "font-size: 13px;"
            "}"
        )
        self._search_input.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self._search_input, 1)

        search_icon = QLabel()
        search_icon.setFixedSize(18, 18)
        search_icon.setStyleSheet("border-image: url(:/treat/pic/treat_search.png);")
        search_layout.addWidget(search_icon, 0, Qt.AlignRight | Qt.AlignVCenter)

        root_layout.addWidget(search_wrap)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 4px 0 4px 0; }"
            "QScrollBar::handle:vertical { background: #D7DDEA; border-radius: 4px; min-height: 24px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
        )

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(12)
        self._list_layout.addStretch()

        scroll_area.setWidget(self._list_widget)
        root_layout.addWidget(scroll_area, 1)

    def _render_cards(self) -> None:
        self._clear_cards()
        self._cards = []

        if not self._all_patients:
            empty = QLabel("暂无患者")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #9AA2B1; font-size: 13px; padding: 24px 0;")
            empty.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self._list_layout.insertWidget(0, empty)
            return

        for patient in self._all_patients:
            card = _PatientCard(patient, self._list_widget)
            card.clicked.connect(self._on_card_clicked)
            self._cards.append(card)
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)

        self._update_card_selection()

    def _clear_cards(self) -> None:
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _update_card_selection(self) -> None:
        for card in self._cards:
            card.set_selected(self._patient_key(card.patient()) == self._selected_patient_id)

    def _on_search_text_changed(self, text: str) -> None:
        self.refresh_patients(keyword=text)

    def _on_card_clicked(self, patient: Dict[str, Any]) -> None:
        self._selected_patient_id = self._patient_key(patient)
        self._update_card_selection()
        self.patient_selected.emit(patient)

    @staticmethod
    def _patient_key(patient: Optional[Dict[str, Any]]) -> Optional[str]:
        if not patient:
            return None
        value = patient.get("PatientId") or patient.get("Name") or ""
        text = str(value).strip()
        return text or None
