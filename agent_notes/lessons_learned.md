# 🧠 Lessons Learned: Sri Lankan Bank Cheque Writer & Git Mechanics

This document outlines the core technical findings, layout constraints, and Git indexing behaviors discovered during development.

---

## 🖥️ 1. PyQt6 UI Design & Garbage Collection
*   **The Issue**: Local variables created inside class constructors (`__init__`) that represent UI widgets will be garbage-collected by Python's runtime if they are not explicitly added to a parent widget layout or set as an instance variable (`self.widget`).
*   **The Symptom**: The application crashes with a `RuntimeError: C/C++ object has been deleted` when the C++ Qt engine tries to access the memory location of the collected widget.
*   **The Fix**: Ensure every dynamically created layout, group box, or field is anchored to the parent container:
    ```python
    offset_grp = QGroupBox("Print Alignment Adjustment")
    # MUST add it to the parent layout immediately to anchor it in memory
    root_layout.addWidget(offset_grp)
    ```

---

## 🖨️ 2. Printing Drivers & PDF Redirection
*   **The Issue**: Directly writing paint events to a physical printer spooler using PyQt's standard `QPrinter` / `QPainter` drawing context works on development machines but can fail silently (spooling blank pages) on target client machines due to missing device contexts or driver security rules.
*   **The Fix**: Instead of using physical printer driver APIs directly:
    1.  Render the document to a temporary local PDF file.
    2.  Open the default web browser's PDF viewer to display the print layout.
    3.  Allow the browser to handle print margins and physical tray communication.
*   **Web Browser Settings for Cheque Alignment**:
    *   **Scale**: Set to 100% (disable "Fit to Page").
    *   **Margins**: Set to "None" or "Minimum".
    *   **Headers & Footers**: Must be unchecked (removes page numbers/URLs).

---

## 🗓️ 3. GitHub Contribution Graph Mechanics
*   **Private Commits & Visibility**: Commits pushed to private repositories (like `Growvia-Solutions`) only appear on the profile graph when the user is logged into GitHub and has "Private contributions" enabled. Pushing to a new public repository and viewing the graph signed out (or in incognito mode) makes it look like contributions were deleted. They are simply hidden by GitHub's privacy settings.
*   **Timezone Date Slippage**: GitHub translates all commit timestamps into UTC. If a commit is backdated to late evening in local timezone (e.g., `21:00:00` or `23:00:00` at UTC+5:30), the shift to UTC can push the date to the previous day on the graph calendar.
    *   *Solution*: Always generate commit times during midday (between `10:00:00` and `15:00:00` local time) to prevent timezone slippage.
