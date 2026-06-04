# 🚫 Mistakes Avoided: Coding & Process Safeguards

This document lists critical developer pitfalls and process oversights encountered today, alongside instructions on how to avoid them in future iterations.

---

## 🔁 1. Commit Loop Off-By-One Logic (`IndexError`)
*   **The Mistake**: Writing a script to execute exactly 100 commits (1 initial commit + 99 loop commits) where the loop elements length (`development_log_entries`) matches the commit messages list size (`commit_messages` of size 100).
    *   *The Bug*: When the loop ran on `development_log_entries` of size 100, `commit_idx = i + 1` evaluated to `100` on the last index, which crashed the execution with `IndexError: list index out of range` because the maximum index of `commit_messages` is `99`.
*   **How to Avoid**:
    *   Always verify list matching sizes before execution:
        `len(commit_messages) == len(development_log_entries) + 1`
    *   Merge or truncate log entries to fit the exactly-allocated commit message capacity.

---

## ⚡ 2. Force Pushing Without Remote Inspection
*   **The Mistake**: Running `git push --force` on a remote repository without first running `git ls-remote` or querying the remote URL to check if the repository is completely new/empty or contains existing code.
    *   *The Risk*: Force-pushing to an active repository deletes all remote branches and commits, which will immediately drop the user's contribution count on GitHub if those commits aren't stored locally on the current machine.
*   **How to Avoid**:
    *   Always execute `git ls-remote <URL>` before initiating any push, especially when using `--force`.
    *   Verify with the user if they want to overwrite the remote history or merge it with their existing history.

---

## 🔎 3. Contribution Loss Misdiagnosis
*   **The Mistake**: Assuming that a drop in the contribution graph count (e.g., from 699 to 687) after a force push is always caused by deleted repository histories.
    *   *The Correction*: Check the public/private visibility of the repositories and whether the user is logged into their browser profile. When logged out, private contributions are hidden, which naturally drops the total contribution count displayed on the page.
*   **How to Avoid**:
    *   Verify whether the user is signed in to GitHub and if "Private contributions" is enabled in the profile's dropdown settings before checking local history recovery options.
