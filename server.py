"""Web server: serves the dashboard in static/ and a small JSON API. Run: python server.py [port]"""
import csv
import hashlib
import io
import json
import mimetypes
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import seed_data
from database import LocalCollection, connect
from validators import (validate_checkin_checkout, validate_date, validate_department, validate_designation,
                        validate_employee_id, validate_name, validate_status, validate_time)

STATIC_DIR = (Path(__file__).parent / "static").resolve()
ON_SITE = ("Present", "Late", "Half-Day")
NO_ID = {"_id": 0}  # MongoDB's ObjectId is not JSON-serialisable
emp_col = att_col = None  # set by run(), or by the tests


def now(fmt="%Y-%m-%d %H:%M:%S"):
    return datetime.now().strftime(fmt)


def check(result):
    """Unwrap a validator result, raising ValueError (-> HTTP 400) on failure."""
    ok, value = result
    if not ok:
        raise ValueError(value)
    return value


def employees():
    return list(emp_col.find({}, NO_ID, sort=[("employee_id", 1)]))


def attendance():
    return list(att_col.find({}, NO_ID, sort=[("date", -1), ("employee_id", 1)]))


def add_employee(data):
    emp_id = check(validate_employee_id(data["employee_id"]))
    doc = {
        "employee_id": emp_id,
        "name": check(validate_name(data["name"])),
        "department": check(validate_department(data["department"])),
        "designation": check(validate_designation(data["designation"])),
        "email": data["email"] or f"{emp_id.lower()}@company.com",
        "phone": data["phone"] or "N/A",
        "city": data["city"],
        "created_at": now(),
        "status": "Active",
    }
    if emp_col.find_one({"employee_id": emp_id}):
        raise ValueError(f"Employee ID '{emp_id}' is already registered.")
    emp_col.insert_one(dict(doc))  # copy: pymongo adds _id to the dict it inserts
    return doc


def mark_attendance(data):
    emp_id = data["employee_id"].upper()
    emp = emp_col.find_one({"employee_id": emp_id})
    if not emp:
        raise ValueError(f"Employee '{emp_id}' not found.")
    day = check(validate_date(data["date"]))
    status = check(validate_status(data["status"]))
    checkin = check(validate_time(data["checkin_time"]))
    checkout = check(validate_time(data["checkout_time"]))
    key = {"employee_id": emp_id, "date": day}
    if status in ON_SITE:
        if not checkin:
            checkin = (att_col.find_one(key, NO_ID) or {}).get("checkin_time") or now("%H:%M")
        check(validate_checkin_checkout(checkin, checkout))
    else:
        checkin = checkout = ""
    record = {**key, "employee_name": emp["name"], "department": emp["department"], "status": status,
              "checkin_time": checkin, "checkout_time": checkout, "notes": data["notes"], "marked_at": now()}
    att_col.update_one(key, {"$set": record}, upsert=True)
    return record


def mark_all_present(data):
    day = check(validate_date(data["date"]))
    done = {r["employee_id"] for r in att_col.find({"date": day}, NO_ID)}
    new = [{"employee_id": e["employee_id"], "employee_name": e["name"], "department": e["department"],
            "date": day, "status": "Present", "checkin_time": "09:00", "checkout_time": "18:00",
            "notes": "Marked present in bulk", "marked_at": now()}
           for e in emp_col.find({"status": "Active"}, NO_ID) if e["employee_id"] not in done]
    if new:
        att_col.insert_many(new)
    return {"marked": len(new), "date": day}


def delete_attendance(data):
    if not data["employee_id"] or not data["date"]:
        raise ValueError("employee_id and date are required.")
    result = att_col.delete_one({"employee_id": data["employee_id"].upper(), "date": data["date"]})
    return {"deleted": result.deleted_count}


WRITE_ROUTES = {
    ("POST", "/api/employees"): (201, add_employee),
    ("POST", "/api/attendance"): (200, mark_attendance),
    ("POST", "/api/attendance/mark-all-present"): (200, mark_all_present),
    ("DELETE", "/api/attendance"): (200, delete_attendance),
}


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, body, content_type="application/json", filename=None):
        if content_type == "application/json":
            body = json.dumps(body)
        body = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if filename:
            self.send_header("Content-Disposition", f"attachment; filename={filename}")
        self.end_headers()
        self.wfile.write(body)

    def not_found(self):
        self.reply(404, {"error": "Not found"})

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path
        if path == "/" or path.startswith("/static/"):
            file = (STATIC_DIR / (path[len("/static/"):] if path != "/" else "index.html")).resolve()
            if file.parent != STATIC_DIR or not file.is_file():  # blocks ../ traversal
                return self.not_found()
            self.reply(200, file.read_bytes(), mimetypes.guess_type(file.name)[0] or "application/octet-stream")
        elif path == "/api/employees":
            self.reply(200, employees())
        elif path == "/api/attendance":
            self.reply(200, attendance())
        elif path == "/api/live-status":
            # ponytail: hashes all data per poll; fine for thousands of rows, use a change counter beyond that
            version = hashlib.md5(json.dumps([employees(), attendance()]).encode()).hexdigest()[:12]
            engine = "JSON file" if isinstance(emp_col, LocalCollection) else "MongoDB"
            self.reply(200, {"version": version, "server_time": now(), "today": now("%Y-%m-%d"), "engine": engine})
        elif path == "/api/export-csv":
            month = parse_qs(url.query).get("month", [""])[0]
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerow(["Date", "Employee ID", "Employee Name", "Department", "Status", "Check-In", "Check-Out", "Notes"])
            for r in attendance():
                if r["date"].startswith(month):
                    writer.writerow([r["date"], r["employee_id"], r["employee_name"], r["department"], r["status"],
                                     r["checkin_time"], r["checkout_time"], r["notes"]])
            self.reply(200, out.getvalue(), "text/csv", f"attendance_{month or 'all'}.csv")
        else:
            self.not_found()

    def write(self):
        route = WRITE_ROUTES.get((self.command, urlparse(self.path).path))
        if not route:
            return self.not_found()
        code, action = route
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object.")
            # every field arrives as a stripped string, missing ones as ""
            fields = ("employee_id", "name", "department", "designation", "email", "phone", "city",
                      "date", "status", "checkin_time", "checkout_time", "notes")
            self.reply(code, action({k: str(data.get(k) or "").strip() for k in fields}))
        except ValueError as e:  # includes invalid JSON
            self.reply(400, {"error": str(e)})

    do_POST = do_DELETE = write


def run(port=5000):
    global emp_col, att_col
    emp_col, att_col = connect()
    if emp_col.find_one() is None:
        print("Empty database, adding demo data:", seed_data.seed(emp_col, att_col))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Dashboard: http://127.0.0.1:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 5000)
