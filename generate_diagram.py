import sys
import os
import math
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import (
    QPainter, QImage, QColor, QPen, QFont, QBrush, QPolygonF, QFontMetrics
)
from PyQt6.QtCore import Qt, QRectF, QPointF

app = QApplication(sys.argv)

# Dimensions
IMG_W = 2400
IMG_H = 3000
img = QImage(IMG_W, IMG_H, QImage.Format.Format_ARGB32)
img.fill(QColor("#0F172A"))  # Dark Slate background for high contrast & elegance

painter = QPainter(img)
painter.setRenderHint(QPainter.RenderHint.Antialiasing)
painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

# Helper functions
def draw_arrow(p: QPainter, p1: QPointF, p2: QPointF, arrow_size=12, color=QColor("#38BDF8"), width=2):
    pen = QPen(color, width)
    p.setPen(pen)
    p.drawLine(p1, p2)
    
    angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
    arrow_p1 = QPointF(
        p2.x() - arrow_size * math.cos(angle - math.pi / 6),
        p2.y() - arrow_size * math.sin(angle - math.pi / 6)
    )
    arrow_p2 = QPointF(
        p2.x() - arrow_size * math.cos(angle + math.pi / 6),
        p2.y() - arrow_size * math.sin(angle + math.pi / 6)
    )
    p.setBrush(QBrush(color))
    p.drawPolygon(QPolygonF([p2, arrow_p1, arrow_p2]))

def draw_dim_h(p: QPainter, x1, x2, y, text, color=QColor("#38BDF8"), offset=0, font_size=16):
    pen = QPen(color, 2)
    p.setPen(pen)
    # Ticks
    p.drawLine(QPointF(x1, y - 8), QPointF(x1, y + 8))
    p.drawLine(QPointF(x2, y - 8), QPointF(x2, y + 8))
    
    # Arrow line
    arrow_sz = 10
    p.drawLine(QPointF(x1, y), QPointF(x2, y))
    p.setBrush(QBrush(color))
    p.drawPolygon(QPolygonF([QPointF(x1, y), QPointF(x1 + arrow_sz, y - 4), QPointF(x1 + arrow_sz, y + 4)]))
    p.drawPolygon(QPolygonF([QPointF(x2, y), QPointF(x2 - arrow_sz, y - 4), QPointF(x2 - arrow_sz, y + 4)]))
    
    # Label
    p.setFont(QFont("Segoe UI", font_size, QFont.Weight.Bold))
    fm = QFontMetrics(p.font())
    tw = fm.horizontalAdvance(text)
    th = fm.height()
    mid_x = (x1 + x2) / 2
    
    # Text badge background
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor("#0F172A")))
    p.drawRect(QRectF(mid_x - tw / 2 - 6, y - th / 2 - 2 + offset, tw + 12, th + 4))
    
    p.setPen(color)
    p.drawText(QRectF(mid_x - tw / 2 - 10, y - th / 2 + offset, tw + 20, th), Qt.AlignmentFlag.AlignCenter, text)

def draw_dim_v(p: QPainter, y1, y2, x, text, color=QColor("#38BDF8"), offset=0, font_size=16):
    pen = QPen(color, 2)
    p.setPen(pen)
    # Ticks
    p.drawLine(QPointF(x - 8, y1), QPointF(x + 8, y1))
    p.drawLine(QPointF(x - 8, y2), QPointF(x + 8, y2))
    
    # Arrow line
    arrow_sz = 10
    p.drawLine(QPointF(x, y1), QPointF(x, y2))
    p.setBrush(QBrush(color))
    p.drawPolygon(QPolygonF([QPointF(x, y1), QPointF(x - 4, y1 + arrow_sz), QPointF(x + 4, y1 + arrow_sz)]))
    p.drawPolygon(QPolygonF([QPointF(x, y2), QPointF(x - 4, y2 - arrow_sz), QPointF(x + 4, y2 - arrow_sz)]))
    
    # Label
    p.setFont(QFont("Segoe UI", font_size, QFont.Weight.Bold))
    fm = QFontMetrics(p.font())
    tw = fm.horizontalAdvance(text)
    th = fm.height()
    mid_y = (y1 + y2) / 2
    
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor("#0F172A")))
    p.drawRect(QRectF(x - tw / 2 - 6 + offset, mid_y - th / 2 - 2, tw + 12, th + 4))
    
    p.setPen(color)
    p.drawText(QRectF(x - tw / 2 - 10 + offset, mid_y - th / 2, tw + 20, th), Qt.AlignmentFlag.AlignCenter, text)


# ── Title & Header ─────────────────────────────────────────────────────────────
painter.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
painter.setPen(QColor("#F8FAFC"))
painter.drawText(QRectF(100, 60, 2200, 60), Qt.AlignmentFlag.AlignLeft, "A4 CHEQUE PRINTING SPECIFICATION & MEASUREMENTS")

painter.setFont(QFont("Segoe UI", 20, QFont.Weight.Normal))
painter.setPen(QColor("#94A3B8"))
painter.drawText(QRectF(100, 125, 2200, 40), Qt.AlignmentFlag.AlignLeft, "Official Sri Lankan Standard (LankaPay CITS: 7.0\" × 3.5\" = 177.8 × 88.9 mm) on A4 (210 × 297 mm)")

# Header Separator
painter.setPen(QPen(QColor("#334155"), 2))
painter.drawLine(100, 180, 2300, 180)


# ── Scale & Layout Coordinates ────────────────────────────────────────────────
# Scale: 6.2 pixels per millimeter
SCALE = 6.2

A4_MM_W = 210.0
A4_MM_H = 297.0

# OFFICIAL LANKACLEAR CITS STANDARD CHEQUE DIMENSIONS
CHQ_MM_W = 177.8   # 7.00 inches exactly (approx 178 mm)
CHQ_MM_H = 88.9    # 3.50 inches exactly (approx 89 mm)
MARGIN_MM = (A4_MM_W - CHQ_MM_W) / 2.0  # (210 - 177.8) / 2 = 16.1 mm

A4_PX_W = A4_MM_W * SCALE   # 1302 px
A4_PX_H = A4_MM_H * SCALE   # 1841.4 px

A4_LEFT = 220
A4_TOP  = 440

CHQ_LEFT = A4_LEFT + MARGIN_MM * SCALE
CHQ_TOP  = A4_TOP
CHQ_PX_W = CHQ_MM_W * SCALE  # 1102.36 px
CHQ_PX_H = CHQ_MM_H * SCALE  # 551.18 px

# ── Draw Tray Feed Direction Banner ───────────────────────────────────────────
feed_box = QRectF(A4_LEFT, A4_TOP - 160, A4_PX_W, 60)
painter.setPen(QPen(QColor("#10B981"), 2))
painter.setBrush(QBrush(QColor("#064E3B")))
painter.drawRoundedRect(feed_box, 8, 8)

painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
painter.setPen(QColor("#A7F3D0"))
painter.drawText(feed_box, Qt.AlignmentFlag.AlignCenter, "▼  PRINTER FEED DIRECTION (TOP EDGE / LEADING EDGE ENTERS FIRST)  ▼")

# Draw downward feed arrows
for arrow_x in [A4_LEFT + 200, A4_LEFT + A4_PX_W / 2, A4_LEFT + A4_PX_W - 200]:
    draw_arrow(painter, QPointF(arrow_x, A4_TOP - 90), QPointF(arrow_x, A4_TOP - 20), arrow_size=14, color=QColor("#10B981"), width=3)


# ── Draw A4 Paper Sheet ───────────────────────────────────────────────────────
# Drop shadow
shadow_rect = QRectF(A4_LEFT + 15, A4_TOP + 15, A4_PX_W, A4_PX_H)
painter.setPen(Qt.PenStyle.NoPen)
painter.setBrush(QBrush(QColor(0, 0, 0, 100)))
painter.drawRect(shadow_rect)

# White A4 sheet
a4_rect = QRectF(A4_LEFT, A4_TOP, A4_PX_W, A4_PX_H)
painter.setPen(QPen(QColor("#64748B"), 2))
painter.setBrush(QBrush(QColor("#FFFFFF")))
painter.drawRect(a4_rect)

# Unprinted / Empty A4 region pattern
empty_rect = QRectF(A4_LEFT, A4_TOP + CHQ_PX_H, A4_PX_W, A4_PX_H - CHQ_PX_H)
painter.setPen(Qt.PenStyle.NoPen)
painter.setBrush(QBrush(QColor("#F1F5F9")))
painter.drawRect(empty_rect)

painter.setFont(QFont("Segoe UI", 24, QFont.Weight.DemiBold))
painter.setPen(QColor("#94A3B8"))
painter.drawText(empty_rect, Qt.AlignmentFlag.AlignCenter, "REMAINING UNPRINTED A4 AREA\n(208.1 mm Height — No Ink Printed Here)")


# ── Draw Cheque Leaf ──────────────────────────────────────────────────────────
chq_rect = QRectF(CHQ_LEFT, CHQ_TOP, CHQ_PX_W, CHQ_PX_H)

# Soft realistic cheque background tint (pale seafoam/mint)
painter.setPen(QPen(QColor("#0D9488"), 3))
painter.setBrush(QBrush(QColor("#ECFDF5")))
painter.drawRect(chq_rect)

# Cheque Guilloche / Security Border (faint inner border)
inner_border = QRectF(CHQ_LEFT + 8, CHQ_TOP + 8, CHQ_PX_W - 16, CHQ_PX_H - 16)
painter.setPen(QPen(QColor("#A7F3D0"), 1.5, Qt.PenStyle.DashLine))
painter.setBrush(Qt.BrushStyle.NoBrush)
painter.drawRect(inner_border)

# Bank Brand Watermark / Title
painter.setFont(QFont("Times New Roman", 20, QFont.Weight.Bold))
painter.setPen(QColor("#115E59"))
painter.drawText(QRectF(CHQ_LEFT + 110, CHQ_TOP + 25, 450, 40), Qt.AlignmentFlag.AlignLeft, "BANK OF CEYLON / SRI LANKA")

painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Normal))
painter.setPen(QColor("#0D9488"))
painter.drawText(QRectF(CHQ_LEFT + 110, CHQ_TOP + 65, 450, 30), Qt.AlignmentFlag.AlignLeft, "OFFICIAL CITS STANDARD (7.0\" × 3.5\" = 177.8 × 88.9 mm)")


# ── Draw Cheque Fields with Exact Coordinates ─────────────────────────────────

# 1. Date Boxes (DD  MM  YYYY)
# x = 121mm, 133.8mm, 146.6mm; y = 10.5mm
date_y = CHQ_TOP + 10.5 * SCALE
box_h = 10 * SCALE
box_w = 6.4 * SCALE
date_x_start = CHQ_LEFT + 121.0 * SCALE

# Date background label
painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
painter.setPen(QColor("#047857"))
painter.drawText(QRectF(date_x_start - 60, date_y - 25, 300, 25), Qt.AlignmentFlag.AlignLeft, "DATE: (y = 10.5 mm)")

date_digits = ["2", "4", "1", "0", "2", "0", "2", "6"]
for i, d in enumerate(date_digits):
    bx = date_x_start + i * box_w + (12 if i >= 2 else 0) + (12 if i >= 4 else 0)
    
    # Digit box
    painter.setPen(QPen(QColor("#059669"), 1.5))
    painter.setBrush(QBrush(QColor("#FFFFFF")))
    painter.drawRect(QRectF(bx, date_y, box_w, box_h))
    
    # Printed digit
    painter.setFont(QFont("Times New Roman", 18, QFont.Weight.Bold))
    painter.setPen(QColor("#0F172A"))
    painter.drawText(QRectF(bx, date_y, box_w, box_h), Qt.AlignmentFlag.AlignCenter, d)

# 2. Crossing Lines (x = 2mm, y = 4mm, w = 22mm, h = 26mm)
cross_x = CHQ_LEFT + 2.0 * SCALE
cross_y = CHQ_TOP + 4.0 * SCALE
painter.setPen(QPen(QColor("#0F172A"), 2.5))
painter.drawLine(QPointF(cross_x, cross_y + 90), QPointF(cross_x + 130, cross_y))
painter.drawLine(QPointF(cross_x + 35, cross_y + 110), QPointF(cross_x + 165, cross_y + 20))

painter.save()
painter.translate(cross_x + 65, cross_y + 55)
painter.rotate(-35)
painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
painter.setPen(QColor("#0F172A"))
painter.drawText(QRectF(-80, -10, 160, 20), Qt.AlignmentFlag.AlignCenter, "A/C PAYEE ONLY")
painter.restore()

# 3. Payee Field (x = 18mm, y = 25.5mm)
pay_x = CHQ_LEFT + 18.0 * SCALE
pay_y = CHQ_TOP + 25.5 * SCALE
painter.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
painter.setPen(QColor("#047857"))
painter.drawText(QRectF(pay_x, pay_y - 30, 220, 25), Qt.AlignmentFlag.AlignLeft, "PAY (x=18mm, y=25.5mm):")

# Payee text box & printed text
painter.setPen(QPen(QColor("#CBD5E1"), 1.5, Qt.PenStyle.DashLine))
painter.drawLine(QPointF(pay_x, pay_y + 28), QPointF(pay_x + 130 * SCALE, pay_y + 28))

painter.setFont(QFont("Times New Roman", 22, QFont.Weight.Normal))
painter.setPen(QColor("#0F172A"))
painter.drawText(QRectF(pay_x, pay_y - 5, 130 * SCALE, 40), Qt.AlignmentFlag.AlignLeft, "** SAMPATH BANDARA PERERA **")

# 4. Amount in Words (x = 18mm, y = 35.5mm & y = 42.5mm)
aw_x = CHQ_LEFT + 18.0 * SCALE
aw_y1 = CHQ_TOP + 35.5 * SCALE
aw_y2 = CHQ_TOP + 42.5 * SCALE

painter.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
painter.setPen(QColor("#047857"))
painter.drawText(QRectF(aw_x, aw_y1 - 25, 300, 25), Qt.AlignmentFlag.AlignLeft, "RUPEES IN WORDS (y=35.5mm & 42.5mm):")

painter.setPen(QPen(QColor("#CBD5E1"), 1.5, Qt.PenStyle.DashLine))
painter.drawLine(QPointF(aw_x, aw_y1 + 25), QPointF(aw_x + 93 * SCALE, aw_y1 + 25))
painter.drawLine(QPointF(aw_x, aw_y2 + 25), QPointF(aw_x + 93 * SCALE, aw_y2 + 25))

painter.setFont(QFont("Times New Roman", 18, QFont.Weight.Normal))
painter.setPen(QColor("#0F172A"))
painter.drawText(QRectF(aw_x, aw_y1 - 4, 93 * SCALE, 30), Qt.AlignmentFlag.AlignLeft, "** One Hundred Twenty Five Thousand Five Hundred")
painter.drawText(QRectF(aw_x, aw_y2 - 4, 93 * SCALE, 30), Qt.AlignmentFlag.AlignLeft, "and 50/100 Only **")

# 5. Amount Box (x = 114mm, y = 40.0mm, w = 56mm)
box_x = CHQ_LEFT + 114.0 * SCALE
box_y = CHQ_TOP + 40.0 * SCALE
box_w = 56.0 * SCALE
box_h = 16.0 * SCALE

painter.setPen(QPen(QColor("#0D9488"), 2))
painter.setBrush(QBrush(QColor("#FFFFFF")))
painter.drawRoundedRect(QRectF(box_x, box_y, box_w, box_h), 4, 4)

painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
painter.setPen(QColor("#047857"))
painter.drawText(QRectF(box_x + 10, box_y - 25, 200, 25), Qt.AlignmentFlag.AlignLeft, "Rs. BOX (x=114mm, y=40mm)")

painter.setFont(QFont("Times New Roman", 24, QFont.Weight.Bold))
painter.setPen(QColor("#0F172A"))
painter.drawText(QRectF(box_x, box_y, box_w, box_h), Qt.AlignmentFlag.AlignCenter, "** 125,500.50 **")

# 6. Bottom MICR Clearing Band (Standard 5/8" = 15.9mm band at bottom)
micr_y = CHQ_TOP + (CHQ_MM_H - 15.9) * SCALE
painter.setPen(QPen(QColor("#CBD5E1"), 1, Qt.PenStyle.DotLine))
painter.drawLine(QPointF(CHQ_LEFT + 8, micr_y), QPointF(CHQ_LEFT + CHQ_PX_W - 8, micr_y))
painter.setFont(QFont("Consolas", 11, QFont.Weight.Normal))
painter.setPen(QColor("#64748B"))
painter.drawText(QRectF(CHQ_LEFT + 20, micr_y + 10, CHQ_PX_W - 40, 25), Qt.AlignmentFlag.AlignCenter, "⑈ 123456 ⑈  7010⑉001⑈  0012345678 ⑈  20")


# ── Draw Dimension Lines & Millimeter Annotations ─────────────────────────────

# TOP HORIZONTAL DIMENSIONS
dim_y_top = A4_TOP - 60
dim_y_sub = A4_TOP - 20

# 1. Full A4 Width (210 mm)
draw_dim_h(painter, A4_LEFT, A4_LEFT + A4_PX_W, dim_y_top, "FULL A4 WIDTH: 210.0 mm", color=QColor("#38BDF8"), font_size=18)

# 2. Left Margin (16.1 mm)
draw_dim_h(painter, A4_LEFT, CHQ_LEFT, dim_y_sub, "16.1 mm", color=QColor("#F59E0B"), font_size=14)

# 3. Cheque Width (177.8 mm / 7.0")
draw_dim_h(painter, CHQ_LEFT, CHQ_LEFT + CHQ_PX_W, dim_y_sub, "CHEQUE WIDTH: 177.8 mm (7.00\")", color=QColor("#10B981"), font_size=15)

# 4. Right Margin (16.1 mm)
draw_dim_h(painter, CHQ_LEFT + CHQ_PX_W, A4_LEFT + A4_PX_W, dim_y_sub, "16.1 mm", color=QColor("#F59E0B"), font_size=14)


# VERTICAL DIMENSIONS (LEFT SIDE OF A4)
dim_x_left = A4_LEFT - 70
dim_x_outer = A4_LEFT - 140

# 1. Cheque Height (88.9 mm / 3.5")
draw_dim_v(painter, CHQ_TOP, CHQ_TOP + CHQ_PX_H, dim_x_left, "88.9 mm (3.50\")", color=QColor("#10B981"), font_size=14)

# 2. Remaining Empty A4 Height (208.1 mm)
draw_dim_v(painter, CHQ_TOP + CHQ_PX_H, A4_TOP + A4_PX_H, dim_x_left, "208.1 mm (Unused A4)", color=QColor("#94A3B8"), font_size=14)

# 3. Total A4 Height (297 mm)
draw_dim_v(painter, A4_TOP, A4_TOP + A4_PX_H, dim_x_outer, "FULL A4 HEIGHT: 297.0 mm", color=QColor("#38BDF8"), font_size=18)


# ── Draw Physical Printer Guides (Plastic Sliders) Illustration ───────────────
guide_w = 40
guide_h = 90
slider_color = QColor("#F59E0B")

# Left guide
left_guide_rect = QRectF(CHQ_LEFT - guide_w, A4_TOP - 10, guide_w, guide_h)
painter.setPen(QPen(QColor("#D97706"), 2))
painter.setBrush(QBrush(slider_color))
painter.drawRoundedRect(left_guide_rect, 6, 6)

# Right guide
right_guide_rect = QRectF(CHQ_LEFT + CHQ_PX_W, A4_TOP - 10, guide_w, guide_h)
painter.drawRoundedRect(right_guide_rect, 6, 6)

painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
painter.setPen(QColor("#78350F"))
painter.drawText(left_guide_rect, Qt.AlignmentFlag.AlignCenter, "TRAY\nGUIDE")
painter.drawText(right_guide_rect, Qt.AlignmentFlag.AlignCenter, "TRAY\nGUIDE")

# Arrows indicating sliders clamping inward
draw_arrow(painter, QPointF(A4_LEFT + 20, A4_TOP + 35), QPointF(CHQ_LEFT - 5, A4_TOP + 35), arrow_size=10, color=QColor("#F59E0B"), width=2)
draw_arrow(painter, QPointF(A4_LEFT + A4_PX_W - 20, A4_TOP + 35), QPointF(CHQ_LEFT + CHQ_PX_W + 5, A4_TOP + 35), arrow_size=10, color=QColor("#F59E0B"), width=2)


# ── RIGHT SIDE: Technical Specifications & Instructions Card ───────────────────
card_x = A4_LEFT + A4_PX_W + 90
card_y = A4_TOP - 160
card_w = IMG_W - card_x - 100
card_h = A4_PX_H + 160

# Background Card
painter.setPen(QPen(QColor("#334155"), 2))
painter.setBrush(QBrush(QColor("#1E293B")))
painter.drawRoundedRect(QRectF(card_x, card_y, card_w, card_h), 12, 12)

# Card Header
painter.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
painter.setPen(QColor("#F8FAFC"))
painter.drawText(QRectF(card_x + 35, card_y + 35, card_w - 70, 40), Qt.AlignmentFlag.AlignLeft, "ENGINEERING SPECIFICATION")

painter.setPen(QPen(QColor("#475569"), 1.5))
painter.drawLine(QPointF(card_x + 35, card_y + 90), QPointF(card_x + card_w - 35, card_y + 90))

# Section 1: The Core Formula
painter.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
painter.setPen(QColor("#38BDF8"))
painter.drawText(QRectF(card_x + 35, card_y + 115, card_w - 70, 30), Qt.AlignmentFlag.AlignLeft, "1. OFFICIAL CITS CENTER-FEED MATHEMATICS")

math_box = QRectF(card_x + 35, card_y + 155, card_w - 70, 125)
painter.setPen(QPen(QColor("#0284C7"), 1.5))
painter.setBrush(QBrush(QColor("#0F172A")))
painter.drawRoundedRect(math_box, 8, 8)

painter.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
painter.setPen(QColor("#E2E8F0"))
painter.drawText(QRectF(card_x + 55, card_y + 168, card_w - 110, 100), Qt.AlignmentFlag.AlignLeft, 
    "A4 Sheet Width     = 210.0 mm\n"
    "Cheque Length      = 7.00 inches = 177.8 mm (~178 mm)\n"
    "Cheque Height      = 3.50 inches =  88.9 mm (~89 mm)\n"
    "Left Tray Margin   = (210.0 - 177.8) / 2 = 16.1 mm\n"
    "Top Tray Margin    = 0.0 mm (Leading Edge)"
)

# Section 2: Coordinate Mapping Table
painter.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
painter.setPen(QColor("#10B981"))
painter.drawText(QRectF(card_x + 35, card_y + 310, card_w - 70, 30), Qt.AlignmentFlag.AlignLeft, "2. FIELD COORDINATES (CHEQUE vs A4)")

table_top = card_y + 355
row_h = 48
col_w = [180, 150, 150]

headers = ["Field Name", "Cheque (X, Y)", "A4 Page (X, Y)"]
painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
painter.setPen(QColor("#94A3B8"))
for ci, h in enumerate(headers):
    painter.drawText(QRectF(card_x + 40 + sum(col_w[:ci]), table_top, col_w[ci], 30), Qt.AlignmentFlag.AlignLeft, h)

painter.setPen(QPen(QColor("#475569"), 1))
painter.drawLine(QPointF(card_x + 35, table_top + 32), QPointF(card_x + card_w - 35, table_top + 32))

table_data = [
    ("Date (DD)", "121.0, 10.5 mm", "137.1, 10.5 mm"),
    ("Date (MM)", "133.8, 10.5 mm", "149.9, 10.5 mm"),
    ("Date (YYYY)", "146.6, 10.5 mm", "162.7, 10.5 mm"),
    ("Payee Name", "18.0, 25.5 mm", "34.1, 25.5 mm"),
    ("Amount in Words (L1)", "18.0, 35.5 mm", "34.1, 35.5 mm"),
    ("Amount in Words (L2)", "18.0, 42.5 mm", "34.1, 42.5 mm"),
    ("Numeric Amount Box", "114.0, 40.0 mm", "130.1, 40.0 mm"),
    ("Crossing Stamp", "2.0, 4.0 mm", "18.1, 4.0 mm"),
]

for ri, (name, chq_coord, a4_coord) in enumerate(table_data):
    ry = table_top + 45 + ri * row_h
    # alternating row highlight
    if ri % 2 == 1:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 8)))
        painter.drawRect(QRectF(card_x + 35, ry - 8, card_w - 70, row_h))
        
    painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
    painter.setPen(QColor("#F1F5F9"))
    painter.drawText(QRectF(card_x + 40, ry, col_w[0], 30), Qt.AlignmentFlag.AlignLeft, name)
    
    painter.setFont(QFont("Consolas", 13, QFont.Weight.Normal))
    painter.setPen(QColor("#94A3B8"))
    painter.drawText(QRectF(card_x + 40 + col_w[0], ry, col_w[1], 30), Qt.AlignmentFlag.AlignLeft, chq_coord)
    
    painter.setPen(QColor("#38BDF8"))
    painter.drawText(QRectF(card_x + 40 + col_w[0] + col_w[1], ry, col_w[2], 30), Qt.AlignmentFlag.AlignLeft, a4_coord)

# Section 3: Physical Loading Guide
guide_top = table_top + 45 + len(table_data) * row_h + 30
painter.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
painter.setPen(QColor("#F59E0B"))
painter.drawText(QRectF(card_x + 35, guide_top, card_w - 70, 30), Qt.AlignmentFlag.AlignLeft, "3. HOW TO INSERT CHEQUE IN PRINTER")

instructions = [
    ("1. Exact Standard", "Sri Lanka CBSL / LankaPay CITS standard: 7.0\" × 3.5\" (177.8 × 88.9 mm)."),
    ("2. Orientation", "Feed the cheque horizontally (177.8 mm width entering first). Do NOT rotate vertically."),
    ("3. Right Side Up", "Face the cheque printing side up (or as required by your printer's tray model)."),
    ("4. Center Guides", "Push the left and right plastic tray guides snugly against the cheque edges at 16.1 mm."),
    ("5. Universal Spooling", "Because the computer sends an A4 job, any printer will accept it without size error!"),
    ("6. Offset Nudge", "Use the app's +/- mm shift boxes to calibrate any tiny printer tray roller mechanical bias.")
]

for ii, (step, desc) in enumerate(instructions):
    iy = guide_top + 45 + ii * 60
    painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    painter.setPen(QColor("#FCD34D"))
    painter.drawText(QRectF(card_x + 40, iy, card_w - 80, 22), Qt.AlignmentFlag.AlignLeft, step)
    
    painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Normal))
    painter.setPen(QColor("#CBD5E1"))
    painter.drawText(QRectF(card_x + 40, iy + 22, card_w - 80, 32), Qt.AlignmentFlag.AlignLeft, desc)

# Section 4: Why this solves all client machines
benefit_top = guide_top + 45 + len(instructions) * 60 + 25
benefit_box = QRectF(card_x + 35, benefit_top, card_w - 70, 155)
painter.setPen(QPen(QColor("#059669"), 1.5))
painter.setBrush(QBrush(QColor("#064E3B")))
painter.drawRoundedRect(benefit_box, 8, 8)

painter.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
painter.setPen(QColor("#A7F3D0"))
painter.drawText(QRectF(card_x + 55, benefit_top + 18, card_w - 110, 28), Qt.AlignmentFlag.AlignLeft, "✓ UNIVERSAL COMPATIBILITY GUARANTEE")

painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Normal))
painter.setPen(QColor("#E2E8F0"))
painter.drawText(QRectF(card_x + 55, benefit_top + 50, card_w - 110, 90), Qt.AlignmentFlag.AlignLeft,
    "• Zero Windows 'Print Server Properties' form creation needed.\n"
    "• Zero 'Custom Paper Size Not Supported' errors on HP, Epson, Canon.\n"
    "• Works identically from SumatraPDF silent print or standard Web Browser!"
)

# ── Footer / Credits ──────────────────────────────────────────────────────────
painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Normal))
painter.setPen(QColor("#64748B"))
painter.drawText(QRectF(100, IMG_H - 80, 2200, 30), Qt.AlignmentFlag.AlignLeft,
    "Generated for Sri Lankan Bank Cheque Writer • Growvia Solutions & Dev IMS • Official LankaPay CITS Standard (7.0\" × 3.5\")"
)

painter.end()

out_path = r"C:\Users\Ishan\.gemini\antigravity\brain\e0294bfa-412e-40f2-960b-6c8055898383\cheque_a4_measurements.png"
img.save(out_path)
print(f"Successfully generated diagram at: {out_path}")
