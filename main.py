"""Growvia Cheque Writer — Sri Lankan bank cheque printing application."""

import ctypes
import json
import os
import subprocess
import sys
import tempfile
import time
import webbrowser
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QFrame,
    QDateEdit, QDoubleSpinBox, QSizePolicy, QMessageBox,
    QCompleter, QRadioButton, QButtonGroup, QDialog,
)
from PyQt6.QtCore import (
    Qt, QDate, QRectF, QSizeF, QMarginsF, QStringListModel, QSettings, QObject, QEvent,
    pyqtSignal, QTimer,
)
from PyQt6.QtGui import (
    QPainter, QFont, QFontMetrics, QPen, QColor, QPageLayout, QPageSize, QPalette, QBrush, QIcon,
)
from PyQt6.QtPrintSupport import QPrinter, QPrinterInfo

from amount_words import amount_to_words
from payee_db import save_payee, search_payees, all_payees

if getattr(sys, "frozen", False):
    exe_dir_banks = Path(sys.executable).parent / "banks"
    if exe_dir_banks.exists() and any(exe_dir_banks.glob("*.json")):
        BANKS_DIR = exe_dir_banks
    else:
        BANKS_DIR = Path(__file__).parent / "banks"
else:
    BANKS_DIR = Path(__file__).parent / "banks"

MM_TO_PX = 96 / 25.4

# Paper & Feed Modes
PAPER_MODE_A4_CENTER = "A4 - Center Feed (Standard)"
PAPER_MODE_A4_LEFT = "A4 - Left-Aligned Feed"
PAPER_MODE_EXACT = "Custom Cheque Size (178 x 89 mm)"
PAPER_MODES = [
    PAPER_MODE_A4_CENTER,
    PAPER_MODE_A4_LEFT,
    PAPER_MODE_EXACT,
]

CROSS_MODES = [
    "Cross Only",
    "Cross A/C Payee + Or Bearer",
    "Cross A/C Payee + Not Negotiable + Or Bearer",
    "Cross A/C Payee",
    "No Crossing",
]


def mm(value: float) -> float:
    return value * MM_TO_PX


def resource_path(name: str) -> Path:
    """Locate a bundled file whether running frozen (PyInstaller) or from source."""
    if getattr(sys, "frozen", False):
        for base in (getattr(sys, "_MEIPASS", None), Path(sys.executable).parent):
            if base:
                cand = Path(base) / name
                if cand.exists():
                    return cand
        return Path(getattr(sys, "_MEIPASS", ".")) / name
    return Path(__file__).parent / name


def load_banks() -> dict:
    banks = {}
    for f in sorted(BANKS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            banks[data["short"]] = data
        except Exception:
            pass
    return banks


def star(text: str) -> str:
    """Wrap text with ** security markers as seen on Sri Lankan cheques."""
    return f"**{text}**"


class ChequeRenderer:
    FONT = "Times New Roman"

    def __init__(self, bank_config: dict, payee: str, amount: float,
                 cheque_date: str, cross_mode: str,
                 x_offset_mm: float = 0.0, y_offset_mm: float = 0.0,
                 paper_mode: str = PAPER_MODE_A4_CENTER,
                 draw_guidelines: bool = False,
                 year_digits: int = 2,
                 date_x_offset_mm: float = 0.0,
                 date_y_offset_mm: float = 0.0):
        self.cfg = bank_config
        self.payee = payee
        self.amount = amount
        self.cheque_date = cheque_date
        self.cross_mode = cross_mode
        self.x_offset_mm = x_offset_mm
        self.y_offset_mm = y_offset_mm
        self.paper_mode = paper_mode
        self.draw_guidelines = draw_guidelines
        self.year_digits = year_digits
        self.date_x_offset_mm = date_x_offset_mm
        self.date_y_offset_mm = date_y_offset_mm

        cheque_w = self.cfg.get("cheque_width_mm", 177.8)
        if self.paper_mode == PAPER_MODE_A4_CENTER:
            # Center on 210mm A4 sheet: (210 - 177.8) / 2 = 16.1 mm
            self.base_x_mm = (210.0 - cheque_w) / 2.0
            self.base_y_mm = 0.0
        elif self.paper_mode == PAPER_MODE_A4_LEFT:
            self.base_x_mm = 0.0
            self.base_y_mm = 0.0
        else:
            self.base_x_mm = 0.0
            self.base_y_mm = 0.0

    @property
    def eff_x(self) -> float:
        return self.base_x_mm + self.x_offset_mm

    @property
    def eff_y(self) -> float:
        return self.base_y_mm + self.y_offset_mm

    def _make_font(self, font_size_mm: float, bold: bool = False) -> QFont:
        font = QFont(self.FONT)
        font.setPixelSize(max(1, int(mm(font_size_mm))))
        font.setBold(bold)
        return font

    def _draw_text(self, painter: QPainter, x_mm: float, y_mm: float,
                   text: str, font_size_mm: float, bold: bool = False,
                   align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft,
                   max_width_mm: float = 200):
        font = self._make_font(font_size_mm, bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(0, 0, 0)))
        rect = QRectF(mm(x_mm + self.eff_x), mm(y_mm + self.eff_y) - mm(font_size_mm),
                      mm(max_width_mm), mm(font_size_mm * 1.4))
        painter.drawText(rect, align, text)

    def _wrap_words_to_lines(self, text: str, font_size_mm: float,
                             line_limits_mm: list[float],
                             prefix: str = "**", suffix: str = "**") -> list[str]:
        fm = QFontMetrics(self._make_font(font_size_mm))
        words = text.split()
        if not words:
            return []

        lines: list[str] = []
        curr_words: list[str] = []

        for i, w in enumerate(words):
            line_idx = len(lines)
            is_first = (line_idx == 0 and len(curr_words) == 0)
            is_last = (i == len(words) - 1)

            test_line = (prefix if line_idx == 0 else "") + " ".join(curr_words + [w]) + (suffix if is_last else "")
            test_px = fm.horizontalAdvance(test_line)

            max_limit_mm = line_limits_mm[min(line_idx, len(line_limits_mm) - 1)]
            max_limit_px = int(mm(max_limit_mm))

            if test_px > max_limit_px and curr_words:
                cur_p = prefix if line_idx == 0 else ""
                lines.append(cur_p + " ".join(curr_words))
                curr_words = [w]
            else:
                curr_words.append(w)

        if curr_words:
            line_idx = len(lines)
            cur_p = prefix if line_idx == 0 else ""
            lines.append(cur_p + " ".join(curr_words) + suffix)

        return lines

    def _draw_date_boxes(self, painter: QPainter):
        f = self.cfg["fields"]
        parts = self.cheque_date.replace(" ", "").split("/")
        dd   = parts[0].zfill(2) if len(parts) > 0 else "  "
        mm_s = parts[1].zfill(2) if len(parts) > 1 else "  "
        raw_year = parts[2] if len(parts) > 2 else ""
        digits = self.year_digits
        yy = raw_year[-digits:].zfill(digits)

        fdd   = f["date_dd"]
        fmm   = f["date_mm"]
        fyyyy = f["date_yyyy"]
        spacing = fdd.get("letter_spacing_mm", 5.6)
        fs = fdd.get("font_size", 5.0)

        dx = self.date_x_offset_mm
        dy = self.date_y_offset_mm

        for i, ch in enumerate(dd):
            self._draw_text(painter, fdd["x"] + dx + i * spacing, fdd["y"] + dy, ch, fs,
                            align=Qt.AlignmentFlag.AlignHCenter, max_width_mm=spacing)
        for i, ch in enumerate(mm_s):
            self._draw_text(painter, fmm["x"] + dx + i * spacing, fmm["y"] + dy, ch, fs,
                            align=Qt.AlignmentFlag.AlignHCenter, max_width_mm=spacing)
        shift = 4 - digits
        for i, ch in enumerate(yy):
            self._draw_text(painter, fyyyy["x"] + dx + (i + shift) * spacing, fyyyy["y"] + dy, ch, fs,
                            align=Qt.AlignmentFlag.AlignHCenter, max_width_mm=spacing)

    def render(self, painter: QPainter):
        f = self.cfg["fields"]
        cheque_w = self.cfg.get("cheque_width_mm", 177.8)
        cheque_h = self.cfg.get("cheque_height_mm", 88.9)

        if self.draw_guidelines:
            pen = QPen(QColor(13, 148, 136), mm(0.35), Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(mm(self.eff_x), mm(self.eff_y), mm(cheque_w), mm(cheque_h)))

        # Date digits
        self._draw_date_boxes(painter)

        # Payee
        pf = f["payee"]
        self._draw_text(painter, pf["x"], pf["y"], star(self.payee),
                        pf["font_size"], bold=False,
                        max_width_mm=pf.get("max_width", 130))

        # Amount box
        ab = f["amount_box"]
        align = (Qt.AlignmentFlag.AlignHCenter
                 if ab.get("align") == "center" else Qt.AlignmentFlag.AlignLeft)
        self._draw_text(painter, ab["x"], ab["y"],
                        star(f"{self.amount:,.2f}"),
                        ab["font_size"], bold=False,
                        align=align, max_width_mm=ab.get("max_width", 56))

        # Amount in words
        words = amount_to_words(self.amount)
        aw  = f["amount_words"]
        aw2 = f.get("amount_words_line2", aw)
        aw3 = f.get("amount_words_line3", {
            "x": aw2["x"],
            "y": aw2["y"] + 7.0,
            "font_size": aw2.get("font_size", 5.0),
            "max_width": 120.0
        })

        max_w1 = aw.get("max_width", 80.0)
        max_w2 = aw2.get("max_width", 91.5)
        max_w3 = aw3.get("max_width", 120.0)
        fs_w   = aw.get("font_size", 5.0)

        lines = self._wrap_words_to_lines(words, fs_w, [max_w1, max_w2, max_w3], prefix="**", suffix="**")
        line_cfgs = [aw, aw2, aw3]

        for i, text_line in enumerate(lines[:3]):
            cfg_i = line_cfgs[i]
            max_limit = [max_w1, max_w2, max_w3][i]
            self._draw_text(painter, cfg_i["x"], cfg_i["y"], text_line, fs_w,
                            max_width_mm=max_limit)

        # Crossing
        if self.cross_mode != "No Crossing":
            self._draw_crossing(painter)

    def _draw_crossing(self, painter: QPainter):
        label_map = {
            "Cross A/C Payee + Or Bearer":                  ["A/C PAYEE ONLY"],
            "Cross A/C Payee + Not Negotiable + Or Bearer": ["NOT NEGOTIABLE", "A/C PAYEE ONLY"],
            "Cross A/C Payee":                              ["A/C PAYEE ONLY"],
            "Cross Only":                                   [],
        }
        lines = label_map.get(self.cross_mode, [])

        pen = QPen(QColor(0, 0, 0))
        pen.setWidthF(mm(0.32))
        painter.setPen(pen)

        # Refined, slightly smaller crossing stamp (approx 15-20% more compact)
        x1a, y1a = mm(3.5 + self.eff_x),  mm(16.0 + self.eff_y)
        x1b, y1b = mm(22.0 + self.eff_x), mm(3.5 + self.eff_y)
        painter.drawLine(int(x1a), int(y1a), int(x1b), int(y1b))

        gap_mm = 6.2
        import math
        angle_rad = math.atan2(y1a - y1b, x1b - x1a)
        dx = gap_mm * math.sin(angle_rad)
        dy = gap_mm * math.cos(angle_rad)
        x2a, y2a = x1a + mm(dx), y1a + mm(dy)
        x2b, y2b = x1b + mm(dx), y1b + mm(dy)
        painter.drawLine(int(x2a), int(y2a), int(x2b), int(y2b))

        if not lines:
            return

        mid_x = (x1a + x1b + x2a + x2b) / 4 + mm(2.2)
        mid_y = (y1a + y1b + y2a + y2b) / 4
        angle_deg = math.degrees(math.atan2(y1b - y1a, x1b - x1a))

        painter.save()
        painter.translate(mid_x, mid_y)
        painter.rotate(angle_deg)

        font = self._make_font(2.8)
        painter.setFont(font)
        painter.setPen(QPen(QColor(0, 0, 0)))

        text_spacing = mm(3.6)
        total = text_spacing * (len(lines) - 1)
        half_w = mm(15)
        for i, text in enumerate(lines):
            y_off = -total / 2 + i * text_spacing
            rect = QRectF(-half_w, y_off - mm(2.8), half_w * 2, mm(3.6))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

        painter.restore()


class ChequePreviewWidget(QFrame):
    """Clean interactive preview canvas showing live cheque rendering."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "ChequePreviewWidget { background-color: #F1F5F9; border: 1.5px solid #E2E8F0; border-radius: 6px; }"
        )
        self.renderer: ChequeRenderer | None = None
        self.show_a4_view = False

    def set_renderer(self, renderer: ChequeRenderer, show_a4_view: bool = False):
        self.renderer = renderer
        self.show_a4_view = show_a4_view
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.renderer:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = self.width()
        h = self.height()
        cheque_w_mm = self.renderer.cfg.get("cheque_width_mm", 177.8)
        cheque_h_mm = self.renderer.cfg.get("cheque_height_mm", 88.9)

        if self.show_a4_view:
            # Full A4 Page View (210 x 297 mm)
            margin = 12
            scale = min((w - margin * 2) / mm(210.0), (h - margin * 2) / mm(297.0))
            offset_x = (w - mm(210.0) * scale) / 2.0
            offset_y = (h - mm(297.0) * scale) / 2.0

            painter.save()
            painter.translate(offset_x, offset_y)
            painter.scale(scale, scale)

            # A4 Sheet with shadow
            painter.setPen(QPen(QColor("#94A3B8"), 1))
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.drawRect(QRectF(0, 0, mm(210.0), mm(297.0)))

            # Cheque Leaf area on A4
            eff_x = self.renderer.eff_x
            eff_y = self.renderer.eff_y
            painter.setPen(QPen(QColor("#0D9488"), 1.2, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor("#ECFDF5")))
            painter.drawRect(QRectF(mm(eff_x), mm(eff_y), mm(cheque_w_mm), mm(cheque_h_mm)))

            self.renderer.render(painter)
            painter.restore()
        else:
            # Zoomed Cheque View
            margin = 16
            scale = min((w - margin * 2) / mm(cheque_w_mm), (h - margin * 2) / mm(cheque_h_mm))
            offset_x = (w - mm(cheque_w_mm) * scale) / 2.0
            offset_y = (h - mm(cheque_h_mm) * scale) / 2.0

            painter.save()
            painter.translate(offset_x, offset_y)
            painter.scale(scale, scale)

            # Cheque background
            painter.setPen(QPen(QColor("#0D9488"), 1.5))
            painter.setBrush(QBrush(QColor("#F8FAF9")))
            painter.drawRoundedRect(QRectF(0, 0, mm(cheque_w_mm), mm(cheque_h_mm)), 4, 4)

            # Inner dotted border
            painter.setPen(QPen(QColor("#A7F3D0"), 1, Qt.PenStyle.DotLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(mm(2), mm(2), mm(cheque_w_mm - 4), mm(cheque_h_mm - 4)))

            # Bank Watermark Title
            bank_name = self.renderer.cfg.get("name", "BANK CHEQUE").upper()
            painter.setFont(QFont("Times New Roman", int(mm(3.8)), QFont.Weight.Bold))
            painter.setPen(QColor("#115E59"))
            painter.drawText(QRectF(mm(18), mm(8), mm(100), mm(8)), Qt.AlignmentFlag.AlignLeft, bank_name)

            orig_bx = self.renderer.base_x_mm
            orig_by = self.renderer.base_y_mm
            orig_ox = self.renderer.x_offset_mm
            orig_oy = self.renderer.y_offset_mm
            self.renderer.base_x_mm = 0.0
            self.renderer.base_y_mm = 0.0
            self.renderer.x_offset_mm = 0.0
            self.renderer.y_offset_mm = 0.0

            self.renderer.render(painter)

            self.renderer.base_x_mm = orig_bx
            self.renderer.base_y_mm = orig_by
            self.renderer.x_offset_mm = orig_ox
            self.renderer.y_offset_mm = orig_oy

            painter.restore()


class PayeeComboBox(QComboBox):
    """Editable QComboBox with persistent SQLite database storage and dropdown history."""

    textChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PayeeCombo")
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setMaxVisibleItems(15)

        # Style inner lineEdit
        if self.lineEdit():
            self.lineEdit().setStyleSheet(
                "QLineEdit {"
                "  font-size: 14px; font-weight: 600; color: #0F172A;"
                "  background: transparent; border: none; padding: 2px 4px;"
                "}"
            )
            self.lineEdit().editingFinished.connect(self._on_finished_editing)
            self.lineEdit().returnPressed.connect(self._on_finished_editing)

        # Dropdown popup styling
        view = self.view()
        if view:
            view.setStyleSheet(
                "QListView { font-size: 13px; font-weight: 500; padding: 4px; color: #0F172A; background: #FFFFFF; outline: none; }"
                "QListView::item { padding: 6px 10px; min-height: 24px; border-radius: 4px; }"
                "QListView::item:hover { background: #E0F2FE; color: #0369A1; }"
                "QListView::item:selected { background: #0284C7; color: #FFFFFF; }"
            )

        # Autocompletion
        comp = self.completer()
        if comp:
            comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            comp.setFilterMode(Qt.MatchFlag.MatchContains)
            comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            popup = comp.popup()
            if popup:
                popup.setStyleSheet(
                    "QListView { font-size: 13px; font-weight: 500; padding: 4px; color: #0F172A; background: #FFFFFF; outline: none; }"
                    "QListView::item { padding: 6px 10px; min-height: 24px; border-radius: 4px; }"
                    "QListView::item:hover { background: #E0F2FE; color: #0369A1; }"
                    "QListView::item:selected { background: #0284C7; color: #FFFFFF; }"
                )

        self.currentTextChanged.connect(self.textChanged.emit)

        # Populate from database
        self.reload_payees()
        self.setEditText("")

    def wheelEvent(self, event):
        event.ignore()

    def setPlaceholderText(self, text: str):
        if self.lineEdit():
            self.lineEdit().setPlaceholderText(text)

    def text(self) -> str:
        return self.currentText().strip()

    def setText(self, text: str):
        self.setEditText(text)

    def reload_payees(self, keep_text: str = ""):
        items = all_payees()
        self.blockSignals(True)
        self.clear()
        if items:
            self.addItems(items)
        if keep_text is not None:
            self.setEditText(keep_text)
        self.blockSignals(False)

    def _on_finished_editing(self):
        val = self.text()
        if val:
            save_payee(val)
            self.reload_payees(keep_text=val)

    def save_current(self):
        self._on_finished_editing()


class NoScrollComboBox(QComboBox):
    """QComboBox that ignores mouse wheel scrolling so values never change accidentally."""
    def wheelEvent(self, event):
        event.ignore()


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that ignores mouse wheel scrolling."""
    def wheelEvent(self, event):
        event.ignore()


class NoScrollDateEdit(QDateEdit):
    """QDateEdit that ignores mouse wheel scrolling."""
    def wheelEvent(self, event):
        event.ignore()


APP_STYLE = """
QMainWindow, QWidget {
    background-color: #F8FAFC;
    color: #1E293B;
    font-family: 'Segoe UI', Arial, sans-serif;
}

QLineEdit, QDateEdit, QDoubleSpinBox, QComboBox {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    selection-background-color: #0284C7;
    selection-color: #FFFFFF;
}
QLineEdit:focus, QDateEdit:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1.5px solid #0284C7;
    background-color: #FFFFFF;
}
QLineEdit:hover, QDateEdit:hover, QDoubleSpinBox:hover, QComboBox:hover {
    border-color: #94A3B8;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    width: 10px;
    height: 10px;
}
QComboBox QAbstractItemView {
    background: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    padding: 4px;
    selection-background-color: #0284C7;
    selection-color: #FFFFFF;
    font-size: 13px;
}

QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    width: 20px;
    background: #F1F5F9;
    border: none;
    border-left: 1px solid #CBD5E1;
}
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
    background: #E2E8F0;
}

QDateEdit::drop-down {
    width: 24px;
    border: none;
    background: #F1F5F9;
    border-left: 1px solid #CBD5E1;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}
"""

PAYEE_STYLE = """
QComboBox#PayeeCombo {
    font-size: 14px;
    font-weight: 600;
    color: #0F172A;
    background-color: #FFFFFF;
    border: 1.5px solid #CBD5E1;
    border-radius: 6px;
    padding: 3px 8px;
}
QComboBox#PayeeCombo:focus, QComboBox#PayeeCombo:hover {
    border-color: #0284C7;
}
QComboBox#PayeeCombo::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid #CBD5E1;
    border-top-right-radius: 5px;
    border-bottom-right-radius: 5px;
    background-color: #F8FAFC;
}
QComboBox#PayeeCombo::drop-down:hover {
    background-color: #E2E8F0;
}
QComboBox#PayeeCombo::down-arrow {
    width: 10px;
    height: 10px;
}
"""


class PasscodeDialog(QDialog):
    """Simple passcode prompt to unlock advanced settings."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings Security")
        self.setFixedSize(310, 150)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)

        lbl = QLabel("Enter passcode to unlock More Options:")
        lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #1E293B;")
        layout.addWidget(lbl)

        self.code_edit = QLineEdit()
        self.code_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.code_edit.setPlaceholderText("Passcode (0000)")
        self.code_edit.setMaxLength(10)
        self.code_edit.setMinimumHeight(32)
        self.code_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.code_edit.setStyleSheet(
            "QLineEdit { font-size: 15px; letter-spacing: 4px; font-weight: 700; border: 1.5px solid #CBD5E1; border-radius: 6px; padding: 4px; }"
            "QLineEdit:focus { border-color: #0284C7; }"
        )
        layout.addWidget(self.code_edit)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(32)
        cancel_btn.setStyleSheet(
            "QPushButton { background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 12px; font-weight: 600; color: #475569; }"
            "QPushButton:hover { background: #E2E8F0; }"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        unlock_btn = QPushButton("Unlock")
        unlock_btn.setMinimumHeight(32)
        unlock_btn.setStyleSheet(
            "QPushButton { background: #0284C7; color: white; border: none; border-radius: 6px; font-size: 12px; font-weight: 700; }"
            "QPushButton:hover { background: #0369A1; }"
        )
        unlock_btn.clicked.connect(self.accept)
        btn_row.addWidget(unlock_btn)

        layout.addLayout(btn_row)

        self.code_edit.returnPressed.connect(self.accept)
        self.code_edit.setFocus()

    def get_passcode(self) -> str:
        return self.code_edit.text()


class MainWindow(QMainWindow):
    def __init__(self, banks: dict):
        super().__init__()
        self.banks = banks
        self.setWindowTitle("Growvia Cheque Writer")
        icon_cand = resource_path("icon.png")
        if not icon_cand.exists():
            icon_cand = resource_path("icon.ico")
        if icon_cand.exists():
            self.setWindowIcon(QIcon(str(icon_cand)))
        self.setMinimumSize(960, 480)

        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#F8FAFC"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#1E293B"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#0F172A"))
        self.setPalette(pal)
        self.setStyleSheet(APP_STYLE)

        self.settings = QSettings("Growvia", "ChequeWriter")

        central = QWidget()
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(14)

        # ══════════════════════════════════════════════════════════════════════
        # LEFT COLUMN: INPUT FORM & ACTIONS
        # ══════════════════════════════════════════════════════════════════════
        left_card = QFrame()
        left_card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; }"
        )
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(9)

        # Section Title
        sec_title = QLabel("CHEQUE DETAILS")
        sec_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; letter-spacing: 0.5px;")
        left_layout.addWidget(sec_title)

        # Row 1: Bank + Date
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self.bank_combo = NoScrollComboBox()
        self.bank_combo.setMinimumHeight(34)
        for short in self.banks:
            self.bank_combo.addItem(self.banks[short]["name"], short)
        saved_bank = self.settings.value("bank", "")
        if saved_bank:
            idx_b = self.bank_combo.findData(saved_bank)
            if idx_b >= 0:
                self.bank_combo.setCurrentIndex(idx_b)
        self.bank_combo.currentIndexChanged.connect(self._on_change)
        row1.addWidget(self.bank_combo, stretch=3)

        self.date_edit = NoScrollDateEdit(QDate.currentDate())
        self.date_edit.setDisplayFormat("dd / MM / yyyy")
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setMinimumHeight(34)
        self.date_edit.dateChanged.connect(self._on_change)
        row1.addWidget(self.date_edit, stretch=2)
        left_layout.addLayout(row1)

        # Row 2: Pay To (Dropdown + Editable with DB persistence)
        self.payee_edit = PayeeComboBox()
        self.payee_edit.setPlaceholderText("Pay To (e.g. MR. SAMPATH PERERA)...")
        self.payee_edit.setStyleSheet(PAYEE_STYLE)
        self.payee_edit.setMinimumHeight(36)
        self.payee_edit.textChanged.connect(self._on_change)
        left_layout.addWidget(self.payee_edit)

        # Row 3: Amount + Crossing
        row3 = QHBoxLayout()
        row3.setSpacing(8)

        self.amount_spin = NoScrollDoubleSpinBox()
        self.amount_spin.setRange(0.01, 99_999_999.99)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSingleStep(100)
        self.amount_spin.setValue(800.00)
        self.amount_spin.setGroupSeparatorShown(True)
        self.amount_spin.setMinimumHeight(34)
        self.amount_spin.setStyleSheet("font-size: 15px; font-weight: 700; color: #0284C7;")
        self.amount_spin.valueChanged.connect(self._on_change)
        row3.addWidget(self.amount_spin, stretch=2)

        self.cross_combo = NoScrollComboBox()
        self.cross_combo.setMinimumHeight(34)
        for m in CROSS_MODES:
            self.cross_combo.addItem(m)
        saved_cross = self.settings.value("cross_mode", "Cross Only")
        idx_c = self.cross_combo.findText(saved_cross)
        if idx_c >= 0:
            self.cross_combo.setCurrentIndex(idx_c)
        else:
            self.cross_combo.setCurrentIndex(0)
        self.cross_combo.currentIndexChanged.connect(self._on_change)
        row3.addWidget(self.cross_combo, stretch=3)
        left_layout.addLayout(row3)

        # Words Label (Auto-updating)
        self.words_label = QLabel()
        self.words_label.setStyleSheet("color: #64748B; font-size: 11px; font-style: italic; padding-left: 2px;")
        self.words_label.setWordWrap(True)
        left_layout.addWidget(self.words_label)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background: #F1F5F9; border: none; max-height: 1px;")
        left_layout.addWidget(div)

        # Row 4: Printer selection
        row4 = QHBoxLayout()
        row4.setSpacing(8)

        print_lbl = QLabel("Printer:")
        print_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B;")
        row4.addWidget(print_lbl)

        self.printer_combo = NoScrollComboBox()
        self.printer_combo.setMinimumHeight(34)
        for info in QPrinterInfo.availablePrinters():
            self.printer_combo.addItem(info.printerName())
        saved_printer = self.settings.value("printer", "")
        idx = self.printer_combo.findText(saved_printer) if saved_printer else -1
        if idx < 0:
            idx = self.printer_combo.findText(QPrinterInfo.defaultPrinterName())
        if idx >= 0:
            self.printer_combo.setCurrentIndex(idx)
        self.printer_combo.currentIndexChanged.connect(
            lambda: self.settings.setValue("printer", self.printer_combo.currentText())
        )
        row4.addWidget(self.printer_combo, stretch=1)
        left_layout.addLayout(row4)

        # More Options Toggle (Collapsible with Passcode Protection)
        self.more_options_btn = QPushButton("🔒 More Options ▾")
        self.more_options_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.more_options_btn.setStyleSheet(
            "QPushButton {"
            "  background: transparent; color: #64748B; font-size: 11px; font-weight: 600;"
            "  border: none; text-align: left; padding: 3px 2px;"
            "}"
            "QPushButton:hover { color: #0284C7; }"
        )
        self.more_options_btn.clicked.connect(self._toggle_more_options)
        left_layout.addWidget(self.more_options_btn)

        # Collapsible Advanced Options Container (Hidden by default, Passcode: 0000)
        self.advanced_container = QWidget()
        adv_layout = QVBoxLayout(self.advanced_container)
        adv_layout.setContentsMargins(0, 0, 0, 4)
        adv_layout.setSpacing(6)

        # Row 5a: Paper Feed Mode (Moved from main form)
        row_pm = QHBoxLayout()
        row_pm.setSpacing(8)

        pm_lbl = QLabel("Paper Feed:")
        pm_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B;")
        row_pm.addWidget(pm_lbl)

        self.paper_mode_combo = NoScrollComboBox()
        self.paper_mode_combo.setMinimumHeight(30)
        for pm in PAPER_MODES:
            self.paper_mode_combo.addItem(pm)
        saved_pm = self.settings.value("paper_mode", PAPER_MODE_A4_CENTER)
        idx_pm = self.paper_mode_combo.findText(saved_pm)
        if idx_pm >= 0:
            self.paper_mode_combo.setCurrentIndex(idx_pm)
        self.paper_mode_combo.currentIndexChanged.connect(self._on_paper_mode_changed)
        row_pm.addWidget(self.paper_mode_combo, stretch=1)
        adv_layout.addLayout(row_pm)

        # Row 5: Fine Offsets (mm)
        row5 = QHBoxLayout()
        row5.setSpacing(8)

        off_lbl = QLabel("Alignment Offset:")
        off_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B;")
        row5.addWidget(off_lbl)

        self.x_offset_spin = NoScrollDoubleSpinBox()
        self.x_offset_spin.setRange(-50.0, 50.0)
        self.x_offset_spin.setSingleStep(0.5)
        self.x_offset_spin.setSuffix(" mm X")
        self.x_offset_spin.setMinimumHeight(30)
        self.x_offset_spin.setToolTip("Horizontal print alignment shift (+ right, - left)")
        row5.addWidget(self.x_offset_spin)

        self.y_offset_spin = NoScrollDoubleSpinBox()
        self.y_offset_spin.setRange(-50.0, 50.0)
        self.y_offset_spin.setSingleStep(0.5)
        self.y_offset_spin.setSuffix(" mm Y")
        self.y_offset_spin.setMinimumHeight(30)
        self.y_offset_spin.setToolTip("Vertical print alignment shift (+ down, - up)")
        row5.addWidget(self.y_offset_spin)

        reset_btn = QPushButton("Reset")
        reset_btn.setMinimumHeight(30)
        reset_btn.setToolTip("Reset offsets to 0.0 mm")
        reset_btn.setStyleSheet(
            "QPushButton {"
            "  font-size: 11px; font-weight: 600; background: #F1F5F9; color: #475569;"
            "  border: 1px solid #CBD5E1; border-radius: 4px; padding: 4px 10px;"
            "}"
            "QPushButton:hover { background: #E2E8F0; }"
        )
        reset_btn.clicked.connect(self._reset_offsets)
        row5.addWidget(reset_btn)

        saved_x = self.settings.value("x_offset", 0.0)
        saved_y = self.settings.value("y_offset", -4.50)
        try: self.x_offset_spin.setValue(float(saved_x))
        except Exception: self.x_offset_spin.setValue(0.0)
        try: self.y_offset_spin.setValue(float(saved_y))
        except Exception: self.y_offset_spin.setValue(-4.50)

        self.x_offset_spin.valueChanged.connect(self._on_offset_changed)
        self.y_offset_spin.valueChanged.connect(self._on_offset_changed)

        row5.addStretch()
        adv_layout.addLayout(row5)

        # Row 5b: Date Fine Tuning & Year Format
        row_date = QHBoxLayout()
        row_date.setSpacing(8)

        date_lbl = QLabel("Date Fine-Tune:")
        date_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B;")
        row_date.addWidget(date_lbl)

        self.date_x_spin = NoScrollDoubleSpinBox()
        self.date_x_spin.setRange(-30.0, 30.0)
        self.date_x_spin.setSingleStep(0.5)
        self.date_x_spin.setSuffix(" mm X")
        self.date_x_spin.setMinimumHeight(30)
        self.date_x_spin.setToolTip("Independent horizontal date shift (+ right, - left)")
        row_date.addWidget(self.date_x_spin)

        self.date_y_spin = NoScrollDoubleSpinBox()
        self.date_y_spin.setRange(-30.0, 30.0)
        self.date_y_spin.setSingleStep(0.5)
        self.date_y_spin.setSuffix(" mm Y")
        self.date_y_spin.setMinimumHeight(30)
        self.date_y_spin.setToolTip("Independent vertical date shift (+ down, - up)")
        row_date.addWidget(self.date_y_spin)

        self.year_format_combo = NoScrollComboBox()
        self.year_format_combo.setMinimumHeight(30)
        self.year_format_combo.addItem("2 Digits ('26)", 2)
        self.year_format_combo.addItem("4 Digits ('2026)", 4)
        saved_yf = self.settings.value("year_format", "2 Digits ('26)")
        idx_yf = self.year_format_combo.findText(saved_yf)
        if idx_yf >= 0:
            self.year_format_combo.setCurrentIndex(idx_yf)
        else:
            self.year_format_combo.setCurrentIndex(0)
        self.year_format_combo.setToolTip("Year digits format (2 digits for preprinted '20', 4 digits for blank boxes)")
        row_date.addWidget(self.year_format_combo)

        saved_dx = self.settings.value("date_x_offset", 4.50)
        saved_dy = self.settings.value("date_y_offset", 0.0)
        try: self.date_x_spin.setValue(float(saved_dx))
        except Exception: self.date_x_spin.setValue(4.50)
        try: self.date_y_spin.setValue(float(saved_dy))
        except Exception: self.date_y_spin.setValue(0.0)

        self.date_x_spin.valueChanged.connect(self._on_date_offset_changed)
        self.date_y_spin.valueChanged.connect(self._on_date_offset_changed)
        self.year_format_combo.currentIndexChanged.connect(self._on_year_format_changed)

        row_date.addStretch()
        adv_layout.addLayout(row_date)

        # Legacy custom paper name edit (only shown when in Custom Cheque Size mode)
        self.paper_name_edit = QLineEdit()
        self.paper_name_edit.setText(self.settings.value("paper_name", "Check SL"))
        self.paper_name_edit.setPlaceholderText("Custom Windows Form Name")
        self.paper_name_edit.setMinimumHeight(30)
        self.paper_name_edit.textChanged.connect(
            lambda: self.settings.setValue("paper_name", self.paper_name_edit.text().strip())
        )
        self.paper_name_edit.setVisible(self.paper_mode_combo.currentText() == PAPER_MODE_EXACT)
        adv_layout.addWidget(self.paper_name_edit)

        # Row 5c: Save Settings Action Row
        save_settings_row = QHBoxLayout()
        save_settings_row.setSpacing(10)

        self.save_settings_btn = QPushButton("💾 Save Settings")
        self.save_settings_btn.setMinimumHeight(32)
        self.save_settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_settings_btn.setToolTip("Save current offsets, date fine-tune, paper feed, printer, and defaults permanently")
        self.save_settings_btn.setStyleSheet(
            "QPushButton {"
            "  font-size: 11px; font-weight: 700; background: #0284C7; color: #FFFFFF;"
            "  border: none; border-radius: 4px; padding: 6px 14px;"
            "}"
            "QPushButton:hover { background: #0369A1; }"
            "QPushButton:pressed { background: #075985; }"
        )
        self.save_settings_btn.clicked.connect(self._save_settings)
        save_settings_row.addWidget(self.save_settings_btn)

        self.settings_status_lbl = QLabel("")
        self.settings_status_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #16A34A;")
        save_settings_row.addWidget(self.settings_status_lbl)
        save_settings_row.addStretch()

        adv_layout.addLayout(save_settings_row)

        # Hide container by default
        self.advanced_container.setVisible(False)
        left_layout.addWidget(self.advanced_container)

        left_layout.addStretch()

        # Row 6: Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.print_btn = QPushButton("🖨️ Print Cheque")
        self.print_btn.setMinimumHeight(40)
        self.print_btn.setStyleSheet(
            "QPushButton {"
            "  font-size: 14px; font-weight: 700; background-color: #0284C7; color: #FFFFFF;"
            "  border: none; border-radius: 6px; padding: 8px 16px;"
            "}"
            "QPushButton:hover { background-color: #0369A1; }"
            "QPushButton:pressed { background-color: #075985; }"
        )
        self.print_btn.clicked.connect(self._print_cheque)
        btn_row.addWidget(self.print_btn, stretch=3)

        self.test_btn = QPushButton("📄 A4 Test")
        self.test_btn.setMinimumHeight(40)
        self.test_btn.setStyleSheet(
            "QPushButton {"
            "  font-size: 12px; font-weight: 600; background: #F1F5F9; color: #334155;"
            "  border: 1px solid #CBD5E1; border-radius: 6px; padding: 6px 12px;"
            "}"
            "QPushButton:hover { background: #E2E8F0; }"
        )
        self.test_btn.setToolTip("Print on plain A4 with cheque outline for zero-waste testing")
        self.test_btn.clicked.connect(self._test_print_guidelines)
        btn_row.addWidget(self.test_btn, stretch=1)

        self.preview_btn = QPushButton("👁️ PDF")
        self.preview_btn.setMinimumHeight(40)
        self.preview_btn.setStyleSheet(
            "QPushButton {"
            "  font-size: 12px; font-weight: 600; background: #F1F5F9; color: #334155;"
            "  border: 1px solid #CBD5E1; border-radius: 6px; padding: 6px 12px;"
            "}"
            "QPushButton:hover { background: #E2E8F0; }"
        )
        self.preview_btn.setToolTip("Open exact PDF preview in your default browser")
        self.preview_btn.clicked.connect(self._preview_pdf)
        btn_row.addWidget(self.preview_btn, stretch=1)

        left_layout.addLayout(btn_row)
        main_layout.addWidget(left_card, stretch=5)

        # ══════════════════════════════════════════════════════════════════════
        # RIGHT COLUMN: LIVE CHEQUE PREVIEW CARD
        # ══════════════════════════════════════════════════════════════════════
        right_card = QFrame()
        right_card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; }"
        )
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(8)

        # Preview Header with Mode Toggle
        p_head = QHBoxLayout()
        p_title = QLabel("LIVE CHEQUE PREVIEW")
        p_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; letter-spacing: 0.5px;")
        p_head.addWidget(p_title)
        p_head.addStretch()

        self.zoom_radio = QRadioButton("Cheque Zoom")
        self.zoom_radio.setChecked(True)
        self.zoom_radio.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155;")
        self.zoom_radio.toggled.connect(self._on_preview_mode_toggle)
        p_head.addWidget(self.zoom_radio)

        self.a4_radio = QRadioButton("A4 Sheet")
        self.a4_radio.setStyleSheet("font-size: 11px; font-weight: 600; color: #334155;")
        self.a4_radio.toggled.connect(self._on_preview_mode_toggle)
        p_head.addWidget(self.a4_radio)
        right_layout.addLayout(p_head)

        # Canvas
        self.preview_canvas = ChequePreviewWidget()
        self.preview_canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout.addWidget(self.preview_canvas)

        # Status Footer
        self.status_lbl = QLabel("Official LankaPay CITS (177.8 × 88.9 mm) • Auto Center Feed (16.1 mm Margins)")
        self.status_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.status_lbl)

        main_layout.addWidget(right_card, stretch=6)

        self.setCentralWidget(central)
        self.resize(1020, 520)
        self._on_change()

    # ── Helpers & Events ─────────────────────────────────────────────────────

    def _make_renderer(self, draw_guidelines: bool = False) -> ChequeRenderer:
        bank_key = self.bank_combo.currentData()
        cfg = self.banks[bank_key]
        payee = self.payee_edit.text().strip() or "SAMPATH PERERA"
        amount = self.amount_spin.value()
        cheque_date = self.date_edit.date().toString("dd / MM / yyyy")
        cross_mode = self.cross_combo.currentText()
        x_offset = self.x_offset_spin.value()
        y_offset = self.y_offset_spin.value()
        paper_mode = self.paper_mode_combo.currentText()
        year_digits = self.year_format_combo.currentData() or 2
        date_x = self.date_x_spin.value()
        date_y = self.date_y_spin.value()

        return ChequeRenderer(
            cfg, payee, amount, cheque_date, cross_mode,
            x_offset, y_offset, paper_mode, draw_guidelines,
            year_digits=year_digits,
            date_x_offset_mm=date_x,
            date_y_offset_mm=date_y,
        )

    def _on_change(self):
        self.words_label.setText(amount_to_words(self.amount_spin.value()))
        renderer = self._make_renderer()
        self.preview_canvas.set_renderer(renderer, show_a4_view=self.a4_radio.isChecked())

    def _on_preview_mode_toggle(self):
        self._on_change()

    def _on_paper_mode_changed(self):
        pm = self.paper_mode_combo.currentText()
        self.settings.setValue("paper_mode", pm)
        self.paper_name_edit.setVisible(pm == PAPER_MODE_EXACT)
        if pm == PAPER_MODE_A4_CENTER:
            self.status_lbl.setText("Official LankaPay CITS (177.8 × 88.9 mm) • Auto Center Feed (16.1 mm Margins)")
        elif pm == PAPER_MODE_A4_LEFT:
            self.status_lbl.setText("Official LankaPay CITS (177.8 × 88.9 mm) • Left-Aligned Feed (0 mm Margin)")
        else:
            self.status_lbl.setText("Custom Cheque Slip Form (178 × 89 mm)")
        self._on_change()

    def _toggle_more_options(self):
        if self.advanced_container.isVisible():
            self.advanced_container.setVisible(False)
            self.more_options_btn.setText("🔒 More Options ▾")
        else:
            dlg = PasscodeDialog(self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                if dlg.get_passcode().strip() == "0000":
                    self.advanced_container.setVisible(True)
                    self.more_options_btn.setText("⚙️ Hide More Options ▴")
                else:
                    QMessageBox.warning(self, "Access Denied", "Incorrect passcode! Default passcode is 0000.")

    def _reset_offsets(self):
        self.x_offset_spin.setValue(0.0)
        self.y_offset_spin.setValue(-4.50)
        self.date_x_spin.setValue(4.50)
        self.date_y_spin.setValue(0.0)
        idx_yf = self.year_format_combo.findText("2 Digits ('26)")
        if idx_yf >= 0:
            self.year_format_combo.setCurrentIndex(idx_yf)

    def _save_settings(self):
        """Persist fine-tuning offsets, paper feed mode, printer, and defaults to disk/registry."""
        # Alignment offsets
        self.settings.setValue("x_offset", self.x_offset_spin.value())
        self.settings.setValue("y_offset", self.y_offset_spin.value())

        # Date shift & year format
        self.settings.setValue("date_x_offset", self.date_x_spin.value())
        self.settings.setValue("date_y_offset", self.date_y_spin.value())
        self.settings.setValue("year_format", self.year_format_combo.currentText())

        # Paper feed mode
        self.settings.setValue("paper_mode", self.paper_mode_combo.currentText())

        # Selected printer
        if hasattr(self, "printer_combo") and self.printer_combo.currentText():
            self.settings.setValue("printer", self.printer_combo.currentText())

        # Bank & crossing selections
        if hasattr(self, "bank_combo") and self.bank_combo.currentData():
            self.settings.setValue("bank", self.bank_combo.currentData())
        if hasattr(self, "cross_combo") and self.cross_combo.currentText():
            self.settings.setValue("cross_mode", self.cross_combo.currentText())

        # Custom paper name if present
        if hasattr(self, "paper_name_edit"):
            self.settings.setValue("paper_name", self.paper_name_edit.text().strip())

        # Current payee saved to DB and dropdown updated
        if hasattr(self, "payee_edit"):
            self.payee_edit.save_current()

        # Force sync to persistent storage
        self.settings.sync()

        # Feedback
        self.settings_status_lbl.setText("✓ Settings saved successfully for next time!")
        QTimer.singleShot(4000, lambda: self.settings_status_lbl.setText(""))

    def _on_offset_changed(self):
        self.settings.setValue("x_offset", self.x_offset_spin.value())
        self.settings.setValue("y_offset", self.y_offset_spin.value())
        self._on_change()

    def _on_date_offset_changed(self):
        self.settings.setValue("date_x_offset", self.date_x_spin.value())
        self.settings.setValue("date_y_offset", self.date_y_spin.value())
        self._on_change()

    def _on_year_format_changed(self):
        self.settings.setValue("year_format", self.year_format_combo.currentText())
        self._on_change()

    def _configure_printer(self, printer: QPrinter, paper_mode: str):
        bank_key = self.bank_combo.currentData()
        cfg = self.banks[bank_key]

        if paper_mode in (PAPER_MODE_A4_CENTER, PAPER_MODE_A4_LEFT):
            page_size = QPageSize(QPageSize.PageSizeId.A4)
            layout = QPageLayout(
                page_size,
                QPageLayout.Orientation.Portrait,
                QMarginsF(0, 0, 0, 0),
                QPageLayout.Unit.Millimeter,
            )
            printer.setPageLayout(layout)
            printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        else:
            w_mm = cfg.get("paper_width_mm", cfg["cheque_width_mm"])
            h_mm = cfg.get("paper_height_mm", cfg["cheque_height_mm"])
            page_size = QPageSize(QSizeF(h_mm, w_mm), QPageSize.Unit.Millimeter, "Cheque")
            layout = QPageLayout(
                page_size,
                QPageLayout.Orientation.Landscape,
                QMarginsF(0, 0, 0, 0),
                QPageLayout.Unit.Millimeter,
            )
            printer.setPageLayout(layout)
            printer.setPageOrientation(QPageLayout.Orientation.Landscape)

    def _draw_on_printer(self, printer: QPrinter, draw_guidelines: bool = False):
        painter = QPainter(printer)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        renderer = self._make_renderer(draw_guidelines=draw_guidelines)

        dpi = painter.device().logicalDpiX()
        if dpi != 96:
            painter.scale(dpi / 96.0, dpi / 96.0)
        renderer.render(painter)
        painter.end()

    # ── Print & Preview Actions ──────────────────────────────────────────────

    def _preview_pdf(self):
        if not self._validate():
            return
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix="cheque_preview_")
        tmp.close()
        pdf_path = tmp.name

        paper_mode = self.paper_mode_combo.currentText()
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(pdf_path)

        self._configure_printer(printer, paper_mode)
        self._draw_on_printer(printer, draw_guidelines=False)

        webbrowser.open(f"file:///{pdf_path.replace(os.sep, '/')}")

    def _test_print_guidelines(self):
        if not self._validate():
            return

        printer_name = self.printer_combo.currentText()
        if not printer_name:
            QMessageBox.warning(self, "No Printer", "Please select a printer from the dropdown.")
            return

        printer_info = QPrinterInfo.printerInfo(printer_name)
        if printer_info.isNull():
            printer_info = QPrinterInfo.defaultPrinter()

        printer = QPrinter(printer_info, QPrinter.PrinterMode.HighResolution)
        paper_mode = self.paper_mode_combo.currentText()
        self._configure_printer(printer, paper_mode)

        try:
            self._draw_on_printer(printer, draw_guidelines=True)
            QMessageBox.information(
                self, "Test Print Sent",
                f"A4 test alignment print has been sent directly to:\n\n{printer_name}\n\n(Dashed cheque outline included for alignment checking)"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Print Error",
                f"Failed to send print job to {printer_name}:\n\n{e}"
            )

    def _print_cheque(self):
        if not self._validate():
            return

        printer_name = self.printer_combo.currentText()
        if not printer_name:
            QMessageBox.warning(self, "No Printer", "Please select a printer from the dropdown.")
            return

        printer_info = QPrinterInfo.printerInfo(printer_name)
        if printer_info.isNull():
            printer_info = QPrinterInfo.defaultPrinter()

        printer = QPrinter(printer_info, QPrinter.PrinterMode.HighResolution)
        paper_mode = self.paper_mode_combo.currentText()
        self._configure_printer(printer, paper_mode)

        try:
            self._draw_on_printer(printer, draw_guidelines=False)

            # Save payee to database history & refresh dropdown
            self.payee_edit.save_current()

            QMessageBox.information(
                self, "Print Sent",
                f"Cheque print job has been sent directly to:\n\n{printer_name}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Print Error",
                f"Failed to send print job to {printer_name}:\n\n{e}"
            )

    def _validate(self) -> bool:
        if not self.payee_edit.text().strip():
            QMessageBox.warning(self, "Missing Field", "Please enter the payee name.")
            self.payee_edit.setFocus()
            return False
        if self.amount_spin.value() <= 0:
            QMessageBox.warning(self, "Missing Field", "Please enter a valid amount.")
            return False
        return True


class GlobalWheelFilter(QObject):
    """Application-wide filter that disables mouse wheel value changes on inputs."""
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            if isinstance(obj, (QComboBox, QDoubleSpinBox, QDateEdit)):
                event.ignore()
                return True
        return super().eventFilter(obj, event)


def main():
    print("Starting Growvia Cheque Writer GUI...", flush=True)

    # Windows AppUserModelID for proper taskbar grouping and logo icon
    try:
        myappid = "Growvia.ChequeWriter.App.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)

    icon_cand = resource_path("icon.png")
    if not icon_cand.exists():
        icon_cand = resource_path("icon.ico")
    if icon_cand.exists():
        app.setWindowIcon(QIcon(str(icon_cand)))

    wheel_filter = GlobalWheelFilter(app)
    app.installEventFilter(wheel_filter)

    banks = load_banks()
    if not banks:
        QMessageBox.critical(None, "Error", "No bank config files found in banks/ folder.")
        sys.exit(1)

    window = MainWindow(banks)

    # Center on primary screen
    screen = app.primaryScreen()
    if screen:
        avail = screen.availableGeometry()
        w_width = min(1040, avail.width() - 30)
        w_height = min(530, avail.height() - 40)
        window.resize(w_width, w_height)
        x = avail.left() + (avail.width() - w_width) // 2
        y = avail.top() + (avail.height() - w_height) // 2
        window.move(x, y)

    window.show()
    window.raise_()
    window.activateWindow()

    try:
        import ctypes
        hwnd = int(window.winId())
        ctypes.windll.user32.ShowWindow(hwnd, 9)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass

    print("Cheque Writer window is ready on your screen!", flush=True)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
