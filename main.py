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
    QLabel, QLineEdit, QComboBox, QPushButton, QGroupBox, QFrame,
    QDateEdit, QDoubleSpinBox, QSizePolicy, QScrollArea,
    QMessageBox, QCompleter, QDialog, QStyle,
)
from PyQt6.QtCore import Qt, QDate, QRectF, QSizeF, QMarginsF, QStringListModel, QSettings
from PyQt6.QtGui import (
    QPainter, QFont, QFontMetrics, QPen, QColor, QPageLayout, QPageSize, QPalette,
)
from PyQt6.QtPrintSupport import QPrinter, QPrinterInfo, QPrintPreviewDialog, QPrintPreviewWidget

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

CROSS_MODES = [
    "Cross A/C Payee + Or Bearer",
    "Cross A/C Payee + Not Negotiable + Or Bearer",
    "Cross A/C Payee",
    "Cross Only",
    "No Crossing",
]


def mm(value: float) -> float:
    return value * MM_TO_PX


def resource_path(name: str) -> Path:
    """Locate a bundled file whether running frozen (PyInstaller) or from source."""
    if getattr(sys, "frozen", False):
        # onefile build extracts datas to _MEIPASS; also check next to the exe
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
        data = json.loads(f.read_text())
        banks[data["short"]] = data
    return banks


def star(text: str) -> str:
    """Wrap text with ** security markers as seen on Sri Lankan cheques."""
    return f"**{text}**"


class ChequeRenderer:
    def __init__(self, bank_config: dict, payee: str, amount: float,
                 cheque_date: str, cross_mode: str, x_offset_mm: float = 0.0, y_offset_mm: float = 0.0):
        self.cfg = bank_config
        self.payee = payee
        self.amount = amount
        self.cheque_date = cheque_date
        self.cross_mode = cross_mode
        self.x_offset_mm = x_offset_mm
        self.y_offset_mm = y_offset_mm

    FONT = "Times New Roman"

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
        rect = QRectF(mm(x_mm + self.x_offset_mm), mm(y_mm + self.y_offset_mm) - mm(font_size_mm),
                      mm(max_width_mm), mm(font_size_mm * 1.4))
        painter.drawText(rect, align, text)

    def _split_by_width(self, text: str, font_size_mm: float, max_width_mm: float,
                        prefix: str = "", suffix: str = "") -> tuple[str, str]:
        """Split text at a word boundary using real font metrics.

        prefix/suffix are added when measuring line 1 (e.g. '**') so the
        rendered width matches the measured width exactly.
        """
        fm = QFontMetrics(self._make_font(font_size_mm))
        max_px = int(mm(max_width_mm))
        word_list = text.split()
        line1_words: list[str] = []
        for i, word in enumerate(word_list):
            candidate = prefix + " ".join(line1_words + [word]) + (suffix if i == len(word_list) - 1 else "")
            if fm.horizontalAdvance(candidate) > max_px:
                line2 = " ".join(word_list[i:])
                return " ".join(line1_words), line2
            line1_words.append(word)
        return " ".join(line1_words), ""

    def _draw_date_boxes(self, painter: QPainter):
        f = self.cfg["fields"]
        parts = self.cheque_date.replace(" ", "").split("/")
        dd   = parts[0].zfill(2) if len(parts) > 0 else "  "
        mm_s = parts[1].zfill(2) if len(parts) > 1 else "  "
        # year_digits in JSON controls how many digits to print (2 or 4)
        year_digits = self.cfg.get("year_digits", 4)
        raw_year = parts[2] if len(parts) > 2 else ""
        yy = raw_year[-year_digits:].zfill(year_digits)

        fdd   = f["date_dd"]
        fmm   = f["date_mm"]
        fyyyy = f["date_yyyy"]
        spacing = fdd.get("letter_spacing_mm", 4.2)
        fs = fdd["font_size"]

        for i, ch in enumerate(dd):
            self._draw_text(painter, fdd["x"] + i * spacing, fdd["y"], ch, fs,
                            align=Qt.AlignmentFlag.AlignHCenter, max_width_mm=spacing)
        for i, ch in enumerate(mm_s):
            self._draw_text(painter, fmm["x"] + i * spacing, fmm["y"], ch, fs,
                            align=Qt.AlignmentFlag.AlignHCenter, max_width_mm=spacing)
        shift = 4 - year_digits
        for i, ch in enumerate(yy):
            self._draw_text(painter, fyyyy["x"] + (i + shift) * spacing, fyyyy["y"], ch, fs,
                            align=Qt.AlignmentFlag.AlignHCenter, max_width_mm=spacing)

    def render(self, painter: QPainter):
        f = self.cfg["fields"]

        # Date digits into boxes
        self._draw_date_boxes(painter)

        # Payee — wrapped with ** **, not bold (cheque font is plain)
        pf = f["payee"]
        self._draw_text(painter, pf["x"], pf["y"], star(self.payee),
                        pf["font_size"], bold=False,
                        max_width_mm=pf.get("max_width", 130))

        # Amount box — ** amount ** centred
        ab = f["amount_box"]
        align = (Qt.AlignmentFlag.AlignHCenter
                 if ab.get("align") == "center" else Qt.AlignmentFlag.AlignLeft)
        self._draw_text(painter, ab["x"], ab["y"],
                        star(f"{self.amount:,.2f}"),
                        ab["font_size"], bold=False,
                        align=align, max_width_mm=ab.get("max_width", 54))

        # Amount in words — split using real font metrics so text never clips
        words = amount_to_words(self.amount)
        aw  = f["amount_words"]
        aw2 = f["amount_words_line2"]
        max_w = aw.get("max_width", 93)
        fs_w  = aw["font_size"]

        # Split measuring with the actual ** prefix/suffix so no word is clipped
        part1, part2 = self._split_by_width(words, fs_w, max_w, prefix="**")
        if part2:
            line1 = "**" + part1
            line2 = part2 + "**"
        else:
            line1 = star(part1)
            line2 = ""

        self._draw_text(painter, aw["x"], aw["y"], line1, fs_w, max_width_mm=max_w)
        if line2:
            self._draw_text(painter, aw2["x"], aw2["y"], line2, aw2["font_size"],
                            max_width_mm=max_w)

        # Crossing
        if self.cross_mode != "No Crossing":
            self._draw_crossing(painter)

    def _draw_crossing(self, painter: QPainter):
        """Draw two parallel diagonal lines with text between them (like a crossing stamp).

        Lines run from upper-right → lower-left, matching the standard Sri Lankan
        cheque crossing. All coordinates are in mm from the cheque origin.
        """
        label_map = {
            "Cross A/C Payee + Or Bearer":                  ["A/C PAYEE ONLY"],
            "Cross A/C Payee + Not Negotiable + Or Bearer": ["NOT NEGOTIABLE", "A/C PAYEE ONLY"],
            "Cross A/C Payee":                              ["A/C PAYEE ONLY"],
            "Cross Only":                                   [],
        }
        lines = label_map.get(self.cross_mode, [])

        pen = QPen(QColor(0, 0, 0))
        pen.setWidthF(mm(0.38))
        painter.setPen(pen)

        # ── Two fixed diagonal lines ─────────────────────────────────────
        # Line 1 (upper / closer to corner): top-right to bottom-left
        # Tilted more clockwise (rotated to the right)
        x1a, y1a = mm(2 + self.x_offset_mm),  mm(18 + self.y_offset_mm)   # bottom-left end
        x1b, y1b = mm(24 + self.x_offset_mm), mm(3 + self.y_offset_mm)    # top-right end
        painter.drawLine(int(x1a), int(y1a), int(x1b), int(y1b))

        # Line 2 (lower): parallel, shifted 8 mm to the right/down for larger text space
        gap_mm = 8.0
        import math
        angle_rad = math.atan2(y1a - y1b, x1b - x1a)   # angle of the line
        dx = gap_mm * math.sin(angle_rad)
        dy = gap_mm * math.cos(angle_rad)
        x2a, y2a = x1a + mm(dx), y1a + mm(dy)
        x2b, y2b = x1b + mm(dx), y1b + mm(dy)
        painter.drawLine(int(x2a), int(y2a), int(x2b), int(y2b))

        # ── Text centred between the two lines ───────────────────────────
        if not lines:
            return

        # Mid-point between the two lines — shift right so 'A' isn't clipped
        mid_x = (x1a + x1b + x2a + x2b) / 4 + mm(3)
        mid_y = (y1a + y1b + y2a + y2b) / 4
        angle_deg = math.degrees(math.atan2(y1b - y1a, x1b - x1a))

        painter.save()
        painter.translate(mid_x, mid_y)
        painter.rotate(angle_deg)

        # Larger font size for visibility (3.5 mm instead of 2.6 mm)
        font = self._make_font(3.5)
        painter.setFont(font)
        painter.setPen(QPen(QColor(0, 0, 0)))

        text_spacing = mm(4.5)
        total = text_spacing * (len(lines) - 1)
        half_w = mm(18)
        for i, text in enumerate(lines):
            y_off = -total / 2 + i * text_spacing
            rect = QRectF(-half_w, y_off - mm(3.5), half_w * 2, mm(4.5))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

        painter.restore()


# (PreviewWidget removed as we print directly to the printer now)


class PayeeLineEdit(QLineEdit):
    """QLineEdit with live SQLite-backed autocomplete."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = QStringListModel()
        self._completer = QCompleter(self._model, self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        popup = self._completer.popup()
        if popup:
            popup.setStyleSheet(
                "QListView { font-size: 14px; padding: 4px; color: #111; background: white; }"
                "QListView::item { padding: 6px 8px; min-height: 28px; }"
                "QListView::item:selected { background: #1a3c5e; color: white; }"
            )
        self.setCompleter(self._completer)
        self.textEdited.connect(self._refresh_suggestions)

    def _refresh_suggestions(self, text: str):
        suggestions = search_payees(text) if text.strip() else []
        self._model.setStringList(suggestions)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        if not self.text():
            self._model.setStringList(all_payees())


# ── Shared stylesheet applied to the whole app ──────────────────────────────
APP_STYLE = """
QMainWindow, QWidget {
    background-color: #F0F4F8;
    color: #1A2B3C;
    font-family: 'Segoe UI', Arial, sans-serif;
}

/* Section labels / group box titles */
QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #D8E2EC;
    border-radius: 8px;
    margin-top: 10px;
    padding: 12px 14px 10px 14px;
    font-size: 11px;
    font-weight: 600;
    color: #5A7A96;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: -1px;
    padding: 0 6px;
    background-color: #FFFFFF;
}

/* All input fields */
QLineEdit, QDateEdit, QDoubleSpinBox, QComboBox {
    background-color: #FFFFFF;
    color: #1A2B3C;
    border: 1.5px solid #C5D5E4;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 14px;
    selection-background-color: #1A5276;
    selection-color: #FFFFFF;
}
QLineEdit:focus, QDateEdit:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 2px solid #1A5276;
    background-color: #FAFCFF;
}
QLineEdit:hover, QDateEdit:hover, QDoubleSpinBox:hover, QComboBox:hover {
    border-color: #7FAFC8;
}

/* Dropdown arrow */
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox::down-arrow {
    width: 12px;
    height: 12px;
}
QComboBox QAbstractItemView {
    background: #FFFFFF;
    color: #1A2B3C;
    border: 1px solid #C5D5E4;
    border-radius: 4px;
    padding: 4px;
    selection-background-color: #1A5276;
    selection-color: #FFFFFF;
    font-size: 13px;
}

/* Spin box buttons */
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    width: 22px;
    background: #EAF0F6;
    border: none;
    border-left: 1px solid #C5D5E4;
    border-radius: 0px;
}
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
    background: #D0E2F0;
}

/* Date edit calendar button */
QDateEdit::drop-down {
    width: 28px;
    border: none;
    background: #EAF0F6;
    border-left: 1px solid #C5D5E4;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}
QDateEdit::down-arrow {
    width: 12px;
    height: 12px;
}

/* Calendar popup */
QCalendarWidget QWidget {
    background-color: #FFFFFF;
    color: #1A2B3C;
    alternate-background-color: #F5F8FB;
}
QCalendarWidget QToolButton {
    background-color: #1A5276;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 13px;
    font-weight: 600;
}
QCalendarWidget QToolButton:hover {
    background-color: #1F618D;
}
QCalendarWidget QSpinBox {
    background: #FFFFFF;
    color: #1A2B3C;
    border: 1px solid #C5D5E4;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 13px;
}
QCalendarWidget QMenu {
    background: #FFFFFF;
    color: #1A2B3C;
    border: 1px solid #C5D5E4;
}
QCalendarWidget QAbstractItemView:enabled {
    background-color: #FFFFFF;
    color: #1A2B3C;
    selection-background-color: #1A5276;
    selection-color: #FFFFFF;
    font-size: 12px;
}
QCalendarWidget QAbstractItemView:disabled {
    color: #B0C4D4;
}
/* Header row (Sun Mon Tue ...) */
QCalendarWidget QHeaderView {
    background-color: #EAF0F6;
    color: #5A7A96;
    font-size: 11px;
    font-weight: 600;
}
QCalendarWidget QHeaderView::section {
    background-color: #EAF0F6;
    color: #5A7A96;
    border: none;
    padding: 4px;
}

/* Scrollbar */
QScrollBar:vertical {
    background: #EAF0F6;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #A0BDD0;
    border-radius: 4px;
    min-height: 30px;
}
"""

PAYEE_FIELD_STYLE = """
QLineEdit {
    font-size: 17px;
    font-weight: 500;
    color: #0D1B2A;
    background-color: #FFFFFF;
    border: 2px solid #C5D5E4;
    border-radius: 7px;
    padding: 11px 14px;
    letter-spacing: 0.2px;
}
QLineEdit:focus {
    border: 2.5px solid #1A5276;
    background-color: #FAFCFF;
}
QLineEdit:hover {
    border-color: #5B9BBD;
}
"""


def _list_printers() -> list[str]:
    """Return installed printer names using PowerShell — no extra dependencies."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-command",
             "Get-Printer | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True, timeout=8
        )
        names = [p.strip() for p in r.stdout.splitlines() if p.strip()]
        return names if names else ["Default Printer"]
    except Exception:
        return ["Default Printer"]


class PrintDialog(QDialog):
    """Printer + paper-size selector — avoids the broken Windows 11 modern dialog."""

    def __init__(self, cheque_w_mm: float, cheque_h_mm: float, parent=None):
        super().__init__(parent)
        self.cheque_w_mm = cheque_w_mm
        self.cheque_h_mm = cheque_h_mm
        self.setWindowTitle("Print Cheque")
        self.setMinimumWidth(400)
        self.setStyleSheet(APP_STYLE)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 20, 20, 20)

        # ── Printer ───────────────────────────────────────────────────────
        lay.addWidget(QLabel("Printer:"))
        self.printer_combo = QComboBox()
        self.printer_combo.setMinimumHeight(38)
        for info in QPrinterInfo.availablePrinters():
            self.printer_combo.addItem(info.printerName())
        # Highlight default printer
        default = QPrinterInfo.defaultPrinterName()
        idx = self.printer_combo.findText(default)
        if idx >= 0:
            self.printer_combo.setCurrentIndex(idx)
        self.printer_combo.currentIndexChanged.connect(self._on_printer_changed)
        lay.addWidget(self.printer_combo)

        # ── Paper size ────────────────────────────────────────────────────
        lay.addWidget(QLabel("Paper Size:"))
        self.size_combo = QComboBox()
        self.size_combo.setMinimumHeight(38)
        lay.addWidget(self.size_combo)

        # ── Orientation ───────────────────────────────────────────────────
        lay.addWidget(QLabel("Orientation:"))
        self.orientation_combo = QComboBox()
        self.orientation_combo.setMinimumHeight(38)
        self.orientation_combo.addItem("Landscape", QPageLayout.Orientation.Landscape)
        self.orientation_combo.addItem("Portrait", QPageLayout.Orientation.Portrait)
        self.orientation_combo.setCurrentIndex(0) # Default to Landscape
        lay.addWidget(self.orientation_combo)

        # Populate sizes for initial printer
        self._on_printer_changed()

        # ── Buttons ───────────────────────────────────────────────────────
        btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(38)
        cancel_btn.clicked.connect(self.reject)

        print_btn = QPushButton("  Print  ")
        print_btn.setMinimumHeight(38)
        print_btn.setStyleSheet(
            "background-color:#1A5276; color:white; font-weight:600;"
            "border-radius:6px; padding:6px 28px;"
        )
        print_btn.clicked.connect(self.accept)

        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addSpacing(8)
        btns.addWidget(print_btn)
        lay.addLayout(btns)

    def _on_printer_changed(self):
        """Reload paper sizes whenever the printer selection changes."""
        self.size_combo.clear()

        # 1. Add the custom cheque page size as the first option
        cheque_size = QPageSize(QSizeF(self.cheque_h_mm, self.cheque_w_mm), QPageSize.Unit.Millimeter, "Cheque")
        label = f"Cheque Size  ({self.cheque_w_mm:.0f} × {self.cheque_h_mm:.0f} mm)"
        self.size_combo.addItem(label, cheque_size)

        # 2. Add all other supported page sizes
        name = self.printer_combo.currentText()
        info = QPrinterInfo.printerInfo(name)
        sizes = info.supportedPageSizes()
        for ps in sizes:
            w = ps.size(QPageSize.Unit.Millimeter).width()
            h = ps.size(QPageSize.Unit.Millimeter).height()
            longer = max(w, h)
            shorter = min(w, h)
            # Skip if it matches the custom cheque size to avoid duplicates
            if abs(longer - self.cheque_w_mm) < 1.0 and abs(shorter - self.cheque_h_mm) < 1.0:
                continue
            label = f"{ps.name()}  ({w:.0f} × {h:.0f} mm)"
            self.size_combo.addItem(label, ps)

        # 3. Always default to the custom Cheque Size
        self.size_combo.setCurrentIndex(0)

    def printer_name(self) -> str:
        return self.printer_combo.currentText()

    def selected_page_size(self) -> QPageSize | None:
        return self.size_combo.currentData()

    def selected_orientation(self) -> QPageLayout.Orientation:
        return self.orientation_combo.currentData()


class MainWindow(QMainWindow):
    def __init__(self, banks: dict):
        super().__init__()
        self.banks = banks
        self.setWindowTitle("Cheque Writer by Dev IMS")
        self.setMinimumWidth(560)

        # Force light palette so system dark mode doesn't override our stylesheet
        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#F0F4F8"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#1A2B3C"))
        pal.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#1A2B3C"))
        pal.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor("#1A2B3C"))
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#9BAFC0"))
        self.setPalette(pal)
        self.setStyleSheet(APP_STYLE)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setSpacing(10)
        root.setContentsMargins(20, 16, 20, 16)

        # ── Header ──────────────────────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 8)

        title = QLabel("Cheque Writer")
        title.setStyleSheet(
            "font-size: 24px; font-weight: 700; color: #1A3C5E; letter-spacing: -0.5px;"
        )
        subtitle = QLabel("Sri Lankan Bank Cheque Printing")
        subtitle.setStyleSheet("font-size: 12px; color: #7A96AA; margin-top: 4px;")
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        h_layout.addLayout(title_col)
        h_layout.addStretch()
        root.addWidget(header)

        # Thin divider under header
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background: #D8E2EC; border: none; max-height: 1px;")
        root.addWidget(line)

        # ── Bank + Date ──────────────────────────────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        bank_grp = QGroupBox("Bank")
        bank_inner = QVBoxLayout(bank_grp)
        bank_inner.setContentsMargins(12, 18, 12, 12)
        self.bank_combo = QComboBox()
        self.bank_combo.setMinimumHeight(40)
        for short in self.banks:
            self.bank_combo.addItem(self.banks[short]["name"], short)
        self.bank_combo.currentIndexChanged.connect(self._on_change)
        bank_inner.addWidget(self.bank_combo)
        top_row.addWidget(bank_grp, stretch=3)

        date_grp = QGroupBox("Cheque Date")
        date_inner = QVBoxLayout(date_grp)
        date_inner.setContentsMargins(12, 18, 12, 12)
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setDisplayFormat("dd / MM / yyyy")
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setMinimumHeight(40)
        self.date_edit.dateChanged.connect(self._on_change)
        date_inner.addWidget(self.date_edit)
        top_row.addWidget(date_grp, stretch=2)

        root.addLayout(top_row)

        # ── Pay To ───────────────────────────────────────────────────────────
        payee_grp = QGroupBox("Pay To")
        payee_inner = QVBoxLayout(payee_grp)
        payee_inner.setContentsMargins(12, 18, 12, 12)
        payee_inner.setSpacing(7)

        self.payee_edit = PayeeLineEdit()
        self.payee_edit.setPlaceholderText("Enter payee full name...")
        self.payee_edit.setStyleSheet(PAYEE_FIELD_STYLE)
        self.payee_edit.setMinimumHeight(50)
        self.payee_edit.textChanged.connect(self._on_change)
        payee_inner.addWidget(self.payee_edit)
        root.addWidget(payee_grp)

        # ── Amount + Crossing ────────────────────────────────────────────────
        mid_row = QHBoxLayout()
        mid_row.setSpacing(12)

        amount_grp = QGroupBox("Amount (Rs.)")
        amount_inner = QVBoxLayout(amount_grp)
        amount_inner.setContentsMargins(12, 18, 12, 12)
        amount_inner.setSpacing(8)
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.01, 99_999_999.99)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSingleStep(100)
        self.amount_spin.setValue(1000.00)
        self.amount_spin.setGroupSeparatorShown(True)
        self.amount_spin.setMinimumHeight(42)
        self.amount_spin.setStyleSheet(
            "QDoubleSpinBox { font-size: 16px; font-weight: 600; color: #0D3B6E; }"
        )
        self.amount_spin.valueChanged.connect(self._on_change)
        amount_inner.addWidget(self.amount_spin)

        self.words_label = QLabel()
        self.words_label.setStyleSheet(
            "color: #5B7A96; font-size: 11px; font-style: italic; padding-left: 2px;"
        )
        self.words_label.setWordWrap(True)
        amount_inner.addWidget(self.words_label)
        mid_row.addWidget(amount_grp, stretch=3)

        cross_grp = QGroupBox("Crossing Mode")
        cross_inner = QVBoxLayout(cross_grp)
        cross_inner.setContentsMargins(12, 18, 12, 12)
        self.cross_combo = QComboBox()
        self.cross_combo.setMinimumHeight(40)
        for m in CROSS_MODES:
            self.cross_combo.addItem(m)
        self.cross_combo.setCurrentIndex(0)
        self.cross_combo.currentIndexChanged.connect(self._on_change)
        cross_inner.addWidget(self.cross_combo)
        cross_inner.addStretch()
        mid_row.addWidget(cross_grp, stretch=2)

        root.addLayout(mid_row)

        # ── Alignment Offsets ────────────────────────────────────────────────
        offset_grp = QGroupBox("Print Alignment Adjustment (mm)")
        offset_inner = QHBoxLayout(offset_grp)
        offset_inner.setContentsMargins(12, 18, 12, 12)
        offset_inner.setSpacing(16)

        # Horizontal Offset
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Horizontal Shift (Left/Right):"))
        self.x_offset_spin = QDoubleSpinBox()
        self.x_offset_spin.setRange(-50.0, 50.0)
        self.x_offset_spin.setSingleStep(0.5)
        self.x_offset_spin.setSuffix(" mm")
        self.x_offset_spin.setMinimumHeight(36)
        h_layout.addWidget(self.x_offset_spin)
        offset_inner.addLayout(h_layout)

        # Vertical Offset
        v_layout = QHBoxLayout()
        v_layout.addWidget(QLabel("Vertical Shift (Up/Down):"))
        self.y_offset_spin = QDoubleSpinBox()
        self.y_offset_spin.setRange(-50.0, 50.0)
        self.y_offset_spin.setSingleStep(0.5)
        self.y_offset_spin.setSuffix(" mm")
        self.y_offset_spin.setMinimumHeight(36)
        v_layout.addWidget(self.y_offset_spin)
        offset_inner.addLayout(v_layout)

        # Load saved values from QSettings
        self.settings = QSettings("Growvia", "ChequeWriter")
        saved_x = self.settings.value("x_offset", 0.0)
        saved_y = self.settings.value("y_offset", 0.0)
        try:
            self.x_offset_spin.setValue(float(saved_x))
        except (ValueError, TypeError):
            self.x_offset_spin.setValue(0.0)
        try:
            self.y_offset_spin.setValue(float(saved_y))
        except (ValueError, TypeError):
            self.y_offset_spin.setValue(0.0)

        # Connect slots
        self.x_offset_spin.valueChanged.connect(self._on_offset_changed)
        self.y_offset_spin.valueChanged.connect(self._on_offset_changed)

        root.addWidget(offset_grp)

        # ── Printer ──────────────────────────────────────────────────────────
        printer_grp = QGroupBox("Printer")
        printer_inner = QVBoxLayout(printer_grp)
        printer_inner.setContentsMargins(12, 18, 12, 12)
        self.printer_combo = QComboBox()
        self.printer_combo.setMinimumHeight(40)
        for info in QPrinterInfo.availablePrinters():
            self.printer_combo.addItem(info.printerName())
        # Restore last used printer, else fall back to the system default
        saved_printer = self.settings.value("printer", "")
        idx = self.printer_combo.findText(saved_printer) if saved_printer else -1
        if idx < 0:
            idx = self.printer_combo.findText(QPrinterInfo.defaultPrinterName())
        if idx >= 0:
            self.printer_combo.setCurrentIndex(idx)
        self.printer_combo.currentIndexChanged.connect(
            lambda: self.settings.setValue("printer", self.printer_combo.currentText())
        )
        printer_inner.addWidget(self.printer_combo)

        # Cheque paper-size name — forces this size per job, so the printer's
        # DEFAULT paper (e.g. A4) can stay unchanged for normal printing.
        # Must match the custom paper size name created in Windows exactly.
        paper_row = QHBoxLayout()
        paper_row.addWidget(QLabel("Cheque Paper Size Name:"))
        self.paper_name_edit = QLineEdit()
        self.paper_name_edit.setMinimumHeight(36)
        self.paper_name_edit.setText(self.settings.value("paper_name", "Check SL"))
        self.paper_name_edit.setToolTip(
            "Must exactly match the custom paper size name created in Windows "
            "(Print Server Properties), e.g. 'Check SL'. Leave blank to use the "
            "printer's default paper."
        )
        self.paper_name_edit.textChanged.connect(
            lambda: self.settings.setValue("paper_name", self.paper_name_edit.text().strip())
        )
        paper_row.addWidget(self.paper_name_edit)
        printer_inner.addSpacing(8)
        printer_inner.addLayout(paper_row)

        root.addWidget(printer_grp)

        # ── Action buttons ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 8, 0, 0)

        self.print_btn = QPushButton("  Print Cheque  ")
        self.print_btn.setMinimumHeight(48)
        self.print_btn.setStyleSheet(
            "QPushButton {"
            "  font-size: 15px; font-weight: 600;"
            "  background-color: #1A5276;"
            "  color: #FFFFFF;"
            "  border: none;"
            "  border-radius: 8px;"
            "  padding: 12px 48px;"
            "  letter-spacing: 0.3px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #1F618D;"
            "}"
            "QPushButton:pressed {"
            "  background-color: #154360;"
            "}"
        )
        self.print_btn.clicked.connect(self._print_cheque)

        btn_row.addStretch()
        btn_row.addWidget(self.print_btn)
        root.addLayout(btn_row)

        # Wrap everything in a scroll area so the window always fits the screen
        # and shows a scrollbar when it can't.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(central)
        self.setCentralWidget(scroll)

        # Start at a compact size that fits small laptop screens
        self.resize(640, 700)

        self._on_change()

    # ------------------------------------------------------------------ helpers

    def _make_renderer(self) -> ChequeRenderer:
        bank_key = self.bank_combo.currentData()
        cfg = self.banks[bank_key]
        payee = self.payee_edit.text().strip() or "________________________________"
        amount = self.amount_spin.value()
        cheque_date = self.date_edit.date().toString("dd / MM / yyyy")
        cross_mode = self.cross_combo.currentText()
        x_offset = self.x_offset_spin.value()
        y_offset = self.y_offset_spin.value()
        return ChequeRenderer(cfg, payee, amount, cheque_date, cross_mode, x_offset, y_offset)

    def _on_change(self):
        self.words_label.setText(amount_to_words(self.amount_spin.value()))

    def _on_offset_changed(self):
        self.settings.setValue("x_offset", self.x_offset_spin.value())
        self.settings.setValue("y_offset", self.y_offset_spin.value())

    def _configure_printer(self, printer: QPrinter):
        bank_key = self.bank_combo.currentData()
        cfg = self.banks[bank_key]
        # Use the PHYSICAL paper size (e.g. Check SL 180×90) for the PDF page so
        # it matches the tray paper exactly — no rotation/centering shift when
        # SumatraPDF prints it. Falls back to the cheque size if not configured.
        w_mm = cfg.get("paper_width_mm", cfg["cheque_width_mm"])
        h_mm = cfg.get("paper_height_mm", cfg["cheque_height_mm"])

        # Custom page size: pass (short, long) = (90, 180) so Qt stores it
        # portrait-style, then Landscape swaps it back to 180×90 ✓
        page_size = QPageSize(QSizeF(h_mm, w_mm), QPageSize.Unit.Millimeter, "Cheque")
        layout = QPageLayout(page_size, QPageLayout.Orientation.Landscape,
                             QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
        printer.setPageLayout(layout)
        printer.setPageOrientation(QPageLayout.Orientation.Landscape)

    def _draw_on_printer(self, printer: QPrinter):
        painter = QPainter(printer)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        renderer = self._make_renderer()

        # Read DPI from the actual paint device (not the printer setting),
        # because PDF output may use a different logical DPI than what was set.
        dpi = painter.device().logicalDpiX()
        if dpi != 96:
            painter.scale(dpi / 96.0, dpi / 96.0)
        renderer.render(painter)
        painter.end()

    # ------------------------------------------------------------------ actions

    def _preview_pdf(self):
        if not self._validate():
            return
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix="cheque_preview_")
        tmp.close()
        pdf_path = tmp.name

        # Setup printer with PDF output settings
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(pdf_path)
        
        self._configure_printer(printer)
        self._draw_on_printer(printer)

        webbrowser.open(f"file:///{pdf_path.replace(os.sep, '/')}")

    def _silent_print(self, pdf_path: str) -> bool:
        """Print the PDF straight to the selected printer via bundled SumatraPDF.

        '-silent' suppresses any UI; '-print-settings noscale' prints the page
        at exact 1:1 size (so alignment offsets stay correct) and lets SumatraPDF
        deterministically rotate the landscape page to fit the cheque paper.
        """
        sumatra = resource_path("SumatraPDF.exe")
        if not sumatra.exists():
            QMessageBox.critical(self, "Print Error",
                                 f"SumatraPDF.exe not found:\n{sumatra}")
            return False

        printer_name = self.printer_combo.currentText()
        # 'noscale' keeps exact 1:1 size; 'paper=<name>' forces the cheque paper
        # size for THIS job only, so the printer's default paper stays untouched.
        print_settings = "noscale"
        paper = self.paper_name_edit.text().strip()
        if paper:
            print_settings += f",paper={paper}"
        args = [str(sumatra), "-print-to", printer_name,
                "-silent", "-print-settings", print_settings, pdf_path]
        try:
            result = subprocess.run(
                args, capture_output=True, text=True, timeout=60,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as e:
            QMessageBox.critical(self, "Print Error", f"Failed to print:\n{e}")
            return False

        if result.returncode != 0:
            QMessageBox.critical(
                self, "Print Error",
                f"SumatraPDF returned error code {result.returncode}.\n"
                f"{result.stderr.strip()}",
            )
            return False
        return True

    def _print_cheque(self):
        if not self._validate():
            return

        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix="cheque_print_")
        tmp.close()
        pdf_path = tmp.name

        # Setup printer with PDF output settings
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(pdf_path)

        self._configure_printer(printer)
        self._draw_on_printer(printer)

        # Print silently — no browser, no dialog
        if not self._silent_print(pdf_path):
            return

        # Clean up the temp PDF
        try:
            os.remove(pdf_path)
        except OSError:
            pass

        # Save payee to database history
        name = self.payee_edit.text().strip()
        if name:
            save_payee(name)

    def _validate(self) -> bool:
        if not self.payee_edit.text().strip():
            QMessageBox.warning(self, "Missing Field", "Please enter the payee name.")
            self.payee_edit.setFocus()
            return False
        if self.amount_spin.value() <= 0:
            QMessageBox.warning(self, "Missing Field", "Please enter a valid amount.")
            return False
        return True


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)

    banks = load_banks()
    if not banks:
        QMessageBox.critical(None, "Error", "No bank config files found in banks/ folder.")
        sys.exit(1)

    window = MainWindow(banks)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
