# Growvia Cheque Writer (Universal A4)

A lightweight, professional desktop application built with Python and PyQt6 to print cheques for Sri Lankan banks with **universal printer compatibility** via standard A4 feed logic.

## Overview
Writing bank cheques manually can lead to spelling mistakes, incorrect date formatting, and poor readability. **Growvia Cheque Writer** automates the process by generating perfectly formatted cheque printouts, utilizing standard layouts for major Sri Lankan banks adhering strictly to Central Bank of Sri Lanka (CBSL) and LankaPay CITS regulations.

## Key Features
- **Universal A4 Printing**: Eliminates paper mismatch errors and the need to register custom forms in Windows `Print Server Properties`. Prints as standard A4 with automatic center-feed (16.1 mm margins) or left-feed placement.
- **Official CITS Dimensions**: Standardized to the official Sri Lankan banking size: **7.00" × 3.50" (177.8 × 88.9 mm)**.
- **Multiple Bank Layouts**: Pre-configured support for:
  - Bank of Ceylon (BOC)
  - Commercial Bank of Ceylon (COMBANK)
  - Hatton National Bank (HNB)
  - Sampath Bank (SAMPATH)
  - Seylan Bank (Seylan)
- **Live On-Screen Visual Preview**: Real-time rendering canvas inside the application displaying exact text, amount, crossing stamps, and placement. Toggle between Zoomed Cheque view and full A4 Paper view.
- **Passcode-Protected Settings (`0000`)**: Administrative settings (paper feed, print alignment offsets, date fine-tuning, and year format) are safely locked behind **`🔒 More Options`** with a simple passcode.
- **Smart 3-Line Word Wrapping**: Amounts in words automatically flow across up to 3 lines at full, uniform font size without shrinking or colliding with the price box.
- **Native Direct 1-Click Print**: Sends print jobs directly to your selected Windows printer without requiring external software. Includes dedicated PDF preview for optional digital verification.
- **Plain Paper Alignment Test**: Print a test page on plain A4 paper with dashed cheque outlines to overlay over a physical cheque leaf against a light source for zero-waste calibration.
- **Automatic Amount to Words**: Translates numeric amounts (e.g. `1500.50`) into standard cheque words automatically (e.g. `**One Thousand Five Hundred and 50/100 Only**`).
- **Live Payee Autocomplete**: Uses a local SQLite database to save payee names and autocomplete them as you type, sorted by frequency of use.
- **2-Digit / 4-Digit Year Support**: Defaults to 2 digits (`'26`) to preserve pre-printed `20` on Sri Lankan bank cheques, with toggleable 4-digit support.

## Tech Stack
- **Programming Language**: Python 3
- **GUI Framework**: PyQt6
- **Database**: SQLite3
- **Layout Engine**: QPrinter & QPainter (Qt Graphics Framework)

## Installation
To run the application from source, you need Python installed on your system.

1. Clone this repository:
```bash
git clone https://github.com/Ishan-malinda/Check_Writter_OpenSrc.git
cd Check_Writter_OpenSrc
```

2. Set up virtual environment and install dependencies:
```bash
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

3. Run the application:
```bash
run.bat
```
or
```bash
.\.venv\Scripts\python main.py
```

## A4 Cheque Printing Mathematics

```
                  ◄─── 210.0 mm (A4 Width) ───►
      ┌─────────────────────────────────────────────────┐
      │          ◄── 177.8 mm (Cheque) ──►              │
      │ 16.1 mm  ┌─────────────────────┐    16.1 mm     │
      │  margin  │ Bank Cheque Leaf    │     margin     │
      │          │ Payee: *********    │                │
      │          │ Amount: *********   │                │
      │          └─────────────────────┘                │
      │                                                 │
      │                  A4 Page                        │
      │                (297.0 mm tall)                  │
      │                                                 │
      └─────────────────────────────────────────────────┘
```

- **A4 Sheet Dimensions**: 210.0 × 297.0 mm
- **Cheque Dimensions**: 177.8 × 88.9 mm (7.00" × 3.50")
- **Left / Right Tray Margin**: $\frac{210.0 - 177.8}{2} = \mathbf{16.1\text{ mm}}$
- **Top Margin**: $\mathbf{0.0\text{ mm}}$ (leading edge enters printer first)

## Paper Modes Supported
1. **A4 - Center Feed (Standard / Recommended)**: Fits 90%+ of consumer and office desktop printers (Epson EcoTank L-series, Canon Pixma/MegaTank, HP SmartTank/LaserJet, Xerox WorkCentre). Insert cheque in center and adjust tray guides.
2. **A4 - Left-Aligned Feed**: For printers with fixed left tray guides.
3. **Custom Cheque Size (178 × 89 mm)**: Legacy mode for specialized cheque slip printers or custom Windows form configurations.

## Contributing
Contributions are welcome! If you have updates to add a new bank layout configuration, create a JSON configuration inside the `banks/` folder and open a Pull Request.

## License
This project is open-source and released under the MIT License. See [LICENSE](LICENSE) for details.

## Credits
Developed by Growvia Solutions & Dev IMS. Copyright 2026. All rights reserved.
