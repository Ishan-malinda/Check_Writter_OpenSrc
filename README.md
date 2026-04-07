# Sri Lankan Bank Cheque Writer

A lightweight, professional desktop application built with Python and PyQt6 to print cheques for Sri Lankan banks.

## Overview
Writing bank cheques manually can lead to spelling mistakes, incorrect date formatting, and poor readability. This application automates the process by generating perfectly formatted cheque printouts, utilizing custom layouts for major Sri Lankan banks.

## Key Features
- **Multiple Bank Layouts**: Pre-configured support for Bank of Ceylon (BOC), Hatton National Bank (HNB), and Seylan Bank. Custom JSON configurations allow easily adding new banks.
- **Automatic Amount to Words**: Translates numeric amounts (e.g. `1500.50`) into standard cheque words automatically (e.g. `**One Thousand Five Hundred and Cents Fifty Only**`).
- **Live Payee Autocomplete**: Uses a local SQLite database to save payee names and autocomplete them as you type, sorted by frequency of use.
- **Interactive Print Alignment**: Provides horizontal and vertical alignment offset settings in millimeters directly in the UI to correct printer tray feeding issues. Saved persistently using registry settings.
