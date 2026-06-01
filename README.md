# Sri Lankan Bank Cheque Writer

A lightweight, professional desktop application built with Python and PyQt6 to print cheques for Sri Lankan banks.

## Overview
Writing bank cheques manually can lead to spelling mistakes, incorrect date formatting, and poor readability. This application automates the process by generating perfectly formatted cheque printouts, utilizing custom layouts for major Sri Lankan banks.

## Key Features
- **Multiple Bank Layouts**: Pre-configured support for Bank of Ceylon (BOC), Hatton National Bank (HNB), and Seylan Bank. Custom JSON configurations allow easily adding new banks.
- **Automatic Amount to Words**: Translates numeric amounts (e.g. `1500.50`) into standard cheque words automatically (e.g. `**One Thousand Five Hundred and Cents Fifty Only**`).
- **Live Payee Autocomplete**: Uses a local SQLite database to save payee names and autocomplete them as you type, sorted by frequency of use.
- **Interactive Print Alignment**: Provides horizontal and vertical alignment offset settings in millimeters directly in the UI to correct printer tray feeding issues. Saved persistently using registry settings.
- **Reliable Browser Printing**: Bypasses unstable printer-driver APIs and crashes by compiling the cheque into a PDF and opening it in your default web browser for print preview and submission.
- **Standalone Executable**: Compiles into a single `dist/ChequeWriter.exe` that runs on any Windows PC without Python or PyQt6 installed.

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

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

## Standalone Executable
To build a single-file executable that does not require Python or PyQt6 installed on target PCs:
```bash
pyinstaller ChequeWriter.spec
```
The output binary will be created at `dist/ChequeWriter.exe`.

## Configuration
### Bank Layout Specifications
Each bank's cheque template is defined in a JSON file inside the `banks/` folder. All coordinate units are in millimeters (mm):
- `cheque_width_mm` / `cheque_height_mm`: Dimensions of the physical cheque.
- `year_digits`: Number of digits to print for the year (e.g. 2 for `26`, 4 for `2026`).
- `fields`: Positioning parameters for:
  - `date_dd` / `date_mm` / `date_yyyy`: Individual boxes for date digits.
  - `payee`: Coordinates and width limits for the payee name.
  - `amount_box`: Coordinates and width limits for the numeric amount.
  - `amount_words` / `amount_words_line2`: Text coordinates for amount-in-words lines.
  - `cross_x` / `cross_y`: Parameters for cheque crossing line origins.

## Alignment Offsets (Registry Settings)
If text is shifted when printed on paper:
- Adjust the **Vertical Shift** (negative values shift text up; positive values shift text down).
- Adjust the **Horizontal Shift** (negative values shift text left; positive values shift text right).
- These configurations are saved automatically to `HKEY_CURRENT_USER\Software\Growvia\ChequeWriter` on Windows.

## Browser Print Settings
When printing the cheque PDF from your default browser, ensure the following settings are selected for perfect alignment:
1. **Margins**: Set to **None** or **Minimum**.
2. **Scale**: Set to **100%** (or Default). Do not select 'Fit to Page'.
3. **Headers & Footers**: Ensure this checkbox is **unchecked** to avoid URLs or page numbers printing on the cheque.
4. **Layout**: Set to **Landscape**.

## File Architecture
- `main.py`: Core GUI layout, event handling, PDF generator, and window coordinates offset logic.
- `payee_db.py`: SQLite backend interface for tracking payee frequency history.
- `amount_words.py`: Algorithmic parser to translate amounts into English words.
- `banks/`: JSON template layouts for supported banks.
- `ChequeWriter.spec`: PyInstaller script containing packaging data.
- `run.bat`: Quick execution batch file.

## SQLite Payees Database Schema
The autocomplete system uses a table called `payees`:
```sql
CREATE TABLE IF NOT EXISTS payees (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL COLLATE NOCASE,
    used_count INTEGER DEFAULT 1,
    last_used TEXT DEFAULT (date('now'))
);
```

## Security Standards
