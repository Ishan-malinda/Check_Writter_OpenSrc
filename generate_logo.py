"""Generate professional high-resolution application icon and multi-size Windows .ico for Growvia Cheque Writer."""

import struct
from io import BytesIO
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import (
    QImage, QPainter, QPainterPath, QLinearGradient, QColor,
    QBrush, QPen, QFont
)
from PyQt6.QtCore import Qt, QRectF, QPointF

def create_logo(size=512) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)

    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    scale = size / 512.0

    # 1. Base Squircle / Rounded App Badge
    # Modern deep navy to oceanic blue gradient
    margin = 24.0 * scale
    badge_rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    radius = 100.0 * scale

    bg_path = QPainterPath()
    bg_path.addRoundedRect(badge_rect, radius, radius)

    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor("#0A192F"))   # Deep rich navy
    grad.setColorAt(0.5, QColor("#0F355C"))   # Oceanic royal blue
    grad.setColorAt(1.0, QColor("#0284C7"))   # Modern vibrant cyan-blue

    painter.fillPath(bg_path, QBrush(grad))

    # Inner Glow / Border
    pen_glow = QPen(QColor(255, 255, 255, 45), 2.5 * scale)
    painter.strokePath(bg_path, pen_glow)

    # 2. Subtle Background Grid/Accent lines for Financial Security feel
    grid_pen = QPen(QColor(255, 255, 255, 12), 1.5 * scale)
    painter.setPen(grid_pen)
    for i in range(4):
        y_pos = (120 + i * 70) * scale
        painter.drawLine(QPointF(60 * scale, y_pos), QPointF(452 * scale, y_pos))

    # 3. Main Cheque Slip (Angled slightly or centered with soft drop-shadow)
    # Drop shadow
    shadow_path = QPainterPath()
    shadow_rect = QRectF(78 * scale, 138 * scale, 356 * scale, 210 * scale)
    shadow_path.addRoundedRect(shadow_rect, 18 * scale, 18 * scale)
    painter.fillPath(shadow_path, QBrush(QColor(0, 0, 0, 70)))

    # Cheque Surface (Crisp warm white)
    cheque_rect = QRectF(76 * scale, 132 * scale, 356 * scale, 210 * scale)
    cheque_path = QPainterPath()
    cheque_path.addRoundedRect(cheque_rect, 18 * scale, 18 * scale)
    painter.fillPath(cheque_path, QBrush(QColor("#FFFFFF")))

    # Cheque border
    cheque_border = QPen(QColor("#CBD5E1"), 1.8 * scale)
    painter.strokePath(cheque_path, cheque_border)

    # 4. Cheque Details:
    # A. Top Left Double Crossing Lines ("//")
    cross_pen = QPen(QColor("#0284C7"), 3.5 * scale)
    painter.setPen(cross_pen)
    painter.drawLine(QPointF(92 * scale, 168 * scale), QPointF(128 * scale, 134 * scale))
    painter.drawLine(QPointF(104 * scale, 168 * scale), QPointF(140 * scale, 134 * scale))

    # B. Bank Header Accent Band
    band_path = QPainterPath()
    band_path.addRoundedRect(QRectF(150 * scale, 146 * scale, 110 * scale, 14 * scale), 4 * scale, 4 * scale)
    painter.fillPath(band_path, QBrush(QColor("#E0F2FE")))

    # C. Date boxes (Top Right)
    box_pen = QPen(QColor("#94A3B8"), 1.5 * scale)
    painter.setPen(box_pen)
    for b in range(6):
        b_x = (320 + b * 16) * scale
        painter.drawRoundedRect(QRectF(b_x, 144 * scale, 13 * scale, 16 * scale), 2 * scale, 2 * scale)

    # D. "PAY" label & Payee Line
    painter.setPen(QPen(QColor("#64748B"), 1.5 * scale))
    font_pay = QFont("Segoe UI", int(11 * scale), QFont.Weight.Bold)
    painter.setFont(font_pay)
    painter.drawText(QPointF(98 * scale, 196 * scale), "PAY")

    # Payee line
    payee_line_pen = QPen(QColor("#94A3B8"), 2.2 * scale)
    painter.setPen(payee_line_pen)
    painter.drawLine(QPointF(134 * scale, 194 * scale), QPointF(320 * scale, 194 * scale))

    # E. Amount Words lines
    words_pen = QPen(QColor("#CBD5E1"), 2.0 * scale)
    painter.setPen(words_pen)
    painter.drawLine(QPointF(98 * scale, 226 * scale), QPointF(300 * scale, 226 * scale))
    painter.drawLine(QPointF(98 * scale, 252 * scale), QPointF(240 * scale, 252 * scale))

    # F. Amount Box (Right Side)
    amt_box = QRectF(305 * scale, 210 * scale, 112 * scale, 46 * scale)
    amt_path = QPainterPath()
    amt_path.addRoundedRect(amt_box, 8 * scale, 8 * scale)
    painter.fillPath(amt_path, QBrush(QColor("#F0FDF4")))
    painter.strokePath(amt_path, QPen(QColor("#22C55E"), 2.0 * scale))

    # Currency text inside amount box
    amt_font = QFont("Segoe UI", int(14 * scale), QFont.Weight.Bold)
    painter.setFont(amt_font)
    painter.setPen(QColor("#15803D"))
    painter.drawText(amt_box, Qt.AlignmentFlag.AlignCenter, "Rs. ***")

    # G. Security MICR band at bottom of cheque
    micr_rect = QRectF(92 * scale, 298 * scale, 250 * scale, 16 * scale)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.fillPath(amt_path, QBrush(QColor("#F0FDF4")))
    micr_pen = QPen(QColor("#CBD5E1"), 1.8 * scale, Qt.PenStyle.DashLine)
    painter.setPen(micr_pen)
    painter.drawLine(QPointF(96 * scale, 310 * scale), QPointF(280 * scale, 310 * scale))

    # 5. Vibrant Growth/Verification Badge (Emerald circle with white checkmark)
    # Positioned at bottom right corner overlapping the cheque
    badge_cx = 370.0 * scale
    badge_cy = 345.0 * scale
    badge_r = 54.0 * scale

    # Badge Shadow
    b_shadow = QPainterPath()
    b_shadow.addEllipse(QPointF(badge_cx + 2 * scale, badge_cy + 4 * scale), badge_r, badge_r)
    painter.fillPath(b_shadow, QBrush(QColor(0, 0, 0, 90)))

    # Badge Gradient (Emerald to Mint)
    b_circle = QPainterPath()
    b_circle.addEllipse(QPointF(badge_cx, badge_cy), badge_r, badge_r)
    b_grad = QLinearGradient(badge_cx - badge_r, badge_cy - badge_r, badge_cx + badge_r, badge_cy + badge_r)
    b_grad.setColorAt(0.0, QColor("#10B981"))
    b_grad.setColorAt(1.0, QColor("#047857"))
    painter.fillPath(b_circle, QBrush(b_grad))

    # Badge Border
    painter.strokePath(b_circle, QPen(QColor(255, 255, 255, 220), 3.5 * scale))

    # Crisp Checkmark inside badge
    check_path = QPainterPath()
    # Coordinates relative to badge center
    check_path.moveTo(QPointF(badge_cx - 20 * scale, badge_cy + 1 * scale))
    check_path.lineTo(QPointF(badge_cx - 6 * scale, badge_cy + 16 * scale))
    check_path.lineTo(QPointF(badge_cx + 22 * scale, badge_cy - 16 * scale))

    check_pen = QPen(QColor("#FFFFFF"), 7.0 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.strokePath(check_path, check_pen)

    painter.end()
    return img


def save_ico_multi(png_images: list[tuple[int, bytes]], out_path: Path):
    """
    Save multiple PNG resolutions into a single Windows .ico file.
    Each element in png_images is (size, png_bytes).
    """
    count = len(png_images)
    header = struct.pack("<HHH", 0, 1, count)
    
    entries = []
    offset = 6 + count * 16  # header (6) + entries (16 each)
    
    for size, data in png_images:
        w = size if size < 256 else 0
        h = size if size < 256 else 0
        bytes_in_res = len(data)
        # bWidth, bHeight, bColorCount, bReserved, wPlanes, wBitCount, dwBytesInRes, dwImageOffset
        entry = struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, bytes_in_res, offset)
        entries.append(entry)
        offset += bytes_in_res

    with open(out_path, "wb") as f:
        f.write(header)
        for entry in entries:
            f.write(entry)
        for _, data in png_images:
            f.write(data)


def main():
    app = QApplication.instance() or QApplication([])

    # High-res base logo (512x512)
    logo_512 = create_logo(512)
    out_png = Path("icon.png")
    logo_512.save(str(out_png), "PNG")
    print(f"Saved {out_png} ({out_png.stat().st_size} bytes)")

    # Multi-resolution ICO (256, 128, 64, 48, 32, 24, 16)
    sizes = [256, 128, 64, 48, 32, 24, 16]
    png_list = []
    for s in sizes:
        scaled = logo_512.scaled(s, s, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        from PyQt6.QtCore import QBuffer, QIODevice
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        scaled.save(buf, "PNG")
        png_list.append((s, bytes(buf.data())))

    out_ico = Path("icon.ico")
    save_ico_multi(png_list, out_ico)
    print(f"Saved {out_ico} ({out_ico.stat().st_size} bytes) with sizes: {sizes}")

if __name__ == "__main__":
    main()
