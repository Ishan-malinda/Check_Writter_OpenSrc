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
