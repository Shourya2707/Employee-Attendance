"""
Validators module for Employee Attendance Management System
"""
import re
from datetime import datetime, date

VALID_STATUSES = ["Present", "Absent", "Late", "Half-Day", "On Leave"]
VALID_DEPARTMENTS = ["Engineering", "HR", "Finance", "Marketing", "Sales", "Operations", "IT", "Management", "General"]

def validate_employee_id(emp_id: str) -> tuple[bool, str]:
    """Validate Employee ID (must be non-empty, e.g. EMP001 or alphanumeric 3-10 chars)."""
    if not emp_id or not isinstance(emp_id, str):
        return False, "Employee ID cannot be empty."
    emp_id = emp_id.strip()
    if len(emp_id) < 2 or len(emp_id) > 20:
        return False, "Employee ID must be between 2 and 20 characters."
    if not re.match(r"^[A-Za-z0-9\-_]+$", emp_id):
        return False, "Employee ID can only contain letters, numbers, hyphens, and underscores."
    return True, emp_id.upper()

def validate_name(name: str) -> tuple[bool, str]:
    """Validate employee name (min 2 chars, letters, spaces, hyphens, dots)."""
    if not name or not isinstance(name, str):
        return False, "Name cannot be empty."
    name = name.strip()
    if len(name) < 2 or len(name) > 60:
        return False, "Name must be between 2 and 60 characters."
    if not re.match(r"^[A-Za-z\s\.\-']+$", name):
        return False, "Name can only contain letters, spaces, hyphens, and periods."
    return True, name.title()

def validate_department(department: str) -> tuple[bool, str]:
    """Validate department name."""
    if not department or not isinstance(department, str):
        return False, "Department cannot be empty."
    dept = department.strip()
    if len(dept) < 2 or len(dept) > 40:
        return False, "Department must be between 2 and 40 characters."
    return True, dept.title()

def validate_designation(designation: str) -> tuple[bool, str]:
    """Validate designation / job title."""
    if not designation or not isinstance(designation, str):
        return False, "Designation cannot be empty."
    desig = designation.strip()
    if len(desig) < 2 or len(desig) > 50:
        return False, "Designation must be between 2 and 50 characters."
    return True, desig.title()

def validate_date(date_str: str) -> tuple[bool, str]:
    """Validate date in YYYY-MM-DD format."""
    if not date_str:
        return True, date.today().strftime("%Y-%m-%d")
    date_str = date_str.strip()
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d").date()
        return True, parsed.strftime("%Y-%m-%d")
    except ValueError:
        return False, "Invalid date format. Expected YYYY-MM-DD (e.g., 2026-10-28)."

def validate_status(status: str) -> tuple[bool, str]:
    """Validate attendance status."""
    if not status:
        return True, "Present"
    status_clean = status.strip().title()
    for valid in VALID_STATUSES:
        if status_clean.lower() == valid.lower():
            return True, valid
    return False, f"Invalid status '{status}'. Valid options are: {', '.join(VALID_STATUSES)}"

def validate_time(time_str: str) -> tuple[bool, str]:
    """Validate time in HH:MM format (24-hour)."""
    if not time_str or time_str.strip() == "":
        return True, ""
    time_str = time_str.strip()
    for fmt in ("%H:%M", "%I:%M %p", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(time_str, fmt)
            return True, parsed.strftime("%H:%M")
        except ValueError:
            continue
    return False, "Invalid time format. Expected HH:MM (e.g. 09:30 or 17:00)."

def validate_checkin_checkout(checkin: str, checkout: str) -> tuple[bool, str]:
    """Ensure check-out is after check-in."""
    if not checkin or not checkout:
        return True, ""
    try:
        t_in = datetime.strptime(checkin, "%H:%M")
        t_out = datetime.strptime(checkout, "%H:%M")
        if t_out <= t_in:
            return False, f"Check-out time ({checkout}) must be after check-in time ({checkin})."
        return True, ""
    except ValueError:
        return False, "Could not parse times for comparison."

