# AttendIQ — Attendance & Performance Analyzer

A Python browser-based student attendance and performance tracker built with Streamlit, SQLite, Pandas, and Plotly.

## Features
- Dashboard with student totals, average attendance/performance, charts, and low-attendance alerts
- Student register with unique student IDs and search
- Daily attendance with Present, Absent, Late, and Excused statuses
- Assessment score entry and percentage calculations
- Combined student report and CSV exports
- SQLite persistence in `attendiq.db`

## Requirements
- Python 3.10 or newer
- Internet connection for initial package installation

## Run on Windows
1. Extract the project ZIP.
2. Open PowerShell in the extracted `attendiq_project` folder.
3. Run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

If PowerShell blocks activation, you can skip activation and run:
```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

The browser opens at `http://localhost:8501`. Keep the terminal open while using the app.

## Data and backup
The app creates `attendiq.db` automatically beside `app.py`. Back up this file regularly. CSV exports are available in Data tools and Reports.

## Online deployment
For a simple demo deployment, push the project to a GitHub repository and deploy it with Streamlit Community Cloud using `app.py` as the entry point. Note: the local SQLite file on a hosted service may not be durable across rebuilds/restarts unless the host provides persistent storage. For real multi-user production use, configure a managed database and authentication first.

## Calculation rules
- Attendance rate = (Present + Late) / (Present + Late + Absent) × 100
- Excused sessions are excluded from the denominator.
- Attendance alert: below 75%.
- Assessment percentage = marks obtained / maximum marks × 100.
- Performance average is the arithmetic mean of a student's recorded assessment percentages.

## Important
This starter application is designed for a small class, demo, or academic project. It does not include login/role-based permissions. Do not expose real student records publicly; add authentication, HTTPS, access controls, and persistent database backups before production use.
