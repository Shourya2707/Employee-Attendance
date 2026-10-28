"""
Seed script to generate 500+ realistic Indian context employee and attendance records.
"""
import random
from datetime import datetime, date, timedelta
from pathlib import Path
from database import LocalClient, LocalCollection

FIRST_NAMES = [
    "Aarav", "Priya", "Rohan", "Ananya", "Vikram", "Sneha", "Rahul", "Pooja", 
    "Amitav", "Neha", "Rajesh", "Meera", "Karthik", "Divya", "Sandeep", "Kavita", 
    "Arjun", "Sunita", "Manoj", "Ritu", "Siddharth", "Ishita", "Varun", "Preeti", 
    "Nikhil", "Tanvi", "Aditya", "Shreya", "Deepak", "Anushka", "Gaurav", "Swati", 
    "Alok", "Pallavi", "Harish", "Aakanksha", "Manish", "Bhavna", "Kunal", "Archana"
]

LAST_NAMES = [
    "Sharma", "Patel", "Gupta", "Verma", "Singh", "Iyer", "Deshmukh", "Nair", 
    "Banerjee", "Joshi", "Kumar", "Sundaram", "Rajan", "Reddy", "Malhotra", "Kulkarni", 
    "Tiwari", "Saxena", "Menon", "Dutta", "Nambiar", "Choudhury", "Chawla", "Singhal", 
    "Mehta", "Bhatia", "Aggarwal", "Pillai", "Mukherjee", "Kapoor", "Chatterjee", "Mishra"
]

DEPARTMENTS = [
    ("Engineering", ["Principal Architect", "Senior Backend Engineer", "Frontend Developer", "DevOps Engineer", "QA Automation Lead", "Cloud Engineer"]),
    ("Product", ["Senior Product Manager", "Associate PM", "UI/UX Designer", "Product Analyst"]),
    ("Finance", ["Financial Controller", "Senior Accountant", "Tax Analyst", "Payroll Specialist"]),
    ("HR", ["HR Business Partner", "Talent Acquisition Lead", "HR Operations Specialist"]),
    ("Sales", ["Enterprise Sales Manager", "Account Executive", "Business Development Lead"]),
    ("Marketing", ["Growth Marketing Lead", "Digital Marketing Specialist", "Content Strategist"]),
    ("Operations", ["Operations Lead", "Logistics Coordinator", "Facilities Manager"]),
    ("IT Support", ["Systems Administrator", "Network Engineer", "IT Desk Lead"])
]

INDIAN_CITIES = ["Bengaluru", "Mumbai", "Pune", "Hyderabad", "Delhi NCR", "Chennai"]

TRAFFIC_NOTES = [
    "Traffic delay on Silk Board junction",
    "Heavy jam on Western Express Highway",
    "Metro purple line delay",
    "Outer Ring Road waterlogging",
    "Monsoon rain delay",
    "Signal failure at Hiranandani circle",
    "Traffic congestion near Cyber City"
]

LEAVE_NOTES = [
    "Approved Casual Leave (CL)",
    "Sick Leave - Viral fever",
    "Earned Leave (EL) - Family event",
    "Diwali celebration leave",
    "Personal emergency leave",
    "Doctor consultation and rest"
]

def generate_indian_dataset(target_attendance=525, num_employees=35):
    db_file = Path("attendance_db.json")
    if db_file.exists():
        try:
            db_file.unlink()
        except Exception:
            pass

    client = LocalClient(db_file)
    emp_col = LocalCollection("employees", db_file)
    att_col = LocalCollection("attendance", db_file)

    employees = []
    used_names = set()

    random.seed(42)  # Deterministic realistic seed

    for i in range(1, num_employees + 1):
        emp_id = f"EMP{1000 + i}"
        
        while True:
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            full_name = f"{first} {last}"
            if full_name not in used_names:
                used_names.add(full_name)
                break

        dept, designations = random.choice(DEPARTMENTS)
        desig = random.choice(designations)
        email = f"{first.lower()}.{last.lower()}@company.in"
        phone = f"+91 {random.randint(9700000000, 9999999999)}"

        emp_doc = {
            "employee_id": emp_id,
            "name": full_name,
            "department": dept,
            "designation": desig,
            "email": email,
            "phone": phone,
            "city": random.choice(INDIAN_CITIES),
            "created_at": "2026-08-01 09:00:00",
            "status": "Active"
        }
        emp_col.insert_one(emp_doc)
        employees.append(emp_doc)

    print(f"Generated {len(employees)} Indian corporate employees.")

    # Generate attendance across past ~18 business working days up to and including today
    base_date = date.today()
    work_dates = []
    curr = base_date
    while len(work_dates) < 18:
        if curr.weekday() < 5:
            work_dates.append(curr.strftime("%Y-%m-%d"))
        curr -= timedelta(days=1)

    # Ensure today is at the beginning so today's attendance is always 100% complete
    total_attendance = 0

    for d_str in work_dates:
        for emp in employees:
            if total_attendance >= target_attendance and d_str != work_dates[0]:
                break

            # Realistic probability distribution
            rand_roll = random.random()
            
            if rand_roll < 0.78:
                # Present (78%)
                status = "Present"
                in_min = random.randint(45, 60) if random.random() < 0.3 else random.randint(0, 15)
                in_hour = 8 if in_min >= 45 else 9
                checkin = f"{in_hour:02d}:{in_min:02d}"
                out_hour = random.choice([18, 18, 18, 19])
                out_min = random.randint(0, 50)
                checkout = f"{out_hour:02d}:{out_min:02d}"
                notes = "On-time arrival" if random.random() < 0.2 else ""

            elif rand_roll < 0.89:
                # Late (11%)
                status = "Late"
                in_hour = random.choice([9, 10])
                in_min = random.randint(35, 59) if in_hour == 9 else random.randint(0, 30)
                checkin = f"{in_hour:02d}:{in_min:02d}"
                checkout = f"{random.choice([18, 19])}:{random.randint(15, 55):02d}"
                notes = random.choice(TRAFFIC_NOTES)

            elif rand_roll < 0.94:
                # Half-Day (5%)
                status = "Half-Day"
                checkin = f"09:{random.randint(0, 15):02d}"
                checkout = f"13:{random.randint(20, 45):02d}"
                notes = "Half day approved (Post-lunch leave)"

            elif rand_roll < 0.98:
                # On Leave (4%)
                status = "On Leave"
                checkin = ""
                checkout = ""
                notes = random.choice(LEAVE_NOTES)

            else:
                # Absent (2%)
                status = "Absent"
                checkin = ""
                checkout = ""
                notes = "Uninformed absence"

            rec = {
                "employee_id": emp["employee_id"],
                "employee_name": emp["name"],
                "department": emp["department"],
                "date": d_str,
                "status": status,
                "checkin_time": checkin,
                "checkout_time": checkout,
                "notes": notes,
                "marked_at": f"{d_str} {checkin if checkin else '09:00'}:00"
            }
            att_col.insert_one(rec)
            total_attendance += 1

        if total_attendance >= target_attendance:
            break

    print(f"Successfully populated {total_attendance} attendance records in {db_file}.")
    return len(employees), total_attendance

if __name__ == "__main__":
    n_emp, n_att = generate_indian_dataset(525, 35)
    print(f"DONE: {n_emp} Employees and {n_att} Attendance records seeded successfully!")
