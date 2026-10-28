# Employee Attendance Management System

Records employees and their daily attendance. It has two front ends that share one database:

- a web dashboard (`server.py` + `static/`)
- an interactive command-line menu (`main.py`)

Data is stored in MongoDB when one is reachable at `MONGODB_URI` (read from `.env`,
default `mongodb://localhost:27017/`). Otherwise it falls back to the local file
`attendance_db.json`, so the project runs with plain Python 3.8+ and no installs.
To use MongoDB, `pip install pymongo` and start a MongoDB server.

## Running

```
python server.py          # web dashboard on http://127.0.0.1:5000
python server.py 8080     # ...or on another port
python main.py            # command-line menu
python seed_data.py       # rebuild attendance_db.json with fresh demo data
```

On Windows, `run_web.bat` and `run_cli.bat` do the same (the web one also opens the browser).
If the database is empty, the server fills it with demo data on start-up.

## Project layout

| File | Purpose |
| --- | --- |
| `server.py` | HTTP server (standard library `http.server`): serves `static/` and the JSON API |
| `static/` | Web frontend: `index.html`, `style.css`, `app.js` |
| `main.py` | Command-line menu: add/list employees, mark and view attendance |
| `database.py` | Connects to MongoDB, or provides `LocalCollection`, a JSON-file stand-in with the same methods |
| `validators.py` | Input checks; each returns `(True, cleaned_value)` or `(False, error_message)` |
| `seed_data.py` | Generates 35 employees and six weeks of weekday attendance ending today |
| `test_suite.py` | Unit tests |

## API

All bodies are JSON. Errors are returned as `{"error": "message"}`.

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| GET | `/api/employees` | | list of employees, sorted by `employee_id` |
| GET | `/api/attendance` | | list of records, newest date first |
| GET | `/api/live-status` | | `{version, server_time, today}`; `version` changes whenever data changes |
| GET | `/api/export-csv?month=YYYY-MM` | | CSV download; `month` is optional |
| POST | `/api/employees` | `employee_id, name, department, designation`, optional `email, phone, city` | 201 + employee, 400 if invalid or duplicate |
| POST | `/api/attendance` | `employee_id, status`, optional `date` (default today), `checkin_time, checkout_time, notes` | 200 + record (creates or replaces that day's record), 400 if invalid |
| POST | `/api/attendance/mark-all-present` | optional `date` | `{marked, date}`: marks every active employee without a record as Present 09:00-18:00 |
| DELETE | `/api/attendance` | `employee_id, date` | `{deleted: 0 or 1}` |

Statuses: `Present`, `Late`, `Half-Day`, `On Leave`, `Absent`. Dates are `YYYY-MM-DD`, times `HH:MM`.
For Present/Late/Half-Day without a check-in time, the existing check-in (or the current time) is used;
On Leave and Absent records have empty times. Check-out must be after check-in.

Employee: `employee_id, name, department, designation, email, phone, city, created_at, status`.
Attendance record: `employee_id, employee_name, department, date, status, checkin_time, checkout_time, notes, marked_at`.

## Tests

```
python -m unittest test_suite -v
```

Covers the validators, `LocalCollection` (CRUD and unique keys) and one HTTP request against a
server on a temporary port. Tests use a temporary file and never touch `attendance_db.json`.
