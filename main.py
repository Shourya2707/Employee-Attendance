"""
Employee Attendance Management System
Main CLI Application
"""
import sys
from datetime import datetime, date

try:
    from pymongo.errors import DuplicateKeyError
except ImportError:
    from database import DuplicateKeyError

from database import connect_and_setup
from validators import (
    validate_employee_id,
    validate_name,
    validate_department,
    validate_designation,
    validate_date,
    validate_status,
    validate_time,
    validate_checkin_checkout,
    VALID_STATUSES,
    VALID_DEPARTMENTS,
)

def print_header(title: str):
    print("\n" + "=" * 65)
    print(f"   {title.center(59)}")
    print("=" * 65)

def print_main_menu():
    print("\n" + "=" * 65)
    print("      EMPLOYEE ATTENDANCE MANAGEMENT SYSTEM - MAIN MENU")
    print("=" * 65)
    print("  [1] Add New Employee")
    print("  [2] View All Employees")
    print("  [3] Mark Daily Attendance")
    print("  [4] View Attendance Records & Reports")
    print("  [5] Launch Live Web Dashboard (Donezo UI)")
    print("  [6] Exit Application")
    print("=" * 65)

def add_employee(emp_col):
    print_header("ADD NEW EMPLOYEE")
    while True:
        emp_id_input = input("Enter Employee ID (e.g., EMP101, or 'q' to cancel): ").strip()
        if emp_id_input.lower() == 'q':
            return
        valid, val_emp_id = validate_employee_id(emp_id_input)
        if not valid:
            print(f"  [!] Error: {val_emp_id}")
            continue
        if emp_col.find_one({"employee_id": val_emp_id}):
            print(f"  [!] Error: Employee ID '{val_emp_id}' is already registered.")
            continue
        break

    while True:
        name_input = input("Enter Full Name: ").strip()
        valid, val_name = validate_name(name_input)
        if not valid:
            print(f"  [!] Error: {val_name}")
            continue
        break

    print(f"Suggested Departments: {', '.join(VALID_DEPARTMENTS[:6])}")
    while True:
        dept_input = input("Enter Department: ").strip()
        valid, val_dept = validate_department(dept_input)
        if not valid:
            print(f"  [!] Error: {val_dept}")
            continue
        break

    while True:
        desig_input = input("Enter Designation / Role: ").strip()
        valid, val_desig = validate_designation(desig_input)
        if not valid:
            print(f"  [!] Error: {val_desig}")
            continue
        break

    email_input = input("Enter Email Address (optional): ").strip()
    phone_input = input("Enter Phone Number (optional): ").strip()

    employee_doc = {
        "employee_id": val_emp_id,
        "name": val_name,
        "department": val_dept,
        "designation": val_desig,
        "email": email_input if email_input else f"{val_emp_id.lower()}@company.com",
        "phone": phone_input if phone_input else "N/A",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Active"
    }

    try:
        emp_col.insert_one(employee_doc)
        print("\n  [OK] SUCCESS! Employee registered successfully:")
        print(f"       ID:          {val_emp_id}")
        print(f"       Name:        {val_name}")
        print(f"       Department:  {val_dept}")
        print(f"       Designation: {val_desig}")
    except DuplicateKeyError:
        print(f"\n  [!] Error: Duplicate employee ID '{val_emp_id}'. Registration aborted.")

def view_all_employees(emp_col):
    print_header("REGISTERED EMPLOYEES DIRECTORY")
    employees = emp_col.find(sort=[("employee_id", 1)])
    if not employees:
        print("  No employees found in the system. Choose Option 1 to add an employee.")
        return

    print(f"{'EMP ID':<10} | {'NAME':<20} | {'DEPARTMENT':<15} | {'DESIGNATION':<18} | {'STATUS':<8}")
    print("-" * 80)
    for emp in employees:
        print(f"{emp.get('employee_id', ''):<10} | {emp.get('name', ''):<20} | {emp.get('department', ''):<15} | {emp.get('designation', ''):<18} | {emp.get('status', 'Active'):<8}")
    print("-" * 80)
    print(f"Total Registered Employees: {len(employees)}")

def mark_daily_attendance(emp_col, att_col):
    print_header("MARK DAILY ATTENDANCE")
    while True:
        emp_id_input = input("Enter Employee ID (or 'q' to cancel): ").strip().upper()
        if emp_id_input == 'Q':
            return
        emp = emp_col.find_one({"employee_id": emp_id_input})
        if not emp:
            print(f"  [!] Employee with ID '{emp_id_input}' does not exist. Please check ID.")
            continue
        break

    today_str = date.today().strftime("%Y-%m-%d")
    while True:
        date_input = input(f"Enter Attendance Date [Press Enter for Today: {today_str}]: ").strip()
        valid, val_date = validate_date(date_input)
        if not valid:
            print(f"  [!] Error: {val_date}")
            continue
        break

    existing = att_col.find_one({"employee_id": emp_id_input, "date": val_date})
    if existing:
        print(f"\n  [Notice] Attendance for {emp.get('name')} on {val_date} is already recorded as: {existing.get('status')}")
        overwrite = input("  Do you wish to update this record? (y/n) [n]: ").strip().lower()
        if overwrite != 'y':
            print("  Operation cancelled.")
            return

    print(f"\nAvailable Statuses: {', '.join(VALID_STATUSES)}")
    while True:
        status_input = input("Enter Status [Press Enter for 'Present']: ").strip()
        valid, val_status = validate_status(status_input)
        if not valid:
            print(f"  [!] Error: {val_status}")
            continue
        break

    now_time = datetime.now().strftime("%H:%M")
    checkin_time = ""
    checkout_time = ""

    if val_status in ["Present", "Late", "Half-Day"]:
        while True:
            t_in = input(f"Enter Check-In Time [Press Enter for {now_time}]: ").strip()
            if not t_in:
                checkin_time = now_time
                break
            valid, val_t_in = validate_time(t_in)
            if not valid:
                print(f"  [!] Error: {val_t_in}")
                continue
            checkin_time = val_t_in
            break

        while True:
            t_out = input("Enter Check-Out Time [HH:MM or Press Enter to skip]: ").strip()
            if not t_out:
                checkout_time = ""
                break
            valid, val_t_out = validate_time(t_out)
            if not valid:
                print(f"  [!] Error: {val_t_out}")
                continue
            v_pair, err_pair = validate_checkin_checkout(checkin_time, val_t_out)
            if not v_pair:
                print(f"  [!] Error: {err_pair}")
                continue
            checkout_time = val_t_out
            break

    notes = input("Enter Notes / Reason (optional): ").strip()

    attendance_record = {
        "employee_id": emp_id_input,
        "employee_name": emp.get("name", "Unknown"),
        "department": emp.get("department", "Unknown"),
        "date": val_date,
        "status": val_status,
        "checkin_time": checkin_time,
        "checkout_time": checkout_time,
        "notes": notes,
        "marked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if existing:
        att_col.update_one({"employee_id": emp_id_input, "date": val_date}, {"$set": attendance_record})
        print(f"\n  [OK] Attendance updated successfully for {emp.get('name')} ({emp_id_input}) on {val_date}.")
    else:
        try:
            att_col.insert_one(attendance_record)
            print(f"\n  [OK] Attendance recorded successfully for {emp.get('name')} ({emp_id_input}) on {val_date}.")
        except DuplicateKeyError:
            print("  [!] Error: Record already exists for this date.")

def view_attendance_records(att_col):
    print_header("ATTENDANCE RECORDS & REPORTS")
    print("  Filter by:")
    print("  [1] All Records")
    print("  [2] Specific Employee ID")
    print("  [3] Specific Date")
    print("  [4] Specific Department")
    choice = input("Select filter [1-4, Default: 1]: ").strip()

    query = {}
    if choice == '2':
        e_id = input("Enter Employee ID: ").strip().upper()
        query = {"employee_id": e_id}
    elif choice == '3':
        today_str = date.today().strftime("%Y-%m-%d")
        d_val = input(f"Enter Date (YYYY-MM-DD) [Default: {today_str}]: ").strip()
        valid, val_d = validate_date(d_val)
        if valid:
            query = {"date": val_d}
    elif choice == '4':
        dept_val = input("Enter Department Name: ").strip().title()
        query = {"department": dept_val}

    records = att_col.find(query, sort=[("date", -1), ("employee_id", 1)])
    if not records:
        print("\n  No attendance records match the selected criteria.")
        return

    print("\n" + f"{'DATE':<12} | {'EMP ID':<10} | {'NAME':<20} | {'DEPT':<12} | {'STATUS':<10} | {'IN':<6} | {'OUT':<6}")
    print("-" * 85)
    stats = {status: 0 for status in VALID_STATUSES}
    for rec in records:
        st = rec.get('status', 'Present')
        if st in stats:
            stats[st] += 1
        t_in = rec.get('checkin_time', '') or '--:--'
        t_out = rec.get('checkout_time', '') or '--:--'
        print(f"{rec.get('date', ''):<12} | {rec.get('employee_id', ''):<10} | {rec.get('employee_name', ''):<20} | {rec.get('department', ''):<12} | {st:<10} | {t_in:<6} | {t_out:<6}")
    print("-" * 85)
    print(f"Total Records: {len(records)} | Present: {stats['Present']} | Late: {stats['Late']} | Half-Day: {stats['Half-Day']} | Absent: {stats['Absent']} | On Leave: {stats['On Leave']}")

def seed_sample_data(emp_col, att_col):
    """Populates realistic initial sample employees and attendance for quick evaluation."""
    sample_employees = [
        {"employee_id": "EMP001", "name": "Aarav Sharma", "department": "Engineering", "designation": "Lead Architect", "email": "aarav.sharma@company.com", "phone": "9876543210", "status": "Active"},
        {"employee_id": "EMP002", "name": "Priya Patel", "department": "HR", "designation": "HR Manager", "email": "priya.patel@company.com", "phone": "9876543211", "status": "Active"},
        {"employee_id": "EMP003", "name": "Rohan Gupta", "department": "Finance", "designation": "Financial Analyst", "email": "rohan.gupta@company.com", "phone": "9876543212", "status": "Active"},
        {"employee_id": "EMP004", "name": "Ananya Verma", "department": "Marketing", "designation": "Marketing Lead", "email": "ananya.v@company.com", "phone": "9876543213", "status": "Active"},
        {"employee_id": "EMP005", "name": "Vikram Singh", "department": "Engineering", "designation": "Software Engineer", "email": "vikram.s@company.com", "phone": "9876543214", "status": "Active"}
    ]

    for emp in sample_employees:
        if not emp_col.find_one({"employee_id": emp["employee_id"]}):
            emp["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            emp_col.insert_one(emp)

    today = date.today().strftime("%Y-%m-%d")
    sample_attendance = [
        {"employee_id": "EMP001", "employee_name": "Aarav Sharma", "department": "Engineering", "date": today, "status": "Present", "checkin_time": "09:05", "checkout_time": "18:15", "notes": "On-time arrival"},
        {"employee_id": "EMP002", "employee_name": "Priya Patel", "department": "HR", "date": today, "status": "Present", "checkin_time": "09:20", "checkout_time": "18:00", "notes": ""},
        {"employee_id": "EMP003", "employee_name": "Rohan Gupta", "department": "Finance", "date": today, "status": "Late", "checkin_time": "10:15", "checkout_time": "18:30", "notes": "Traffic delay"},
        {"employee_id": "EMP004", "employee_name": "Ananya Verma", "department": "Marketing", "date": today, "status": "On Leave", "checkin_time": "", "checkout_time": "", "notes": "Approved annual leave"},
        {"employee_id": "EMP005", "employee_name": "Vikram Singh", "department": "Engineering", "date": today, "status": "Half-Day", "checkin_time": "09:10", "checkout_time": "13:30", "notes": "Doctor appointment"}
    ]

    for att in sample_attendance:
        if not att_col.find_one({"employee_id": att["employee_id"], "date": att["date"]}):
            att["marked_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            att_col.insert_one(att)

def main():
    client, db, emp_col, att_col = connect_and_setup()

    # Preload sample records if database is empty so user can immediately view records
    if emp_col.count_documents() == 0:
        seed_sample_data(emp_col, att_col)

    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        print("\n--- RUNNING DEMO MODE ---")
        view_all_employees(emp_col)
        view_attendance_records(att_col)
        print("\nDemo finished successfully!")
        return

    while True:
        print_main_menu()
        choice = input("Enter choice (1-6): ").strip()
        if choice == "1":
            add_employee(emp_col)
        elif choice == "2":
            view_all_employees(emp_col)
        elif choice == "3":
            mark_daily_attendance(emp_col, att_col)
        elif choice == "4":
            view_attendance_records(att_col)
        elif choice == "5":
            import webbrowser
            print("\n  Starting Donezo Interactive Web Dashboard at http://127.0.0.1:5000 ...")
            webbrowser.open("http://127.0.0.1:5000")
            from server import run_server
            run_server(5000)
        elif choice == "6":
            print("\nExiting Employee Attendance Management System. Goodbye!\n")
            if hasattr(client, 'close'):
                client.close()
            break
        else:
            print("  [!] Invalid choice. Please enter a number between 1 and 6.")

if __name__ == "__main__":
    main()
