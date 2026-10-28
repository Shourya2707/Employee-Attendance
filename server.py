"""
Employee Attendance Management System - Live Interactive Application Server
High-End Dashboard matching modern SaaS UI with:
1. Real-time background database synchronization
2. Interactive Dashboard with KPI cards, capsule analytics charts, radial progress gauge, and live time tracker
3. "Lazy & Efficient" Quick Data Entry Page (1-click mark, speed punch-in, batch actions)
4. Comprehensive Tabular Data Page (all data in row form with filters, search, inline editing, and CSV export)
"""

import sys
import os
import json
import urllib.parse
import mimetypes
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from datetime import datetime, date
from pathlib import Path

from database import connect_and_setup, DuplicateKeyError
from validators import (
    validate_employee_id,
    validate_name,
    validate_department,
    validate_designation,
    validate_date,
    validate_status,
    validate_time,
    VALID_STATUSES,
    VALID_DEPARTMENTS
)

_, _, emp_col, att_col = connect_and_setup()

def ensure_rich_seed_data():
    """Ensure a rich set of Indian corporate employees and attendance records exist."""
    if emp_col.count_documents() < 10 or att_col.count_documents() < 100:
        import seed_data
        seed_data.generate_indian_dataset(525, 35)

ensure_rich_seed_data()

STATIC_DIR = (Path(__file__).parent / "static").resolve()

class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Keep terminal log clean
        sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]} {args[1]}\n")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path.startswith("/static/"):
            name = "index.html" if path == "/" else path[len("/static/"):]
            file = (STATIC_DIR / name).resolve()
            if file.parent != STATIC_DIR or not file.is_file():
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(file.name)[0] or "application/octet-stream")
            self.end_headers()
            self.wfile.write(file.read_bytes())

        elif path == "/api/live-status":
            # Real-time state identifier based on database file modification time and record counts
            db_file = Path("attendance_db.json")
            mtime = db_file.stat().st_mtime if db_file.exists() else 0
            emp_count = emp_col.count_documents()
            att_count = att_col.count_documents()
            version_str = f"{mtime}_{emp_count}_{att_count}"
            self.respond_json(200, {
                "version": version_str,
                "employees_count": emp_count,
                "attendance_count": att_count,
                "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

        elif path == "/api/employees":
            employees = emp_col.find(sort=[("employee_id", 1)])
            self.respond_json(200, employees)

        elif path == "/api/attendance":
            records = att_col.find(sort=[("date", -1), ("employee_id", 1)])
            self.respond_json(200, records)

        elif path == "/api/export-csv":
            records = att_col.find(sort=[("date", -1), ("employee_id", 1)])
            csv_lines = ["Date,Employee ID,Employee Name,Department,Status,Check-In,Check-Out,Notes"]
            for r in records:
                csv_lines.append(f'"{r.get("date","")}","{r.get("employee_id","")}","{r.get("employee_name","")}","{r.get("department","")}","{r.get("status","")}","{r.get("checkin_time","")}","{r.get("checkout_time","")}","{r.get("notes","")}"')
            csv_content = "\n".join(csv_lines)

            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Disposition", "attachment; filename=attendance_records.csv")
            self.end_headers()
            self.wfile.write(csv_content.encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
        try:
            data = json.loads(body) if body else {}
        except Exception:
            self.respond_json(400, {"error": "Invalid JSON format"})
            return

        if path == "/api/employees":
            v_id, emp_id = validate_employee_id(data.get("employee_id", ""))
            v_name, name = validate_name(data.get("name", ""))
            v_dept, dept = validate_department(data.get("department", ""))
            v_desig, desig = validate_designation(data.get("designation", ""))
            if not v_id:
                self.respond_json(400, {"error": emp_id})
                return
            if not v_name:
                self.respond_json(400, {"error": name})
                return
            if not v_dept:
                self.respond_json(400, {"error": dept})
                return
            if not v_desig:
                self.respond_json(400, {"error": desig})
                return

            if emp_col.find_one({"employee_id": emp_id}):
                self.respond_json(400, {"error": f"Employee ID '{emp_id}' is already registered."})
                return

            new_emp = {
                "employee_id": emp_id,
                "name": name,
                "department": dept,
                "designation": desig,
                "email": data.get("email") or f"{emp_id.lower()}@company.com",
                "phone": data.get("phone") or "N/A",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Active"
            }
            emp_col.insert_one(new_emp)
            self.respond_json(201, new_emp)

        elif path == "/api/attendance":
            emp_id = data.get("employee_id", "").strip().upper()
            emp = emp_col.find_one({"employee_id": emp_id})
            if not emp:
                self.respond_json(400, {"error": f"Employee '{emp_id}' not found."})
                return

            v_date, date_str = validate_date(data.get("date", ""))
            v_status, status = validate_status(data.get("status", "Present"))

            record = {
                "employee_id": emp_id,
                "employee_name": emp.get("name", "Unknown"),
                "department": emp.get("department", "Unknown"),
                "date": date_str,
                "status": status,
                "checkin_time": data.get("checkin_time", "") or datetime.now().strftime("%H:%M"),
                "checkout_time": data.get("checkout_time", ""),
                "notes": data.get("notes", ""),
                "marked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            existing = att_col.find_one({"employee_id": emp_id, "date": date_str})
            if existing:
                att_col.update_one({"employee_id": emp_id, "date": date_str}, {"$set": record})
            else:
                att_col.insert_one(record)
            self.respond_json(200, record)

        elif path == "/api/attendance/quick-mark":
            # 1-Click fast mark endpoint for the Lazy Data Entry page
            emp_id = data.get("employee_id", "").strip().upper()
            status = data.get("status", "Present")
            date_str = data.get("date") or date.today().strftime("%Y-%m-%d")

            emp = emp_col.find_one({"employee_id": emp_id})
            if not emp:
                self.respond_json(400, {"error": f"Employee '{emp_id}' not found."})
                return

            existing = att_col.find_one({"employee_id": emp_id, "date": date_str})
            now_time = datetime.now().strftime("%H:%M")

            checkin = existing.get("checkin_time") if existing else (now_time if status in ["Present", "Late", "Half-Day"] else "")
            checkout = existing.get("checkout_time", "") if existing else ""

            record = {
                "employee_id": emp_id,
                "employee_name": emp.get("name", "Unknown"),
                "department": emp.get("department", "Unknown"),
                "date": date_str,
                "status": status,
                "checkin_time": checkin,
                "checkout_time": checkout,
                "notes": f"Quick-marked as {status}",
                "marked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            if existing:
                att_col.update_one({"employee_id": emp_id, "date": date_str}, {"$set": record})
            else:
                att_col.insert_one(record)

            self.respond_json(200, record)

        elif path == "/api/attendance/mark-all-present":
            # Ultra-lazy: 1-click mark all unmarked employees for today as Present
            today_str = date.today().strftime("%Y-%m-%d")
            all_emps = emp_col.find()
            marked_count = 0

            for emp in all_emps:
                emp_id = emp["employee_id"]
                existing = att_col.find_one({"employee_id": emp_id, "date": today_str})
                if not existing:
                    att_col.insert_one({
                        "employee_id": emp_id,
                        "employee_name": emp.get("name", "Unknown"),
                        "department": emp.get("department", "Unknown"),
                        "date": today_str,
                        "status": "Present",
                        "checkin_time": "09:00",
                        "checkout_time": "18:00",
                        "notes": "1-Click Auto Marked Present",
                        "marked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    marked_count += 1

            self.respond_json(200, {"message": f"Successfully marked {marked_count} remaining employees as Present for {today_str}!"})

        elif path == "/api/seed-demo":
            ensure_rich_seed_data()
            self.respond_json(200, {"message": "Demo data seeded successfully!"})

        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            self.respond_json(400, {"error": "Invalid JSON"})
            return

        if path == "/api/attendance":
            emp_id = data.get("employee_id")
            date_str = data.get("date")
            if not emp_id or not date_str:
                self.respond_json(400, {"error": "Missing employee_id or date"})
                return

            res = att_col.delete_one({"employee_id": emp_id, "date": date_str})
            self.respond_json(200, {"deleted": res.deleted_count})
        else:
            self.send_response(404)
            self.end_headers()

    def respond_json(self, status_code, obj):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode("utf-8"))

def run_server(port=5000):
    server = ThreadingHTTPServer(('127.0.0.1', port), RequestHandler)
    server.daemon_threads = True
    print(f"\n==================================================================")
    print(f"  DONEZO ATTENDANCE SYSTEM - LIVE INTERACTIVE SERVER")
    print(f"  Live Dashboard URL: http://127.0.0.1:{port}")
    print(f"  Real-time database auto-sync: ENABLED")
    print(f"  Press Ctrl+C to stop the server.")
    print(f"==================================================================\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()

if __name__ == "__main__":
    port = 5000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port)
