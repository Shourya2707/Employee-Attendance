# Employee Attendance Management System

A robust, full-featured Employee Attendance Management System with both **Interactive Terminal CLI** and **Modern Live Web Dashboard**.

---

## 🚀 Quick Start (Running Live)

### Option 1: Live Interactive Terminal CLI
Run in PowerShell:
```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" main.py
```
*(Or simply double-click `run_cli.bat`)*

**To run an automated instant demo in terminal:**
```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" main.py --demo
```

---

### Option 2: Live Web Dashboard & REST API
Run in PowerShell:
```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" server.py
```
*(Or simply double-click `run_web.bat`)*

Open your browser at: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🛠 Project Architecture

| File | Description |
| :--- | :--- |
| **`main.py`** | Interactive CLI application providing Employee Registration, Attendance Tracking, Filtering, and Reports. |
| **`server.py`** | Lightweight, zero-dependency Web Server serving the interactive frontend dashboard and REST APIs (`/api/employees`, `/api/attendance`). |
| **`database.py`** | Database layer supporting live **MongoDB** (`mongodb://localhost:27017/`), with an automatic, seamless **Local Database** fallback (`attendance_db.json`) ensuring zero setup friction. |
| **`validators.py`** | Input validation engine checking Employee IDs, Name formats, Departments, Designations, Dates, Statuses, and Check-In/Check-Out logic. |
| **`test_suite.py`** | Complete `unittest` suite covering all validator and database CRUD operations. |
| **`run_cli.bat`** | 1-Click launcher for Terminal CLI. |
| **`run_web.bat`** | 1-Click launcher for Web Dashboard (automatically opens browser). |

---

## 🧪 Running Automated Tests

Run the test suite via PowerShell:
```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -m unittest test_suite.py -v
```

---

## 📋 Complete Feature Test Guide

### 1. Employee Management Tests
- [x] **Add Employee**: Validates employee ID format (`EMPxxx`), name, department, designation, and optional contact info.
- [x] **Duplicate ID Prevention**: Prevents registering two employees with the same ID (raises unique constraint error).
- [x] **Employee Directory**: Displays all active staff in formatted table with counts.

### 2. Attendance Tracking Tests
- [x] **Mark Attendance**: Records date (defaults to today), status (`Present`, `Late`, `Half-Day`, `Absent`, `On Leave`), and timestamps.
- [x] **Same-Day Duplicate Prevention**: Checks if attendance for the employee on the given date exists, prompting whether to update or retain.
- [x] **Time Validation**: Ensures check-out time is chronologically after check-in time.

### 3. Reports & Analytics Tests
- [x] **Attendance Log**: Formatted view with date, ID, name, status, and in/out times.
- [x] **Multi-Criteria Filtering**: Filter by specific employee, single date, or department.
- [x] **Summary Statistics**: Aggregates total records and counts per status category.

