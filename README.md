# Kantata (Kimble) Timesheet Automation PoC

This project contains a Proof of Concept (PoC) for automating timesheet entries on the Kantata Salesforce page.

## Prerequisites

- Python 3.8+
- Playwright

## Setup

1. Install dependencies:
   ```powershell
   pip install playwright
   playwright install chromium
   ```

2. The scripts use a persistent user data directory (`user_data/`) to store your login session. This means you only need to log in manually once.

## Running in PyCharm

I have added Run Configurations for PyCharm. You should now see "Inspect Elements" and "PoC Timesheet" in the dropdown menu at the top right of your IDE.

1.  **Select the configuration**: Choose either "Inspect Elements" or "PoC Timesheet" from the dropdown.
2.  **Run**: Click the green "Run" button (triangle icon) or press `Shift + F10`.

This will automatically use the project's virtual environment and the correct scripts.

## Manual Usage (Command Line)

### 1. Element Inspection Tool
Use this script to identify the selectors (IDs, Classes, Names) for the UI elements on the Kantata page.

```powershell
python inspect_elements.py
```
- It will open the Salesforce page.
- Log in manually if prompted.
- The script will scan the page and all iframes every 10 seconds, printing found buttons and inputs to the console.
- It also saves these findings to `elements_log.txt` in the project root for easy copying.
- Use this information to update the automation script with correct selectors.

### 2. Basic Automation PoC
A template script that navigates to the timesheet and takes a screenshot.

```powershell
python poc_timesheet.py
```

## Next Steps

Once you have identified the selectors for:
1. The "Add Row" or "New Entry" button.
2. The project/activity selection dropdowns.
3. The hours input fields.
4. The "Save" or "Submit" button.

You can modify `poc_timesheet.py` to use `page.click(selector)` and `page.fill(selector, value)` to automate the entry process.
