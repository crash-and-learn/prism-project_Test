# 1. 파이썬 표준 라이브러리 (기본 내장)
import sys
import random
import re
import traceback
import requests
from datetime import datetime
from typing import List, Optional, Callable, Any, Dict

# 2. 외부 데이터 및 차트 라이브러리
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

# 3. PySide6 (UI 프레임워크) 모듈
from PySide6.QtCore import (
    QAbstractTableModel, Qt, QThread, QTimer, Signal, QDate
)
from PySide6.QtGui import (
    QAction, QColor, QFont
)
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDateEdit, QDialog,
    QFormLayout, QFrame, QGraphicsDropShadowEffect, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMenu, QProgressBar, QPushButton, QRadioButton, QScrollArea, QSizePolicy,
    QSpinBox, QSplitter, QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QTableView, QTabWidget, QTextEdit, QToolBox, QTreeView, QVBoxLayout, QWidget
)


# ==========================================
# [Design System] Zinc Enterprise v3.0 (Final)
# ==========================================
THEME_CSS = """
/* Global Reset */
QMainWindow, QDialog { background-color: #09090B; color: #E4E4E7; font-family: 'Inter', 'Segoe UI', sans-serif; }
QWidget { font-size: 13px; color: #A1A1AA; }

/* Typography */
QLabel#H1 { font-size: 24px; font-weight: 700; color: #FAFAFA; letter-spacing: -0.5px; }
QLabel#H2 { font-size: 16px; font-weight: 600; color: #F4F4F5; margin-bottom: 5px; }
QLabel#Label { font-size: 12px; font-weight: 500; color: #71717A; }
QLabel#Section { font-size: 11px; font-weight: 700; color: #52525B; text-transform: uppercase; letter-spacing: 1px; }

/* Inputs */
QLineEdit, QTextEdit, QComboBox, QDateEdit, QSpinBox {
    background-color: #18181B;
    border: 1px solid #27272A;
    border-radius: 6px;
    padding: 10px 12px;
    color: #FAFAFA;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus {
    border: 1px solid #6366F1; background-color: #09090B;
}

/* Buttons */
QPushButton {
    background-color: #27272A; border: 1px solid #3F3F46; color: #FAFAFA;
    border-radius: 6px; padding: 8px 16px; font-weight: 600;
}
QPushButton:hover { background-color: #3F3F46; border-color: #52525B; }
QPushButton#Primary { background-color: #4F46E5; border: 1px solid #4338CA; color: white; }
QPushButton#Primary:hover { background-color: #4338CA; }
QPushButton#Ghost { background-color: transparent; border: none; color: #A1A1AA; }
QPushButton#Ghost:hover { color: #FAFAFA; background-color: #27272A; }
QPushButton#Danger { color: #F87171; border-color: #7F1D1D; background: rgba(127, 29, 29, 0.2); }

/* Navigation */
QFrame#Sidebar { background-color: #09090B; border-right: 1px solid #27272A; }
QListWidget#Nav { background: transparent; border: none; outline: none; margin-top: 10px; }
QListWidget#Nav::item {
    height: 40px; padding-left: 10px; border-radius: 6px; margin: 2px 10px;
    color: #A1A1AA; font-weight: 500; border: 1px solid transparent;
}
QListWidget#Nav::item:hover { background-color: #18181B; color: #FAFAFA; }
QListWidget#Nav::item:selected {
    background-color: #1E1B4B; color: #818CF8; border: 1px solid #312E81;
}

/* Cards */
QFrame#Card { background-color: #121215; border: 1px solid #27272A; border-radius: 8px; }
QGroupBox {
    border: 1px solid #27272A; border-radius: 8px; margin-top: 24px; padding-top: 15px; font-weight: 600; color: #A1A1AA;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }

/* Tables */
QTableWidget {
    background-color: transparent; border: none; gridline-color: #27272A;
    selection-background-color: #1E1B4B; selection-color: #818CF8;
}
QHeaderView::section {
    background-color: #09090B; color: #71717A; padding: 10px; border: none;
    border-bottom: 1px solid #27272A; font-weight: 600; text-transform: uppercase; font-size: 11px;
}
QTableWidget::item { padding: 8px; border-bottom: 1px solid #27272A; color: #E4E4E7; }

/* Scrollbars */
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #27272A; border-radius: 5px; min-height: 40px; }
QScrollBar::handle:vertical:hover { background: #3F3F46; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

/* Progress Bar */
QProgressBar {
    border: 1px solid #27272A; border-radius: 4px; text-align: center;
    background-color: #18181B; color: white;
}
QProgressBar::chunk { background-color: #4F46E5; border-radius: 3px; }
"""

# ==========================================
# Shared Components
# ==========================================

class Toast(QFrame):
    """Non-blocking notification overlay."""
    def __init__(self, parent, text, type="success"):
        super().__init__(parent)
        color = "#10B981" if type == "success" else "#EF4444"
        bg = "#064E3B" if type == "success" else "#7F1D1D"
        self.setStyleSheet(f"background-color: {bg}; border: 1px solid {color}; border-radius: 6px; color: white; padding: 12px;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        layout.addWidget(QLabel(f"{'✓' if type=='success' else '⚠️'}  {text}", styleSheet="border:none; background:transparent; font-weight:600;"))
        self.adjustSize()
        self.hide()

    def show_msg(self):
        if not self.parent(): return
        p_width = self.parent().width()
        self.move(p_width - self.width() - 30, 30)
        self.show()
        self.raise_()
        QTimer.singleShot(3000, self.hide)

class StatCard(QFrame):
    """KPI Indicator Card."""
    def __init__(self, title, value, delta, positive=True):
        super().__init__()
        self.setObjectName("Card")
        l = QVBoxLayout(self)
        l.setContentsMargins(20, 20, 20, 20)
        
        hl = QHBoxLayout()
        hl.addWidget(QLabel(title, objectName="Label"))
        hl.addStretch()
        icon = QLabel("📈" if positive else "📉")
        icon.setStyleSheet("border:none; background:transparent;")
        hl.addWidget(icon)
        l.addLayout(hl)
        
        v = QLabel(value, objectName="H1")
        v.setStyleSheet("font-size: 26px; margin: 5px 0;")
        l.addWidget(v)
        
        d_color = "#10B981" if positive else "#F43F5E"
        l.addWidget(QLabel(f"{'+' if positive else ''}{delta} from last month", styleSheet=f"color: {d_color}; font-weight:600; border:none;"))

class StatusBadge(QLabel):
    """Table cell status indicator."""
    def __init__(self, text, status="active"):
        super().__init__(text)
        self.setAlignment(Qt.AlignCenter)
        color = "#10B981" if status == "active" else "#F59E0B" if status == "warning" else "#71717A"
        if status == "error": color = "#EF4444"
        bg = f"{color}20" # 20% opacity hex
        self.setStyleSheet(f"background-color: {bg}; color: {color}; border-radius: 4px; padding: 4px 8px; font-weight: 700; font-size: 11px;")
        self.setFixedSize(80, 24)

class FormDialog(QDialog):
    """Generic Modal for creating items."""
    def __init__(self, title, fields):
        super().__init__()
        self.setWindowTitle(title)
        self.setFixedSize(400, 100 + (len(fields) * 50))
        self.setStyleSheet(THEME_CSS)
        
        l = QVBoxLayout(self)
        l.setContentsMargins(30, 30, 30, 30)
        l.addWidget(QLabel(title, objectName="H1"))
        l.addSpacing(10)
        
        self.inputs = {}
        for label, widget_type in fields:
            l.addWidget(QLabel(label, styleSheet="color:#A1A1AA; font-weight:600;"))
            if widget_type == "text": w = QLineEdit()
            elif widget_type == "combo": w = QComboBox(); w.addItems(["Option A", "Option B", "Option C"])
            elif widget_type == "date": w = QDateEdit(); w.setCalendarPopup(True); w.setDate(datetime.now())
            elif widget_type == "spin": w = QSpinBox(); w.setRange(0, 100)
            self.inputs[label] = w
            l.addWidget(w)
            
        l.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel"); btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Save", objectName="Primary"); btn_save.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        l.addLayout(btn_layout)

class StatusOverlay(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 180);") # 반투명 배경
        self.hide()
        
        # 중앙 카드
        self.card = QFrame(self)
        self.card.setObjectName("StatusCard") # CSS 적용됨
        self.card.setStyleSheet("""
            #StatusCard {
                background-color: #18181B; 
                border: 1px solid #3F3F46; 
                border-radius: 12px;
            }
        """)
        self.card.setFixedSize(320, 120)
        
        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignCenter)
        
        self.title_lbl = QLabel("Processing...", objectName="StatusTitle")
        self.title_lbl.setStyleSheet("color: #FAFAFA; font-size: 16px; font-weight: 700;")
        
        self.msg_lbl = QLabel("Initializing...", objectName="StatusText")
        self.msg_lbl.setStyleSheet("color: #A1A1AA; font-size: 13px; margin-top: 5px;")
        
        layout.addWidget(self.title_lbl, alignment=Qt.AlignCenter)
        layout.addWidget(self.msg_lbl, alignment=Qt.AlignCenter)

    def update_status(self, step, text):
        self.show()
        self.raise_() # 맨 앞으로 가져오기
        self.msg_lbl.setText(text)
        QApplication.processEvents() # UI 즉시 갱신

    def resizeEvent(self, event):
        # 화면 크기가 바뀔 때 오버레이도 꽉 차게, 카드는 중앙에
        self.resize(self.parent().size())
        self.card.move(
            (self.width() - self.card.width()) // 2,
            (self.height() - self.card.height()) // 2
        )
        super().resizeEvent(event)

class DraggableFieldList(QListWidget):
    def __init__(self, items_dict=None):
        super().__init__()
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDefaultDropAction(Qt.CopyAction)
        
        # 스타일: 차원(Dimension)과 지표(Metric) 구분을 위해 칩 스타일 적용
        self.setStyleSheet("""
            QListWidget { background: transparent; border: none; outline: none; }
            QListWidget::item { 
                background: #27272A; color: #E4E4E7; 
                border: 1px solid #3F3F46; border-radius: 4px;
                padding: 6px 12px; margin: 2px 0px; font-weight: 500;
            }
            QListWidget::item:hover { background: #3F3F46; border-color: #52525B; }
            QListWidget::item:selected { background: #4F46E5; border-color: #4338CA; color: white; }
        """)
        
        if items_dict:
            self.load_items(items_dict)

    def load_items(self, data_dict):
        self.clear()
        for key, info in data_dict.items():
            # 라벨 텍스트 생성
            label_text = info['label']
            
            item = QListWidgetItem(label_text)
            # [중요] 나중에 쿼리 만들 때 쓸 식별자(Key)와 메타데이터 저장
            item.setData(Qt.UserRole, key) 
            item.setData(Qt.UserRole + 1, info) # 전체 정보 저장
            self.addItem(item)

    def startDrag(self, supportedActions):
        super().startDrag(Qt.CopyAction) # 원본 유지

class PivotDropZone(QListWidget):
    # 아이템이 드롭되거나 변경되었을 때 부모에게 알리는 신호
    itemsChanged = Signal() 

    def __init__(self, zone_type="dim"):
        super().__init__()
        self.zone_type = zone_type # "dim" (행/열) 또는 "metric" (값)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        
        # 스타일 설정
        border_color = "#4F46E5" if zone_type == "metric" else "#27272A"
        self.setStyleSheet(f"""
            QListWidget {{ 
                background: #18181B; border: 1px dashed {border_color}; border-radius: 6px; 
                outline: none; font-size: 12px; min-height: 40px;
            }}
            QListWidget::item {{ 
                background: #27272A; color: #E4E4E7; 
                border: 1px solid #3F3F46; border-radius: 12px; 
                padding: 4px 10px; margin: 2px 4px; 
            }}
        """)
        
        # [Metric Zone Only] 우클릭 메뉴 활성화
        if self.zone_type == "metric":
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self.show_context_menu)

    def dropEvent(self, event):
        if event.source() == self:
            event.setDropAction(Qt.MoveAction)
        else:
            event.setDropAction(Qt.CopyAction)
        
        super().dropEvent(event)
        
        # [Logic] 드롭된 아이템 처리
        # 방금 들어온 아이템 찾기 (마지막 아이템이라고 가정)
        if self.count() > 0:
            item = self.item(self.count() - 1)
            # 메타데이터 읽기
            meta = item.data(Qt.UserRole + 1)
            
            if self.zone_type == "metric" and meta:
                # Metric인 경우: 기본 집계함수(AVG 등)를 라벨에 붙여줌
                default_agg = meta.get('default', 'SUM')
                base_label = meta['label']
                new_label = f"[{default_agg}] {base_label}"
                
                item.setText(new_label)
                item.setData(Qt.UserRole + 2, default_agg) # 현재 적용된 집계 방식 저장

        self.itemsChanged.emit() # 부모에게 "미리보기 업데이트 해!" 신호 보냄

    def show_context_menu(self, pos):
        # [Metric Zone Only] 우클릭 시 집계 방식 변경 메뉴
        item = self.itemAt(pos)
        if not item: return
        
        meta = item.data(Qt.UserRole + 1) # config 정보
        if not meta or 'options' not in meta: return
        
        menu = QMenu(self)
        menu.setStyleSheet(THEME_CSS) # 기존 테마 적용
        
        current_agg = item.data(Qt.UserRole + 2)
        base_label = meta['label']
        
        for agg in meta['options']:
            action = QAction(agg, self)
            if agg == current_agg:
                action.setCheckable(True)
                action.setChecked(True)
            
            # 람다 캡처 문제 해결을 위해 기본값 인자 사용
            action.triggered.connect(lambda checked, a=agg, i=item, l=base_label: self.change_agg(i, a, l))
            menu.addAction(action)
            
        menu.exec(self.mapToGlobal(pos))

    def change_agg(self, item, agg, label):
        item.setText(f"[{agg}] {label}")
        item.setData(Qt.UserRole + 2, agg) # 집계 방식 업데이트
        self.itemsChanged.emit() # 변경 신호 전송

class PandasModel(QAbstractTableModel):
    """Pandas DataFrame을 QTableView에 연결하기 위한 어댑터"""
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])
            if orientation == Qt.Vertical:
                return str(self._data.index[section])
        return None


# ==========================================
# Page Logic
# ==========================================

class BasePage(QWidget):
    """
    공통적인 페이지 레이아웃을 정의하는 기본 클래스입니다.
    상단 헤더(Title, Subtitle)와 스크롤 가능한 콘텐츠 영역을 포함합니다.
    """
    def __init__(self, title: str, subtitle: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        # 메인 레이아웃 초기화
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(40, 40, 40, 40)
        self.main_layout.setSpacing(20)
        
        # UI 컴포넌트 구성
        self._setup_header(title, subtitle)
        self._setup_scroll_area()

    def _setup_header(self, title: str, subtitle: str) -> None:
        """페이지 상단 헤더 영역을 구성합니다."""
        header_container = QWidget()
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        header_layout.addWidget(QLabel(title, objectName="H1"))
        header_layout.addWidget(QLabel(subtitle, objectName="Label"))
        
        self.main_layout.addWidget(header_container)

    def _setup_scroll_area(self) -> None:
        """스크롤 가능한 콘텐츠 영역을 구성합니다."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")
        
        # 실제 콘텐츠가 담길 컨테이너
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 15, 20)
        self.content_layout.setSpacing(24)
        
        scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(scroll_area)

    def add_section_header(
        self, 
        text: str, 
        button_text: Optional[str] = None, 
        callback: Optional[Callable] = None
    ) -> None:
        """콘텐츠 영역 내에 섹션 헤더(제목 + 선택적 버튼)를 추가합니다."""
        section_container = QWidget()
        section_layout = QHBoxLayout(section_container)
        section_layout.setContentsMargins(0, 10, 0, 10)
        
        section_layout.addWidget(QLabel(text, objectName="H2"))
        section_layout.addStretch()
        
        if button_text:
            btn = QPushButton(button_text, objectName="Primary")
            if callback:
                btn.clicked.connect(callback)
            section_layout.addWidget(btn)
            
        self.content_layout.addWidget(section_container)

    def add_table(self, columns: List[str], rows: List[List[Any]] = []) -> QTableWidget:
        """테이블을 생성하고 데이터를 채운 뒤 콘텐츠 영역에 추가합니다."""
        row_count = len(rows)
        col_count = len(columns)
        
        table = QTableWidget(row_count, col_count)
        self._configure_table_style(table, columns)
        self._populate_table_data(table, rows)
        
        self.content_layout.addWidget(table)
        return table

    def _configure_table_style(self, table: QTableWidget, columns: List[str]) -> None:
        """테이블의 스타일 및 헤더 설정을 처리합니다."""
        table.setHorizontalHeaderLabels(columns)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setMinimumHeight(300)

    def _populate_table_data(self, table: QTableWidget, rows: List[List[Any]]) -> None:
        """테이블에 데이터를 입력합니다. 위젯인 경우 setCellWidget을 사용합니다."""
        for r_idx, row_data in enumerate(rows):
            for c_idx, val in enumerate(row_data):
                if isinstance(val, QWidget):
                    table.setCellWidget(r_idx, c_idx, val)
                else:
                    item = QTableWidgetItem(str(val))
                    # 필요하다면 여기서 텍스트 정렬 등을 추가할 수 있습니다.
                    # item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    table.setItem(r_idx, c_idx, item)

# 1. Dashboard
class DashboardPage(BasePage):
    # 향후 API로 대체될 더미 데이터 정의 (유지보수 용이성)
    FEED_MESSAGES = [
        "User logged in", 
        "DB Backup OK", 
        "Latency Spike > 100ms", 
        "New Order #9921", 
        "API Key Revoked"
    ]
    
    # 차트 배경 스타일 상수화
    CHART_STYLE = (
        "background: qlineargradient(x1:0, y1:1, x2:0, y2:0, "
        "stop:0 #1E1B4B, stop:1 transparent); border-radius:6px;"
    )

    def __init__(self):
        super().__init__("Executive Overview", "Real-time metrics and system health.")
        
        # 1. UI 초기화
        self._setup_ui()
        
        # 2. 데이터 타이머 시작
        self._start_feed_timer()

    def _setup_ui(self):
        """전체 UI 레이아웃을 구성합니다."""
        # 통계 그리드 섹션 추가
        self.content_layout.addLayout(self._create_stats_grid())
        
        # 하단 분할 레이아웃 (차트 + 피드)
        split_layout = QHBoxLayout()
        split_layout.setSpacing(20)
        
        split_layout.addWidget(self._create_chart_section(), 3) # 비율 3
        split_layout.addWidget(self._create_feed_section(), 1)  # 비율 1
        
        self.content_layout.addLayout(split_layout)

    def _create_stats_grid(self) -> QGridLayout:
        """상단 통계 카드 그리드를 생성합니다."""
        grid = QGridLayout()
        grid.setSpacing(20)

        # 향후 API 호출 결과로 대체하기 쉬운 구조
        stats_data = [
            {"title": "Revenue", "value": "$245K", "change": "12%", "is_positive": True},
            {"title": "Users", "value": "14.2K", "change": "3.4%", "is_positive": True},
            {"title": "Latency", "value": "42ms", "change": "-12ms", "is_positive": True},
            {"title": "Errors", "value": "23", "change": "5%", "is_positive": False},
        ]

        for i, data in enumerate(stats_data):
            card = StatCard(
                data["title"], 
                data["value"], 
                data["change"], 
                data["is_positive"]
            )
            grid.addWidget(card, 0, i)
            
        return grid

    def _create_chart_section(self) -> QFrame:
        """트래픽 차트 UI를 생성합니다."""
        chart_box = QFrame(objectName="Card")
        chart_box.setMinimumHeight(400)
        
        layout = QVBoxLayout(chart_box)
        layout.addWidget(QLabel("Traffic Trends", objectName="H2"))
        
        # 시각화 영역 (추후 실제 차트 위젯으로 교체 가능)
        viz_frame = QFrame(styleSheet=self.CHART_STYLE)
        viz_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        layout.addWidget(viz_frame)
        return chart_box

    def _create_feed_section(self) -> QFrame:
        """실시간 피드 UI를 생성합니다."""
        list_box = QFrame(objectName="Card")
        list_box.setMinimumHeight(400)
        
        layout = QVBoxLayout(list_box)
        layout.addWidget(QLabel("Live Feed", objectName="H2"))
        
        self.feed_list = QListWidget(styleSheet="border:none; background:transparent;")
        layout.addWidget(self.feed_list)
        
        return list_box

    def _start_feed_timer(self):
        """데이터 갱신 타이머를 설정합니다."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_feed)
        self.timer.start(3000)

    def update_feed(self):
        """새로운 피드 아이템을 리스트에 추가합니다."""
        # 실제 환경에서는 여기서 API나 소켓 데이터를 받아옵니다.
        current_time = datetime.now().strftime("%H:%M:%S")
        message = random.choice(self.FEED_MESSAGES)
        
        item = QListWidgetItem(f"[{current_time}] {message}")
        item.setForeground(QColor("#A1A1AA"))
        
        self.feed_list.insertItem(0, item)
        
        # 리스트 아이템 개수 제한 (메모리 관리)
        if self.feed_list.count() > 20:
            self.feed_list.takeItem(20)

# 2. Analysis
class AnalysisPage(BasePage):
    # --- [Stylesheets & Constants] ---
    STYLE_SPLITTER = "QSplitter::handle { background-color: #3F3F46; }"
    STYLE_REGION_TREE = "border: 1px solid #27272A; background-color: #18181B; border-radius: 4px;"
    STYLE_TOOLBOX = """
        QToolBox::tab { background: #18181B; border: 1px solid #27272A; border-radius: 4px; color: #A1A1AA; font-weight: 600; }
        QToolBox::tab:selected { background: #27272A; color: #FAFAFA; }
    """
    STYLE_TABS = """
        QTabWidget::pane { border: none; background: transparent; }
        QTabWidget::tab-bar { left: 10px; }
        QTabBar::tab {
            background: transparent; color: #71717A; padding: 12px 16px;
            font-weight: 600; border-bottom: 2px solid transparent; margin-right: 4px;
        }
        QTabBar::tab:hover { color: #E4E4E7; background-color: rgba(255, 255, 255, 0.05); border-radius: 4px; }
        QTabBar::tab:selected { color: #818CF8; border-bottom: 2px solid #6366F1; background: transparent; }
    """
    
    # Action Bar Styles (인라인 스타일을 클래스 상수로 추출)
    STYLE_BTN_PRESET = """
        QPushButton { background: #18181B; border: 1px solid #27272A; color: #A1A1AA; padding: 5px 12px; font-size: 12px; } 
        QPushButton:hover { border-color: #52525B; color: #E4E4E7; }
    """
    STYLE_BTN_RESET = "background: transparent; border: none; color: #71717A; font-weight: 600;"
    STYLE_BTN_EXPORT = """
        QPushButton { background: #27272A; border: 1px solid #3F3F46; color: #E4E4E7; } 
        QPushButton:hover { background: #3F3F46; }
    """

    def __init__(self, toast_cb: Callable) -> None:
        super().__init__("Analysis Studio", "Configure data models and visualize results.")
        self.toast = toast_cb
        
        # UI 요소 상태 저장을 위한 딕셔너리 (데이터 추출 시 유용)
        self.filter_checkboxes: Dict[str, QCheckBox] = {}
        
        self._init_ui()

    def _init_ui(self) -> None:
        """메인 레이아웃 및 스플리터를 초기화하고 좌우 패널을 통합합니다."""
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(1)
        self.main_splitter.setStyleSheet(self.STYLE_SPLITTER)
        self.main_splitter.setMinimumHeight(600)
        
        self.main_splitter.addWidget(self._create_left_panel())
        self.main_splitter.addWidget(self._create_right_panel())
        
        # 패널 비율 설정
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 4)
        
        self.content_layout.addWidget(self.main_splitter)

    # ---------------------------------------------------------
    # Left Panel Components
    # ---------------------------------------------------------
    def _create_left_panel(self) -> QFrame:
        """왼쪽 전역 필터 패널의 뼈대를 구성하고 반환합니다."""
        left_panel = QFrame(objectName="Card")
        layout = QVBoxLayout(left_panel)
        layout.setContentsMargins(10, 15, 10, 15)
        layout.setSpacing(20)
        
        layout.addWidget(QLabel("Global Filters", objectName="H2"))
        layout.addWidget(self._create_date_group())
        layout.addWidget(self._create_region_group())
        layout.addWidget(self._create_filter_toolbox())
        layout.addStretch()
        
        return left_panel

    def _create_date_group(self) -> QGroupBox:
        """분석 기간 설정(Date Group) 위젯을 생성합니다."""
        group_box = QGroupBox("Analysis Period")
        layout = QVBoxLayout(group_box)
        layout.setSpacing(10)
        
        # 1. Date Range Row
        date_layout = QHBoxLayout()
        # self.date_start = QDateEdit(datetime.now(), calendarPopup=True)
        self.date_start = QDateEdit(QDate(2024, 1, 1), calendarPopup=True)
        # self.date_end = QDateEdit(datetime.now(), calendarPopup=True)
        self.date_end = QDateEdit(QDate(2024, 12, 31), calendarPopup=True)
        
        date_layout.addWidget(self.date_start)
        date_layout.addWidget(QLabel("~", alignment=Qt.AlignCenter))
        date_layout.addWidget(self.date_end)
        
        # 2. Day Type Selection Row
        type_layout = QHBoxLayout()
        self.rb_all = QRadioButton("All", checked=True)
        self.rb_week = QRadioButton("Weekday")
        self.rb_holi = QRadioButton("Holiday")
        
        for rb in (self.rb_all, self.rb_week, self.rb_holi):
            type_layout.addWidget(rb)
        
        layout.addLayout(date_layout)
        layout.addLayout(type_layout)
        
        return group_box

    def _create_region_group(self) -> QGroupBox:
        """지역 선택(Region Group) 위젯을 생성합니다."""
        group_box = QGroupBox("Region Selection")
        layout = QVBoxLayout(group_box)
        
        self.region_tree = QTreeView()
        self.region_tree.setHeaderHidden(True)
        self.region_tree.setStyleSheet(self.STYLE_REGION_TREE)
        
        layout.addWidget(self.region_tree)
        return group_box

    def _create_filter_toolbox(self) -> QToolBox:
        """상태 및 예약 방식 필터(Toolbox) 위젯을 생성합니다."""
        self.toolbox = QToolBox()
        self.toolbox.setStyleSheet(self.STYLE_TOOLBOX)
        
        # 필터 구성 데이터 세트 (DRY 원칙 적용)
        filter_configs = {
            "Status Filter": ["Completed", "No Show", "Canceled"],
            "Booking Method": ["App Call", "Phone Call"]
        }
        
        for tab_name, items in filter_configs.items():
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(5, 10, 5, 10)
            
            for item in items:
                cb = QCheckBox(item)
                self.filter_checkboxes[item] = cb  # 상태 추적을 위해 딕셔너리에 저장
                layout.addWidget(cb)
                
            layout.addStretch()
            self.toolbox.addItem(page, tab_name)
            
        return self.toolbox

    # ---------------------------------------------------------
    # Right Panel Components
    # ---------------------------------------------------------
    def _create_right_panel(self) -> QFrame:
        right_panel = QFrame(objectName="Card")
        layout = QVBoxLayout(right_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(self.STYLE_TABS)

        # 동적 속성 할당 대신, 명확하게 캡슐화된 커스텀 위젯 객체를 삽입합니다.
        tab_configs = [
            ("Time Series Analysis", "Time Series"),
            ("Spatial / Stop Analysis", "Spatial Map"),
            ("Statistical Summary", "Statistics")
        ]
        
        for title, label in tab_configs:
            # 커스텀 탭 위젯 인스턴스화
            tab_widget = AnalysisTabWidget() 
            self.tabs.addTab(tab_widget, label)
        
        self.tabs.setCornerWidget(self._create_action_bar(), Qt.TopRightCorner)
        layout.addWidget(self.tabs)
        
        return right_panel

    def _create_action_bar(self) -> QWidget:
        """우측 상단의 버튼 액션 바를 생성하여 반환합니다."""
        action_bar = QWidget()
        layout = QHBoxLayout(action_bar)
        layout.setContentsMargins(0, 5, 10, 5)
        layout.setSpacing(8)
        
        # 버튼 위젯 생성 및 스타일 적용
        btn_preset = QPushButton("Preset: Default ▾")
        btn_preset.setStyleSheet(self.STYLE_BTN_PRESET)
        
        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setStyleSheet("color: #27272A;")
        divider.setFixedHeight(20)
        
        btn_reset = QPushButton("↺ Reset")
        btn_reset.setStyleSheet(self.STYLE_BTN_RESET)
        btn_reset.setCursor(Qt.PointingHandCursor)
        
        btn_run = QPushButton("▶ Run Analysis", objectName="Primary")
        btn_run.setCursor(Qt.PointingHandCursor)
        btn_run.clicked.connect(self.run_simulation)
        
        btn_export = QPushButton("💾 Export")
        btn_export.setStyleSheet(self.STYLE_BTN_EXPORT)

        # 레이아웃에 추가
        layout.addWidget(btn_preset)
        layout.addSpacing(10)
        layout.addWidget(divider)
        layout.addSpacing(5)
        layout.addWidget(btn_reset)
        layout.addWidget(btn_run)
        layout.addWidget(btn_export)
        
        return action_bar

    def _create_analysis_tab_layout(self, title_placeholder) -> QWidget:
        """분석 탭의 메인 레이아웃을 생성하고 핵심 위젯의 참조를 컨테이너에 저장합니다."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 15, 15, 15)
        
        v_splitter = QSplitter(Qt.Vertical)
        v_splitter.setHandleWidth(1)
        v_splitter.setStyleSheet("QSplitter::handle { background-color: #3F3F46; }")
        
        # 1. Top Area (Config) 생성
        top_frame, row_zone, col_zone, val_zone = self._create_tab_config_area()
        
        # 2. Bottom Area (Result) 생성
        bottom_frame, table, canvas, ax = self._create_tab_result_area()
        
        # 스플리터에 조립 및 비율 설정
        v_splitter.addWidget(top_frame)
        v_splitter.addWidget(bottom_frame)
        v_splitter.setStretchFactor(0, 4)
        v_splitter.setStretchFactor(1, 6)
        
        layout.addWidget(v_splitter)

        # [Key Logic] run_simulation()에서 접근할 수 있도록 컨테이너의 속성으로 바인딩
        container.row_zone = row_zone
        container.col_zone = col_zone
        container.val_zone = val_zone
        container.table = table
        container.canvas = canvas
        container.ax = ax

        return container
    
    def run_simulation(self):
        current_tab: AnalysisTabWidget = self.tabs.currentWidget()
        if not current_tab: return

        self.toast("Fetching Data from API...", "success")
        
        try:
            rows, cols, vals = self._extract_pivot_settings(current_tab)
            
            # 1. 날짜 필터 데이터 추출
            start_date = self.date_start.date().toString(Qt.ISODate)
            end_date = self.date_end.date().toString(Qt.ISODate)
            
            # 2. 평일/휴일/All 라디오 버튼 상태 확인 (추가된 부분)
            day_type = "all"
            if self.rb_week.isChecked():
                day_type = "weekday"
            elif self.rb_holi.isChecked():
                day_type = "holiday"

            # 3. 체크박스 상태 확인 및 DB 값 매핑 (기존 유지)
            status_mapping = {"Completed": "이용완료", "No Show": "노쇼", "Canceled": "호출취소"}
            booking_mapping = {"App Call": "앱(실시간)", "Phone Call": "전화(실시간)"}
            
            selected_dispatch_types = [db_val for ui_lbl, db_val in status_mapping.items() if self.filter_checkboxes[ui_lbl].isChecked()]
            selected_booking_methods = [db_val for ui_lbl, db_val in booking_mapping.items() if self.filter_checkboxes[ui_lbl].isChecked()]
            
            # [추가] 라디오 버튼 상태 읽기
            day_type = "All"
            if self.rb_week.isChecked():
                day_type = "Weekday"
            elif self.rb_holi.isChecked():
                day_type = "Holiday"

            # 4. 전송할 Payload 구성
            payload = {
                "start_date": start_date,
                "end_date": end_date,
                "dispatch_types": selected_dispatch_types,
                "booking_methods": selected_booking_methods,
                "day_type": day_type # API로 전달
            }
            
            # 5. API 호출 (이하 동일)
            raw_data = AnalysisDataEngine.fetch_api_data(payload)
            
            if raw_data.empty:
                self.toast("No data received from API.", "error")
                return

            # 3. 인자 4개를 모두 전달하여 호출 (수정 포인트)
            aggregated_data = AnalysisDataEngine.aggregate_data(raw_data, rows, cols, vals)
            
            # 4. 결과 업데이트
            self._update_table_view(current_tab.table, aggregated_data)
            self._update_chart_view(current_tab.canvas, current_tab.ax, aggregated_data, rows, vals)
            
        except Exception as e:
            self.toast("Analysis failed.", "error")
            print(f"[Simulation Error] {traceback.format_exc()}")

    # ---------------------------------------------------------
    # Helper Methods for run_simulation
    # ---------------------------------------------------------
    def _extract_pivot_settings(self, widget) -> tuple[list[str], list[str]]:
        """DropZone의 아이템 텍스트에서 특수문자(이모지 등)를 안전하게 제거하고 필드명만 추출해."""
        def clean_text(text: str) -> str:
            return re.sub(r'^[^\w\s]+\s+', '', text).strip()
            
        rows = [clean_text(widget.row_zone.item(i).text()) for i in range(widget.row_zone.count())]
        cols = [clean_text(widget.col_zone.item(i).text()) for i in range(widget.col_zone.count())] # 열 추출 추가
        vals = [clean_text(widget.val_zone.item(i).text()) for i in range(widget.val_zone.count())]
        
        return rows, cols, vals # cols 포함 리턴
    
    def _update_table_view(self, table_widget, df: pd.DataFrame) -> None:
        """Pandas 데이터를 받아 QTableView를 업데이트해."""
        model = PandasModel(df)
        table_widget.setModel(model)

    def _update_chart_view(self, canvas, ax, df: pd.DataFrame, rows: list[str], vals: list[str]) -> None:
        """집계된 데이터와 사용자 설정(행, 값)을 바탕으로 Matplotlib 차트를 다시 그려."""
        ax.clear()
        ax.set_facecolor('#18181B')
        
        numeric_df = df.select_dtypes(include=np.number)
        if numeric_df.empty:
            ax.text(0.5, 0.5, "No numeric data to display", ha='center', va='center', color='#52525B')
            canvas.draw()
            return
            
        # [수정됨] 사용자가 Values 존에 드롭한 값이 있다면 우선 적용, 없으면 첫 번째 수치형 데이터 사용
        valid_vals = [v for v in vals if v in numeric_df.columns]
        target_col = valid_vals[0] if valid_vals else numeric_df.columns[0]
        
        # X축 결정: 사용자가 Rows 존에 드롭한 기준 컬럼 최우선, 없으면 그냥 첫 번째 컬럼
        valid_rows = [r for r in rows if r in df.columns]
        x_col = valid_rows[0] if valid_rows else (df.columns[0] if len(df.columns) > 0 else None)
        
        # 차트 렌더링 로직
        if x_col and x_col != target_col:
            # 범주형(Categorical) 데이터로 간주하여 Bar 차트 생성
            ax.bar(df[x_col].astype(str), df[target_col], color='#6366F1', alpha=0.7)
            ax.set_title(f"Average {target_col} by {x_col}", color='white', fontsize=10, pad=10)
        else:
            # 단순 선형(Line) 차트 생성
            ax.plot(df[target_col], color='#6366F1', marker='o')
            ax.set_title(f"Trend of {target_col}", color='white', fontsize=10, pad=10)
            
        # X축 라벨 회전 설정 (겹침 방지)
        ax.tick_params(colors='#A1A1AA', rotation=45)
        
        # 차트 요소들이 캔버스 밖으로 잘리지 않도록 여백 자동 조정
        canvas.figure.tight_layout()
        canvas.draw()

class AnalysisDataEngine:
    """데이터 수집 및 Pandas 기반 집계 로직을 전담하는 헬퍼 클래스입니다."""
    
    @staticmethod
    def fetch_api_data(payload: dict) -> pd.DataFrame:
        url = "http://127.0.0.1:8000/api/history/" # 장고 POST 엔드포인트
        try:
            # POST 방식으로 변경, payload 전송
            response = requests.post(url, json=payload, timeout=10) 
            response.raise_for_status() 
            
            data = response.json()
            return pd.DataFrame(data)
        
        except Exception as e:
            print(f"[API Error] {e}")
            return pd.DataFrame()

    @staticmethod
    def aggregate_data(df: pd.DataFrame, rows: list[str], cols: list[str], vals: list[str]) -> pd.DataFrame:
        if df.empty:
            return df
            
        # UI에서 드래그한 값 중 실제 df에 존재하는 컬럼만 필터링
        valid_rows = [c for c in rows if c in df.columns]
        valid_cols = [c for c in cols if c in df.columns]
        valid_vals = [c for c in vals if c in df.columns]

        # 행이나 값이 설정되지 않았다면 원본 반환
        if not valid_rows or not valid_vals:
            return df

        try:
            # [핵심] Pandas Pivot Table 활용
            # UI에서 "이용인원"을 Values에 드롭하면 여기서 aggfunc='sum'으로 합산됨
            pivoted = pd.pivot_table(
                df, 
                values=valid_vals, 
                index=valid_rows, 
                columns=valid_cols if valid_cols else None, 
                aggfunc='sum', # 필요시 np.sum 등으로 처리, 향후 UI에서 agg 선택기능과 연동 가능
                fill_value=0
            )
            
            # 피벗된 MultiIndex 컬럼을 평탄화 (테이블 뷰어에서 보기 좋게 만듦)
            if valid_cols:
                pivoted.columns = ['_'.join(map(str, col)).strip() for col in pivoted.columns.values]
                
            return pivoted.reset_index().round(1)
            
        except Exception as e:
            print(f"[Pivot Error] {e}")
            return df

class AnalysisTabWidget(QWidget):
    """개별 분석 탭의 UI 레이아웃과 위젯 상태를 캡슐화하는 클래스입니다."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_zone = None
        self.col_zone = None
        self.val_zone = None
        self.table = None
        self.canvas = None
        self.ax = None
        
        self._init_layout()

    def _init_layout(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        v_splitter = QSplitter(Qt.Vertical)
        v_splitter.setHandleWidth(1)
        v_splitter.setStyleSheet("QSplitter::handle { background-color: #3F3F46; }")
        
        # UI 생성 메서드 호출 (AnalysisPage에 있던 _create_tab_config_area 등의 로직을 이 클래스로 이동)
        top_frame, self.row_zone, self.col_zone, self.val_zone = self._create_tab_config_area()
        bottom_frame, self.table, self.canvas, self.ax = self._create_tab_result_area()
        
        v_splitter.addWidget(top_frame)
        v_splitter.addWidget(bottom_frame)
        v_splitter.setStretchFactor(0, 4)
        v_splitter.setStretchFactor(1, 6)
        
        layout.addWidget(v_splitter)

    def _create_tab_config_area(self) -> tuple:
        """탭 상단의 설정 영역(필드 목록 및 피벗 드롭 존)을 생성합니다."""
        top_frame = QFrame()
        top_frame.setStyleSheet("background-color: #121215; border-radius: 6px;")
        
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(15, 15, 15, 15)
        top_layout.setSpacing(20)

        # Left: Fields Widget
        fields_widget = self._create_fields_widget()
        
        # Right: Pivot Drop Targets
        target_container, row_zone, col_zone, val_zone = self._create_pivot_drop_zones()
        
        top_layout.addWidget(fields_widget)
        top_layout.addWidget(target_container)

        return top_frame, row_zone, col_zone, val_zone
    
    def _create_pivot_drop_zones(self) -> tuple:
        """피벗 테이블 구성을 위한 드롭 존(행, 열, 값) UI를 생성합니다."""
        target_container = QWidget()
        target_layout = QVBoxLayout(target_container)
        
        row_zone = PivotDropZone("Rows")
        col_zone = PivotDropZone("Columns")
        val_zone = PivotDropZone("Values")

        def wrap_zone(title: str, icon: str, widget: QWidget) -> QGroupBox:
            group_box = QGroupBox(f"{icon}  {title}")
            group_box.setStyleSheet(
                "QGroupBox { border: 1px solid #27272A; border-radius: 6px; margin-top: 22px; font-weight: 600; color: #A1A1AA; } "
                "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }"
            )
            layout = QVBoxLayout(group_box)
            layout.setContentsMargins(0, 15, 0, 0)
            layout.addWidget(widget)
            return group_box

        dims_layout = QHBoxLayout()
        dims_layout.addWidget(wrap_zone("Rows", "☰", row_zone))
        dims_layout.addWidget(wrap_zone("Columns", "|||", col_zone))
        
        target_layout.addLayout(dims_layout, stretch=3)
        target_layout.addWidget(wrap_zone("Values", "Σ", val_zone), stretch=2)
        
        return target_container, row_zone, col_zone, val_zone

    def _create_tab_result_area(self) -> tuple:
        """탭 하단의 결과 영역(데이터 그리드 및 시각화 차트)을 생성합니다."""
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet("background-color: #121215; border-radius: 6px;")
        
        bot_layout = QVBoxLayout(bottom_frame)
        bot_layout.setContentsMargins(0, 0, 0, 0)
        
        h_splitter = QSplitter(Qt.Horizontal)
        h_splitter.setStyleSheet("QSplitter::handle { background-color: #3F3F46; }")
        
        # Grid & Chart 생성
        grid_con, table = self._create_data_grid_widget()
        chart_con, canvas, ax = self._create_chart_widget()
        
        h_splitter.addWidget(grid_con)
        h_splitter.addWidget(chart_con)
        bot_layout.addWidget(h_splitter)
        
        return bottom_frame, table, canvas, ax

    def _create_data_grid_widget(self) -> tuple:
        """결과를 표시할 데이터 테이블 위젯을 생성합니다."""
        grid_con = QWidget()
        layout = QVBoxLayout(grid_con)
        
        layout.addWidget(QLabel("Data Grid", objectName="H2"))
        
        table = QTableView()
        table.setStyleSheet(
            "QTableView { background-color: #18181B; border: 1px solid #27272A; color: #E4E4E7; gridline-color: #3F3F46; } "
            "QHeaderView::section { background-color: #27272A; color: #A1A1AA; border: none; padding: 5px; }"
        )
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)
        
        return grid_con, table

    def _create_chart_widget(self) -> tuple:
        """결과를 표시할 Matplotlib 캔버스 위젯을 생성합니다."""
        chart_con = QWidget()
        layout = QVBoxLayout(chart_con)
        
        layout.addWidget(QLabel("Visualization", objectName="H2"))
        
        fig = Figure(figsize=(5, 4), dpi=100)
        fig.patch.set_facecolor('#18181B')
        
        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background-color: #18181B; border-radius: 4px;")
        
        ax = fig.add_subplot(111)
        ax.set_facecolor('#18181B')
        ax.spines['bottom'].set_color('#52525B')
        ax.spines['left'].set_color('#52525B')
        ax.spines['top'].set_visible(False)   # 상단/우측 테두리 제거로 시각적 깔끔함 증대
        ax.spines['right'].set_visible(False)
        ax.tick_params(colors='#A1A1AA')
        ax.text(0.5, 0.5, "Ready to Run", ha='center', va='center', color='#52525B')
        
        layout.addWidget(canvas)
        
        return chart_con, canvas, ax

    def _create_fields_widget(self) -> QWidget:
        """사용 가능한 데이터 필드 목록 UI를 생성합니다."""
        fields_widget = QWidget()
        fields_widget.setFixedWidth(220)
        
        fields_layout = QVBoxLayout(fields_widget)
        fields_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_title = QLabel("Available Fields")
        lbl_title.setStyleSheet("font-weight: 700; color: #E4E4E7;")
        
        search_input = QLineEdit()
        search_input.setPlaceholderText("Search...")
        search_input.setStyleSheet("background: #18181B; border: 1px solid #27272A; padding: 6px; border-radius: 4px;")
        
        field_list = DraggableFieldList()
        fields_data = [
            ("📅", "날짜"), ("🕒", "시간"), ("T", "배차분류"), 
            ("👥", "이용인원"), ("#", "운행거리"), ("#", "요금"), ("T", "User Type")
        ]
        for icon, name in fields_data: 
            field_list.addItem(QListWidgetItem(f"{icon}  {name}"))
            
        fields_layout.addWidget(lbl_title)
        fields_layout.addWidget(search_input)
        fields_layout.addWidget(field_list)
        
        return fields_widget

    # TODO: AnalysisPage에 있던 _create_tab_config_area, _create_pivot_drop_zones, 
    # _create_tab_result_area, _create_data_grid_widget, _create_chart_widget 메서드들을 
    # 이 클래스 내부로 옮깁니다. 생성 중 self.row_zone 등에 위젯 인스턴스를 안전하게 할당합니다.

# 3. Data Source
class DataSourcePage(BasePage):
    def __init__(self, toast_cb):
        super().__init__("Data Sources", "Manage database connections.")
        self.toast = toast_cb
        self.add_section_header("Active Connections", "+ New Connection", self.new_conn)
        
        rows = [
            ["Production DB", "PostgreSQL", "10.0.0.5", StatusBadge("Active", "active"), "Today"],
            ["Replica A", "MySQL", "10.0.0.8", StatusBadge("Syncing", "warning"), "Today"],
            ["Legacy", "Oracle", "192.168.1.10", StatusBadge("Offline", "error"), "Yesterday"],
        ]
        self.table = self.add_table(["Name", "Type", "Host", "Status", "Last Sync"], rows)

    def new_conn(self):
        dlg = FormDialog("New Connection", [("Name", "text"), ("Type", "combo"), ("Host", "text"), ("Port", "text")])
        if dlg.exec():
            self.toast("Connection Added", "success")

# 4. Wrangling
class WranglingPage(BasePage):
    def __init__(self):
        super().__init__("Data Wrangling", "Clean and prepare raw datasets.")
        
        tb = QFrame(objectName="Card")
        tbl = QHBoxLayout(tb)
        tbl.addWidget(QLabel("Dataset:")); tbl.addWidget(QComboBox())
        tbl.addStretch()
        tbl.addWidget(QPushButton("Deduplicate"))
        tbl.addWidget(QPushButton("Impute Nulls"))
        tbl.addWidget(QPushButton("Export CSV", objectName="Primary"))
        self.content_layout.addWidget(tb)
        
        self.content_layout.addWidget(QLabel("Preview (Top 100 rows)", objectName="H2"))
        data = [
            ["101", "Alpha Corp", "Active", "2025-01-01", "$500"],
            ["102", "Beta LLC", "Pending", "2025-01-02", "NULL"],
            ["103", "Gamma Inc", "Closed", "2025-01-03", "$0"],
        ]
        self.add_table(["ID", "Client", "Status", "Date", "Value"], data)

# 5. SQL Console
class SQLPage(BasePage):
    def __init__(self, toast_cb):
        super().__init__("SQL Console", "Execute raw queries.")
        self.toast = toast_cb
        
        splitter = QSplitter(Qt.Vertical)
        
        ed_frame = QFrame(objectName="Card")
        el = QVBoxLayout(ed_frame)
        self.ed = QTextEdit()
        self.ed.setPlaceholderText("SELECT * FROM production.users LIMIT 100;")
        self.ed.setStyleSheet("font-family: Consolas; color: #818CF8; border:none; background:transparent;")
        
        btns = QHBoxLayout(); btns.addStretch()
        run = QPushButton("Run Query", objectName="Primary")
        run.clicked.connect(self.run_query)
        btns.addWidget(run)
        el.addWidget(self.ed); el.addLayout(btns)
        
        res_frame = QFrame(objectName="Card")
        rl = QVBoxLayout(res_frame)
        rl.addWidget(QLabel("Results", objectName="H2"))
        self.res_table = QTableWidget(0, 3)
        self.res_table.setHorizontalHeaderLabels(["ID", "Name", "Status"])
        self.res_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rl.addWidget(self.res_table)
        
        splitter.addWidget(ed_frame); splitter.addWidget(res_frame)
        self.content_layout.addWidget(splitter)
        
    def run_query(self):
        self.toast("Query Executed (14ms)", "success")
        self.res_table.setRowCount(3)
        for i in range(3):
            self.res_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
            self.res_table.setItem(i, 1, QTableWidgetItem(f"User {i+1}"))
            self.res_table.setItem(i, 2, QTableWidgetItem("Active"))

# 6. Reports
class ReportPage(BasePage):
    def __init__(self):
        super().__init__("Report Builder", "Design PDFs.")
        layout = QHBoxLayout()
        
        tools = QFrame(objectName="Card"); tools.setFixedWidth(200)
        tl = QVBoxLayout(tools)
        tl.addWidget(QLabel("Widgets", objectName="Section"))
        for t in ["Header", "Text", "Chart", "Table", "Image"]:
            btn = QPushButton(t); tl.addWidget(btn)
        tl.addStretch()
        
        canvas = QFrame(objectName="Card")
        cl = QVBoxLayout(canvas)
        cl.addWidget(QLabel("A4 Canvas - Drag Widgets Here", alignment=Qt.AlignCenter, styleSheet="color:#52525B; border: 2px dashed #27272A; border-radius:8px;"))
        
        layout.addWidget(tools); layout.addWidget(canvas)
        self.content_layout.addLayout(layout)

# 7. Scheduler
class SchedulerPage(BasePage):
    def __init__(self, toast_cb):
        super().__init__("Scheduler", "Automated jobs.")
        self.toast = toast_cb
        self.add_section_header("Jobs", "+ New Job", self.new_job)
        
        rows = [
            ["Daily Revenue", "0 9 * * *", "Tomorrow 09:00", StatusBadge("Active", "active")],
            ["DB Sync", "*/30 * * * *", "10:30", StatusBadge("Active", "active")],
            ["Cleanup", "0 0 1 * *", "Dec 1", StatusBadge("Paused", "inactive")],
        ]
        self.add_table(["Job Name", "Cron", "Next Run", "Status"], rows)

    def new_job(self):
        if FormDialog("Create Job", [("Name", "text"), ("Cron Expression", "text"), ("Type", "combo")]).exec():
            self.toast("Job Scheduled", "success")

# 8. Alerts
class AlertPage(BasePage):
    def __init__(self):
        super().__init__("Alert Rules", "Notification triggers.")
        
        # New Rule Form
        f = QFrame(objectName="Card")
        fl = QHBoxLayout(f)
        fl.addWidget(QLabel("Metric:")); fl.addWidget(QComboBox())
        fl.addWidget(QLabel("Threshold:")); fl.addWidget(QLineEdit())
        fl.addWidget(QPushButton("Add Rule", objectName="Primary"))
        self.content_layout.addWidget(f)
        
        self.add_section_header("Active Rules")
        rows = [
            ["High CPU", "CPU > 90%", "Email", StatusBadge("Enabled", "active")],
            ["Disk Space", "Free < 10GB", "Slack", StatusBadge("Enabled", "active")],
        ]
        self.add_table(["Name", "Condition", "Channel", "State"], rows)

# 9. Audit
class AuditPage(BasePage):
    def __init__(self):
        super().__init__("Audit Logs", "Security trail.")
        
        fb = QHBoxLayout()
        fb.addWidget(QLineEdit(placeholderText="Search user or IP..."))
        fb.addWidget(QDateEdit())
        fb.addWidget(QPushButton("Export"))
        self.content_layout.addLayout(fb)
        
        rows = [
            ["10:00:01", "admin", "LOGIN", "Success", "192.168.1.50"],
            ["10:05:23", "analyst", "QUERY", "Select *", "192.168.1.12"],
        ]
        self.add_table(["Time", "User", "Action", "Details", "IP"], rows)

# 10. Users
class UserAdminPage(BasePage):
    def __init__(self, toast_cb):
        super().__init__("User Management", "Roles & Permissions.")
        self.toast = toast_cb
        self.add_section_header("Team", "Invite User", self.invite)
        
        rows = [
            ["John Doe", "john@co.com", StatusBadge("Admin", "active"), "Today"],
            ["Jane Smith", "jane@co.com", StatusBadge("Editor", "warning"), "Yesterday"],
        ]
        self.add_table(["Name", "Email", "Role", "Last Login"], rows)
        
    def invite(self):
        if FormDialog("Invite User", [("Email", "text"), ("Role", "combo")]).exec():
            self.toast("Invitation Sent", "success")

# 11. Settings
class SettingsPage(BasePage):
    def __init__(self):
        super().__init__("Settings", "System configuration.")
        
        card = QFrame(objectName="Card")
        l = QVBoxLayout(card)
        
        # Tabs inside Settings
        tabs = QTabWidget()
        
        # General Tab
        gen = QWidget(); gl = QFormLayout(gen); gl.setSpacing(20)
        gl.addRow("Theme", QComboBox())
        gl.addRow("Language", QComboBox())
        gl.addRow("Timezone", QComboBox())
        tabs.addTab(gen, "General")
        
        # Security Tab
        sec = QWidget(); sl = QFormLayout(sec); sl.setSpacing(20)
        sl.addRow("MFA Enforcement", QCheckBox("Require for all admins"))
        sl.addRow("Session Timeout (m)", QSpinBox())
        tabs.addTab(sec, "Security")
        
        l.addWidget(tabs)
        
        # Footer
        btns = QHBoxLayout(); btns.addStretch()
        btns.addWidget(QPushButton("Save Changes", objectName="Primary"))
        l.addLayout(btns)
        
        self.content_layout.addWidget(card)

# ==========================================
# Main & Login
# ==========================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pro Analytics Suite v3.0")
        
        # 외부에서 정의된 THEME_CSS 적용
        self.setStyleSheet(THEME_CSS)
        
        # UI 초기화 및 레이아웃 설정
        self._init_ui()
        self._setup_layout()
        self._setup_sidebar()
        self._setup_navigation()
        self._setup_footer()
        
        # 초기 페이지 설정 (Dashboard)
        self.nav_list.setCurrentRow(1)

    def _init_ui(self):
        """기본 위젯 및 스택 위젯 초기화"""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.stack = QStackedWidget()
        self.toast = Toast(self.central_widget, "")
        
        # 네비게이션 리스트 위젯
        self.nav_list = QListWidget(objectName="Nav")
        self.nav_list.setFocusPolicy(Qt.NoFocus)
        self.nav_list.itemClicked.connect(self._on_nav_item_clicked)

    def _setup_layout(self):
        """메인 레이아웃 설정"""
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

    def _setup_sidebar(self):
        """사이드바 프레임 및 헤더 설정"""
        self.sidebar = QFrame(objectName="Sidebar")
        self.sidebar.setFixedWidth(260)
        
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(15, 25, 15, 20)
        
        # App Title
        app_title = QLabel("🔷  PRO SUITE")
        app_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #FAFAFA; padding-left:5px;")
        
        self.sidebar_layout.addWidget(app_title)
        self.sidebar_layout.addSpacing(20)
        self.sidebar_layout.addWidget(self.nav_list)
        
        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.stack)

    def _get_menu_config(self):
        """메뉴 구조 데이터 정의 (설정 분리)"""
        return [
            ("WORKSPACE", [
                ("🏠", "Dashboard", DashboardPage()),
                ("⚡", "Analysis", AnalysisPage(self.show_toast)),
                ("💻", "SQL Console", SQLPage(self.show_toast)),
                ("📄", "Reports", ReportPage()),
            ]),
            ("DATA OPS", [
                ("🔌", "Data Sources", DataSourcePage(self.show_toast)),
                ("🧬", "Wrangling", WranglingPage()),
                ("📅", "Scheduler", SchedulerPage(self.show_toast)),
            ]),
            ("ADMIN", [
                ("🔔", "Alerts", AlertPage()),
                ("🛡️", "Audit Logs", AuditPage()),
                ("👥", "Users", UserAdminPage(self.show_toast)),
                ("⚙️", "Settings", SettingsPage()),
            ])
        ]
        
    def _setup_navigation(self):
        """메뉴 아이템 생성 및 스택 추가"""
        menu_data = self._get_menu_config()
        
        for section_name, items in menu_data:
            # 섹션 헤더 추가
            header_item = QListWidgetItem(section_name)
            header_item.setFlags(Qt.NoItemFlags) # 클릭 불가 설정
            header_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            header_item.setForeground(QColor("#52525B"))
            self.nav_list.addItem(header_item)
            
            # 하위 메뉴 아이템 추가
            for icon, name, page_widget in items:
                item_text = f"  {icon}   {name}"
                nav_item = QListWidgetItem(item_text)
                
                self.nav_list.addItem(nav_item)
                self.stack.addWidget(page_widget)
                
                # 스택 인덱스를 아이템 데이터에 저장 (헤더 때문에 인덱스가 밀리는 것 방지)
                page_index = self.stack.count() - 1
                nav_item.setData(Qt.UserRole, page_index)
        
    def _setup_footer(self):
        """사이드바 하단 사용자 정보 영역 설정"""
        user_frame = QFrame()
        user_frame.setStyleSheet("background: #18181B; border-radius: 6px; padding: 8px;")
        
        user_layout = QHBoxLayout(user_frame)
        user_layout.setContentsMargins(5, 5, 5, 5)
        
        profile_icon = QLabel("👤")
        user_info = QLabel("<b>Admin</b><br><span style='color:#71717A; font-size:11px'>Pro Plan</span>")
        
        user_layout.addWidget(profile_icon)
        user_layout.addWidget(user_info)
        
        self.sidebar_layout.addWidget(user_frame)
        
    def _on_nav_item_clicked(self, item):
        """네비게이션 클릭 이벤트 핸들러"""
        page_index = item.data(Qt.UserRole)
        if page_index is not None:
            self.stack.setCurrentIndex(page_index)

    def show_toast(self, msg, type="success"):
        """토스트 메시지 표시"""
        if self.toast:
            self.toast.deleteLater()
        
        self.toast = Toast(self.centralWidget(), msg, type)
        self.toast.show_msg()
class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self._init_window_settings()
        self._init_ui()

    def _init_window_settings(self):
        """1. 윈도우 기본 설정"""
        self.setFixedSize(400, 500)
        self.setStyleSheet(THEME_CSS)
        self.setWindowFlags(Qt.FramelessWindowHint)

    def _init_ui(self):
        """2. 전체 UI 레이아웃 구성"""
        # 메인 레이아웃 생성
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(50, 50, 50, 50)
        self.main_layout.setSpacing(20)

        # 각 섹션별로 함수 호출 (순서대로 배치됨)
        self._add_header_section()
        self._add_input_section()
        self._add_action_section()
        self._add_footer_section()

    def _add_header_section(self):
        """3. 헤더 영역 추가"""
        title_label = QLabel("PRO PRISM⚡️")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: 800;")
        
        self.main_layout.addWidget(title_label)
        self.main_layout.addStretch() # 위쪽 여백

    def _add_input_section(self):
        """4. 입력 필드 영역 추가"""
        input_label = QLabel("Sign In")
        
        # 인스턴스 변수로 저장 (나중에 데이터 접근 필요하므로 self 붙임)
        self.email_input = QLineEdit(placeholderText="Email")
        self.password_input = QLineEdit(placeholderText="Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        
        self.main_layout.addWidget(input_label)
        self.main_layout.addWidget(self.email_input)
        self.main_layout.addWidget(self.password_input)

    def _add_action_section(self):
        """5. 버튼 영역 추가"""
        login_btn = QPushButton("Login")
        login_btn.setObjectName("Primary")
        login_btn.setFixedHeight(45)
        login_btn.clicked.connect(self.accept)
        
        self.main_layout.addWidget(login_btn)
        self.main_layout.addStretch() # 아래쪽 여백

    def _add_footer_section(self):
        """6. 푸터 영역 추가"""
        version_label = QLabel("v3.0 Enterprise")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #52525B;")
        
        self.main_layout.addWidget(version_label)

if __name__ == "__main__":
    # 1. 정책을 먼저 설정 (QApplication 클래스에서 직접 호출)
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    # 2. 앱 인스턴스 생성
    app = QApplication(sys.argv)
    
    if LoginWindow().exec() == QDialog.Accepted:
        win = MainWindow()
        win.showMaximized()
        sys.exit(app.exec())