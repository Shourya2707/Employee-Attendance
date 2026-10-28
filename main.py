"""Interactive command-line interface. Run: python main.py"""
from datetime import datetime

from database import connect
from validators import (VALID_STATUSES, validate_checkin_checkout, validate_date, validate_department,
                        validate_designation, validate_employee_id, validate_name, validate_status, validate_time)

MENU = """
==================== EMPLOYEE ATTENDANCE ====================
  [1] Add employee          [4] View attendance records
  [2] View employees        [5] Open web dashboard
  [3] Mark attendance       [6] Exit
  (Ctrl+C cancels the current action)"""


def ask(prompt, validator):
    """Keep asking until the validator accepts the answer."""
    while True:
        ok, value = validator(input(prompt))
        if ok:
            return value
        print("  Error:", value)


def ask_employee(emp_col):
    while True:
        emp = emp_col.find_one({"employee_id": input("Employee ID: ").strip().upper()})
        if emp:
            return emp
        print("  Error: no employee with that ID.")


def add_employee(emp_col):
    emp_id = ask("Employee ID (e.g. EMP101): ", validate_employee_id)
    if emp_col.find_one({"employee_id": emp_id}):
        return print(f"  Error: {emp_id} is already registered.")
    doc = {
        "employee_id": emp_id,
        "name": ask("Full name: ", validate_name),
        "department": ask("Department: ", validate_department),
        "designation": ask("Designation: ", validate_designation),
        "email": input("Email (optional): ").strip() or f"{emp_id.lower()}@company.com",
        "phone": input("Phone (optional): ").strip() or "N/A",
        "city": input("City (optional): ").strip(),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Active",
    }
    emp_col.insert_one(doc)
    print(f"  Saved {doc['name']} ({emp_id}).")


def view_employees(emp_col):
    employees = list(emp_col.find({}, {"_id": 0}, sort=[("employee_id", 1)]))
    print(f"\n{'ID':<9} {'NAME':<22} {'DEPARTMENT':<13} DESIGNATION")
    for e in employees:
        print(f"{e['employee_id']:<9} {e['name']:<22} {e['department']:<13} {e['designation']}")
    print(f"Total: {len(employees)}")


def mark_attendance(emp_col, att_col):
    emp = ask_employee(emp_col)
    day = ask("Date [Enter = today]: ", validate_date)
    key = {"employee_id": emp["employee_id"], "date": day}
    existing = att_col.find_one(key)
    if existing and input(f"  Already marked {existing['status']}. Overwrite? (y/n): ").strip().lower() != "y":
        return
    status = ask(f"Status ({', '.join(VALID_STATUSES)}) [Enter = Present]: ", validate_status)
    checkin = checkout = ""
    if status in ("Present", "Late", "Half-Day"):
        now = datetime.now().strftime("%H:%M")
        checkin = ask(f"Check-in HH:MM [Enter = {now}]: ", validate_time) or now

        def valid_checkout(text):
            ok, value = validate_time(text)
            return validate_checkin_checkout(checkin, value) if ok else (ok, value)
        checkout = ask("Check-out HH:MM [Enter = skip]: ", valid_checkout)
    record = {**key, "employee_name": emp["name"], "department": emp["department"], "status": status,
              "checkin_time": checkin, "checkout_time": checkout, "notes": input("Notes (optional): ").strip(),
              "marked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    att_col.update_one(key, {"$set": record}, upsert=True)
    print(f"  Saved: {emp['name']} {status} on {day}.")


def view_attendance(att_col):
    choice = input("Filter: [1] all  [2] employee  [3] date  [4] department: ").strip()
    query = {}
    if choice == "2":
        query = {"employee_id": input("Employee ID: ").strip().upper()}
    elif choice == "3":
        query = {"date": ask("Date [Enter = today]: ", validate_date)}
    elif choice == "4":
        query = {"department": input("Department: ").strip()}
    records = list(att_col.find(query, {"_id": 0}, sort=[("date", -1), ("employee_id", 1)]))
    print(f"\n{'DATE':<11} {'ID':<9} {'NAME':<22} {'STATUS':<9} {'IN':<6} OUT")
    for r in records:
        print(f"{r['date']:<11} {r['employee_id']:<9} {r['employee_name']:<22} {r['status']:<9} "
              f"{r['checkin_time'] or '--:--':<6} {r['checkout_time'] or '--:--'}")
    counts = {s: sum(r["status"] == s for r in records) for s in VALID_STATUSES}
    print(f"Total: {len(records)} | " + " | ".join(f"{s}: {n}" for s, n in counts.items()))


def main():
    emp_col, att_col = connect()
    actions = {
        "1": lambda: add_employee(emp_col),
        "2": lambda: view_employees(emp_col),
        "3": lambda: mark_attendance(emp_col, att_col),
        "4": lambda: view_attendance(att_col),
    }
    while True:
        print(MENU)
        choice = input("Choice: ").strip()
        if choice == "5":
            import webbrowser
            import server
            webbrowser.open("http://127.0.0.1:5000")
            return server.run(5000)
        if choice == "6":
            return
        try:
            actions.get(choice, lambda: print("  Choose 1-6."))()
        except KeyboardInterrupt:
            print("\n  Cancelled.")


if __name__ == "__main__":
    main()
