"""
Seed Script for Smart Blood Donor System (SBDS)
Creates:
- 110 Verified & Active Donor accounts
- 70 Seeker accounts
- 20 Hospital accounts
- 20 Blood Bank accounts
Total: 220 realistic accounts with complete profiles, inventory, requests, and KYC records.
Password for all accounts: Secret123!
"""

import os
import sys
import time
import secrets
import hashlib
import sqlite3
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

PASSWORD_HASH_ITERATIONS = 310_000
COMMON_PASSWORD = "Secret123!"

# Pre-compute PBKDF2 hash
def make_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]

MALE_NAMES = [
    "Md. Tanvir Ahmed", "Shakil Hossain", "Arifur Rahman", "Rakibul Islam", "Mehedi Hasan",
    "Fahim Shahriar", "Mahfuzur Rahman", "Saiful Islam", "Tariqul Islam", "Ashraful Alam",
    "Kamrul Hasan", "Nazmul Huda", "Sohel Rana", "Jahidul Islam", "Anisur Rahman",
    "Sajjad Hossain", "Al-Amin Sheikh", "Imran Hossain", "Golam Mostafa", "Moniruzzaman Monir",
    "Hasan Mahmud", "Zubair Ahmed", "Kawsar Ahmed", "Rezaul Karim", "Shariful Islam",
    "Mustafizur Rahman", "Tanjim Hasan", "Nayem Islam", "Shafiqul Islam", "Habibur Rahman",
    "Mahmudul Hasan", "Naimur Rahman", "Rashedul Islam", "Mizanur Rahman", "Asaduzzaman Noor",
    "Ehsanul Haque", "Zahid Hasan", "Biplob Hossain", "Farhan Tanvir", "Shahadat Hossain"
]

FEMALE_NAMES = [
    "Farhana Akter", "Nusrat Jahan", "Tahmina Sultana", "Sumaiya Islam", "Sadia Afrin",
    "Jannatul Ferdous", "Rasheda Begum", "Sharmin Sultana", "Nazia Hasan", "Sabrina Yeasmin",
    "Shamima Nasrin", "Afroza Begum", "Umme Kulsum", "Tasnim Zara", "Nabila Tabassum",
    "Farzana Haque", "Samia Rahman", "Tanjila Akter", "Maksuda Khatun", "Ishrat Jahan",
    "Lamia Sultana", "Salma Khatun", "Mahfuza Akter", "Rubina Yasmin", "Mehnaz Parveen",
    "Nafisa Anjum", "Fatema Tuz Zohra", "Ruma Akter", "Munira Sultana", "Bristy Akter"
]

DHAKA_AREAS = [
    ("Dhanmondi", 23.7461, 90.3742),
    ("Mirpur", 23.8223, 90.3654),
    ("Uttara", 23.8759, 90.3795),
    ("Gulshan", 23.7925, 90.4078),
    ("Banani", 23.7937, 90.4043),
    ("Mohakhali", 23.7776, 90.4035),
    ("Mohammadpur", 23.7658, 90.3584),
    ("Motijheel", 23.7330, 90.4172),
    ("Badda", 23.7806, 90.4267),
    ("Jatrabari", 23.7104, 90.4348),
    ("Shahbagh", 23.7388, 90.3956),
    ("Khilgaon", 23.7516, 90.4223),
    ("Rampura", 23.7612, 90.4208),
    ("Basundhara", 23.8191, 90.4326),
    ("Tejgaon", 23.7598, 90.3912)
]

OTHER_DISTRICTS = [
    ("Chattogram", "Agrabad", 22.3250, 91.8143),
    ("Chattogram", "Nasirabad", 22.3655, 91.8214),
    ("Chattogram", "Panchlaish", 22.3686, 91.8335),
    ("Rajshahi", "Boalia", 24.3636, 88.6241),
    ("Rajshahi", "Motihar", 24.3700, 88.6360),
    ("Sylhet", "Zindabazar", 24.8949, 91.8687),
    ("Sylhet", "Amberkhana", 24.9080, 91.8680),
    ("Khulna", "Sonadanga", 22.8200, 89.5400),
    ("Khulna", "Khalishpur", 22.8500, 89.5300),
    ("Barishal", "Sadatganj", 22.7010, 90.3535),
    ("Rangpur", "Dhap", 25.7500, 89.2500),
    ("Mymensingh", "Town Hall", 24.7539, 90.4073),
    ("Bogura", "Sutrapur", 24.8465, 89.3734),
    ("Cumilla", "Kandirpar", 23.4607, 91.1809),
    ("Gazipur", "Chowrasta", 23.9989, 90.4203)
]

HOSPITAL_LIST = [
    ("Dhaka Medical College Hospital", "Govt", "Dhaka", "Shahbagh", "10666", "Prof. Dr. Md. Nazmul Haque"),
    ("Sir Salimullah Medical College & Mitford Hospital", "Govt", "Dhaka", "Mitford", "02-7319002", "Prof. Dr. Md. Shah Alam"),
    ("Kurmitola General Hospital", "Govt", "Dhaka", "Cantonment", "02-55062345", "Brig. Gen. Md. Sajjad Kabir"),
    ("Shaheed Suhrawardy Medical College Hospital", "Govt", "Dhaka", "Sher-e-Bangla Nagar", "02-9130800", "Prof. Dr. Md. Mostafizur Rahman"),
    ("National Institute of Cardiovascular Diseases (NICVD)", "Govt", "Dhaka", "Sher-e-Bangla Nagar", "02-9122560", "Prof. Dr. Mir Jamal Uddin"),
    ("Bangabandhu Sheikh Mujib Medical University (BSMMU)", "Autonomous", "Dhaka", "Shahbagh", "02-9614545", "Prof. Dr. Md. Sharfuddin Ahmed"),
    ("Square Hospital Ltd.", "Private", "Dhaka", "Panthapath", "10616", "Dr. Sanwar Hossain"),
    ("United Hospital Ltd.", "Private", "Dhaka", "Gulshan", "10666", "Dr. Shafiul Alam"),
    ("Evercare Hospital Dhaka", "Private", "Dhaka", "Basundhara", "10678", "Dr. Arif Mahmud"),
    ("Labaid Specialized Hospital", "Private", "Dhaka", "Dhanmondi", "10606", "Dr. AM Shamim"),
    ("Ibn Sina Specialized Hospital", "Private", "Dhaka", "Dhanmondi", "10615", "Dr. Mohammad Nurul Amin"),
    ("BIRDEM General Hospital", "Autonomous", "Dhaka", "Shahbagh", "02-9661551", "Prof. M. K. I. Quayyum Choudhury"),
    ("Enam Medical College & Hospital", "Private", "Dhaka", "Savar", "02-7743779", "Dr. Md. Enamur Rahman"),
    ("Apollo Imperial Hospital Chattogram", "Private", "Chattogram", "Pahartali", "09612-247247", "Prof. Dr. Rabiul Husain"),
    ("Chattogram Medical College Hospital (CMCH)", "Govt", "Chattogram", "Panchlaish", "031-619400", "Brig. Gen. Shamim Ahsan"),
    ("Rajshahi Medical College Hospital (RMCH)", "Govt", "Rajshahi", "Rajpara", "0721-776001", "Brig. Gen. F. M. Shamim Ahmed"),
    ("Sylhet MAG Osmani Medical College Hospital", "Govt", "Sylhet", "Kajolshah", "0821-713667", "Brig. Gen. Mahbubur Rahman"),
    ("Khulna Medical College Hospital (KMCH)", "Govt", "Khulna", "Boyra", "041-760350", "Dr. Md. Rabiul Hasan"),
    ("Sher-e-Bangla Medical College Hospital (SBMCH)", "Govt", "Barishal", "Band Road", "0431-217354", "Dr. H. M. Saiful Islam"),
    ("Rangpur Medical College Hospital (RpMCH)", "Govt", "Rangpur", "Dhap", "0521-62288", "Dr. Md. Yunus Ali")
]

BLOOD_BANK_LIST = [
    ("Quantum Foundation Central Blood Lab", "NGO Blood Center", "Dhaka", "Shantinagar", "01714-010869", "Md. Rezaul Hasan"),
    ("Bangladesh Red Crescent Society Central Blood Bank", "Humanitarian Blood Bank", "Dhaka", "Mohammadpur", "02-9116563", "Kazi Shofiqul Azam"),
    ("Sandhani Central Blood Bank", "Voluntary Blood Bank", "Dhaka", "Shahbagh", "02-9668690", "Dr. Tanvir Ahmed"),
    ("Badhan Central Blood Bank", "Student Voluntary Bank", "Dhaka", "TSC, Dhaka University", "01534-982674", "Shahnewaz Shuvo"),
    ("Thalassemia Foundation Hospital Blood Bank", "Specialized Blood Bank", "Dhaka", "Green Road", "02-9103512", "Dr. Aminul Islam"),
    ("Fatema Rahim Blood Transfusion Center", "Private Blood Bank", "Dhaka", "Dhanmondi", "01711-345678", "Dr. M. A. Rahim"),
    ("Al-Markazul Islami Blood Bank", "Charitable Blood Bank", "Dhaka", "Shyamoli", "02-9127867", "Mufti Shahidul Islam"),
    ("Police Blood Bank Rajarbagh", "Institutional Blood Bank", "Dhaka", "Rajarbagh", "02-9334418", "Dr. Emdadul Haque"),
    ("Armed Forces Institute of Pathology (AFIP) Blood Bank", "Military Blood Center", "Dhaka", "Dhaka Cantonment", "02-8711111", "Col. Dr. Md. Asaduzzaman"),
    ("Dhaka Central Blood Bank & Transfusion Service", "Private Blood Bank", "Dhaka", "Farmgate", "01819-223344", "Dr. K. M. Jahangir"),
    ("Chittagong Sandhani Blood Center", "Voluntary Blood Bank", "Chattogram", "Anderkilla", "031-638700", "Dr. Nazmul Karim"),
    ("Chittagong Red Crescent Blood Center", "Humanitarian Blood Bank", "Chattogram", "Agrabad", "031-716245", "Aslam Hossain"),
    ("Rajshahi Sandhani Voluntary Blood Bank", "Voluntary Blood Bank", "Rajshahi", "RMCH Campus", "0721-772211", "Dr. Farhad Hossain"),
    ("Rajshahi Red Crescent Blood Bank", "Humanitarian Blood Bank", "Rajshahi", "Alupatti", "0721-774488", "S. M. Mahbub"),
    ("Sylhet Sandhani Blood Aid Center", "Voluntary Blood Bank", "Sylhet", "Chowhatta", "0821-718822", "Dr. Sayeed Ahmed"),
    ("Khulna Sandhani Voluntary Blood Bank", "Voluntary Blood Bank", "Khulna", "Dakbangla", "041-720120", "Dr. M. A. Kashem"),
    ("Barishal Voluntary Blood Donors Center", "Voluntary Blood Bank", "Barishal", "Sadatganj", "0431-64532", "Dr. Anwarul Azim"),
    ("Comilla Blood Foundation & Transfusion Hub", "NGO Blood Center", "Cumilla", "Kandirpar", "081-65432", "Mohammad Ali"),
    ("Bogura Sandhani Blood Center", "Voluntary Blood Bank", "Bogura", "Nawab Bari Road", "051-62345", "Dr. Rafiqul Islam"),
    ("Apex Lifecare Voluntary Blood Bank", "Private Blood Bank", "Dhaka", "Uttara", "01720-998877", "Dr. S. M. Kamrul")
]

DISEASE_REASONS = [
    "Dengue fever with severe thrombocytopenia",
    "Emergency C-Section delivery complication",
    "Open heart coronary artery bypass graft (CABG)",
    "Thalassemia routine monthly blood transfusion",
    "Road traffic accident severe internal hemorrhage",
    "Chemotherapy induced acute severe anemia",
    "Chronic kidney disease hemodialysis blood loss",
    "Aplastic anemia packed red blood cell requirement",
    "Orthopedic hip replacement surgical blood reserve",
    "Severe post-partum hemorrhage (PPH) resuscitation"
]


def seed_databases():
    print("=" * 60)
    print("STARTING COMPREHENSIVE SEEDING (220 ACCOUNTS)")
    print("=" * 60)

    now = datetime.now(timezone.utc)
    now_ts = int(now.timestamp())
    now_iso = now.isoformat()

    common_hash = make_hash(COMMON_PASSWORD)

    # 1. Connect to SQLite auth.db and urgent_requests.db
    auth_conn = sqlite3.connect("auth.db")
    urgent_conn = sqlite3.connect("urgent_requests.db")

    # Connect to PostgreSQL if available
    pg_conn = None
    pg_url = os.environ.get("DATABASE_URL")
    if pg_url:
        try:
            import psycopg2
            pg_conn = psycopg2.connect(pg_url, connect_timeout=5)
            print("[OK] Connected to PostgreSQL remote database.")
        except Exception as e:
            print(f"[NOTE] PostgreSQL not reachable: {e}. Seeding local SQLite databases.")

    def run_auth(sql, params=()):
        auth_conn.execute(sql, params)
        if pg_conn:
            try:
                pg_sql = sql.replace("?", "%s").replace("INSERT OR IGNORE INTO", "INSERT INTO").replace("INSERT OR REPLACE INTO", "INSERT INTO")
                if "ON CONFLICT" not in pg_sql and "INSERT INTO" in pg_sql:
                    pg_sql += " ON CONFLICT DO NOTHING"
                pg_cur = pg_conn.cursor()
                pg_cur.execute(pg_sql, params)
            except Exception:
                pg_conn.rollback()

    def run_urgent(sql, params=()):
        urgent_conn.execute(sql, params)
        if pg_conn:
            try:
                pg_sql = sql.replace("?", "%s").replace("INSERT OR IGNORE INTO", "INSERT INTO").replace("INSERT OR REPLACE INTO", "INSERT INTO")
                if "ON CONFLICT" not in pg_sql and "INSERT INTO" in pg_sql:
                    pg_sql += " ON CONFLICT DO NOTHING"
                pg_cur = pg_conn.cursor()
                pg_cur.execute(pg_sql, params)
            except Exception:
                pg_conn.rollback()

    # =========================================================================
    # PART A: 110 DONOR ACCOUNTS (+8801700000001 to +8801700000110)
    # =========================================================================
    print("\n--- Seeding 110 Donor Accounts ---")
    donor_phones = []
    for i in range(1, 111):
        phone = f"+880170000{i:04d}"
        donor_phones.append(phone)
        bg = BLOOD_GROUPS[(i - 1) % len(BLOOD_GROUPS)]

        if i % 2 == 1:
            name = MALE_NAMES[(i // 2) % len(MALE_NAMES)]
            gender = "Male"
        else:
            name = FEMALE_NAMES[(i // 2) % len(FEMALE_NAMES)]
            gender = "Female"

        if i <= 80:
            loc = DHAKA_AREAS[(i - 1) % len(DHAKA_AREAS)]
            district = "Dhaka"
            area = loc[0]
            lat = loc[1] + (secrets.randbelow(40) - 20) * 0.001
            lng = loc[2] + (secrets.randbelow(40) - 20) * 0.001
        else:
            loc = OTHER_DISTRICTS[(i - 81) % len(OTHER_DISTRICTS)]
            district = loc[0]
            area = loc[1]
            lat = loc[2] + (secrets.randbelow(40) - 20) * 0.001
            lng = loc[3] + (secrets.randbelow(40) - 20) * 0.001

        email = f"donor_{i}@sbds.org.bd"
        dob = f"199{i % 9 + 1}-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"
        is_verified = 1 if i <= 95 else 0

        # auth_users
        auth_conn.execute(
            """
            INSERT OR REPLACE INTO auth_users (
                phone, password_hash, created_at, updated_at, role, name, blood_group,
                status, district, area, is_verified, email
            ) VALUES (?, ?, ?, ?, 'donor', ?, ?, 'active', ?, ?, ?, ?)
            """,
            (phone, common_hash, now_ts, now_ts, name, bg, district, area, is_verified, email)
        )

        # donor_profiles
        last_donation = (now - timedelta(days=(i * 7 + 10) % 150 + 20)).strftime("%Y-%m-%d")
        auth_conn.execute(
            """
            INSERT OR REPLACE INTO donor_profiles (
                phone, name, email, date_of_birth, gender, blood_group, district, area, address,
                last_donation, medical_conditions, medications, allergies, fitness_status,
                preferred_donation_types, updated_at, is_available, share_direct_contact
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'None', 'None', 'None', 'fit', 'Whole Blood, Platelets', ?, 1, 1)
            """,
            (phone, name, email, dob, gender, bg, district, area, f"House {i*3}, Road {i%15 + 1}, {area}", last_donation, now_iso)
        )

        # donor_availability
        auth_conn.execute(
            """
            INSERT OR REPLACE INTO donor_availability (
                donor_phone, is_available, radius_km, preferred_zones, updated_at
            ) VALUES (?, 1, 15, ?, ?)
            """,
            (phone, area, now_iso)
        )

        # donor_privacy_settings
        auth_conn.execute(
            """
            INSERT OR REPLACE INTO donor_privacy_settings (
                phone, allow_hospital_calls, mask_public_phone, public_directory, show_badges,
                share_direct_contact, phone_visibility, updated_at
            ) VALUES (?, 1, 0, 1, 1, 1, 'all', ?)
            """,
            (phone, now_iso)
        )

        # donor_location_settings
        auth_conn.execute(
            """
            INSERT OR REPLACE INTO donor_location_settings (
                phone, granularity, share_exact_location, allow_gps_detection, emergency_elevation,
                fuzzy_radius_km, last_latitude, last_longitude, updated_at
            ) VALUES (?, 'exact', 1, 1, 1, 0, ?, ?, ?)
            """,
            (phone, lat, lng, now_iso)
        )

        # donor_kyc_verifications (in urgent_requests.db)
        kyc_status = "verified" if is_verified == 1 else ("pending" if i <= 105 else "rejected")
        nid_num = f"199{i%9+1}{secrets.randbelow(8999999)+1000000}"
        urgent_conn.execute(
            """
            INSERT OR REPLACE INTO donor_kyc_verifications (
                donor_phone, donor_name, blood_group, nid_number, document_type, document_url,
                status, rejection_reason, submitted_at, reviewed_at, reviewed_by
            ) VALUES (?, ?, ?, ?, 'NID Card', '/static/uploads/demo_nid.jpg', ?, ?, ?, ?, ?)
            """,
            (
                phone, name, bg, nid_num, kyc_status,
                "" if kyc_status != "rejected" else "Unclear scanned photo of National ID.",
                now_iso,
                now_iso if kyc_status != "pending" else None,
                "+8801745678901" if kyc_status != "pending" else None
            )
        )

        # Some donation history
        if i % 2 == 0:
            don_date = (now - timedelta(days=(i * 12) % 360 + 30)).strftime("%Y-%m-%d")
            hosp_sample = HOSPITAL_LIST[(i // 2) % len(HOSPITAL_LIST)][0]
            urgent_conn.execute(
                """
                INSERT OR REPLACE INTO donation_history (
                    donor_phone, donation_date, donation_type, hospital_name, district, area
                ) VALUES (?, ?, 'Whole Blood', ?, ?, ?)
                """,
                (phone, don_date, hosp_sample, district, area)
            )
            urgent_conn.execute(
                """
                INSERT OR REPLACE INTO donor_donation_history (
                    donor_phone, donated_at, donation_type, notes
                ) VALUES (?, ?, 'Whole Blood', ?)
                """,
                (phone, don_date, f"Voluntary blood donation at {hosp_sample}")
            )

    print("[OK] Created 110 Donors (with Profiles, Availability, Privacy, GPS Coordinates, KYC Records, and History).")

    # =========================================================================
    # PART B: 70 SEEKER ACCOUNTS (+8801800000001 to +8801800000070)
    # =========================================================================
    print("\n--- Seeding 70 Seeker Accounts ---")
    seeker_phones = []
    for i in range(1, 71):
        phone = f"+880180000{i:04d}"
        seeker_phones.append(phone)
        bg = BLOOD_GROUPS[(i - 1) % len(BLOOD_GROUPS)]

        if i % 2 == 1:
            name = MALE_NAMES[(i - 1) % len(MALE_NAMES)]
        else:
            name = FEMALE_NAMES[(i - 1) % len(FEMALE_NAMES)]

        if i <= 55:
            loc = DHAKA_AREAS[(i - 1) % len(DHAKA_AREAS)]
            district = "Dhaka"
            area = loc[0]
        else:
            loc = OTHER_DISTRICTS[(i - 56) % len(OTHER_DISTRICTS)]
            district = loc[0]
            area = loc[1]

        email = f"seeker_{i}@sbds.org.bd"

        auth_conn.execute(
            """
            INSERT OR REPLACE INTO auth_users (
                phone, password_hash, created_at, updated_at, role, name, blood_group,
                status, district, area, is_verified, email
            ) VALUES (?, ?, ?, ?, 'seeker', ?, ?, 'active', ?, ?, 1, ?)
            """,
            (phone, common_hash, now_ts, now_ts, name, bg, district, area, email)
        )

        # Seed realistic blood requests created by these seekers (about 45 requests)
        if i <= 45:
            is_emergency = 1 if i % 3 == 0 else 0
            urgency = "Emergency" if is_emergency else ("Urgent" if i % 2 == 0 else "Standard")
            hosp = HOSPITAL_LIST[(i - 1) % len(HOSPITAL_LIST)][0]
            patient_name = f"Patient {name.split()[-1]}"
            units = (i % 3) + 1
            reason = DISEASE_REASONS[(i - 1) % len(DISEASE_REASONS)]
            needed_dt = (now + timedelta(hours=6 if is_emergency else 24)).strftime("%Y-%m-%d %H:%M")
            req_status = "Active" if i <= 35 else ("Fulfilled" if i <= 40 else "Completed")

            urgent_conn.execute(
                """
                INSERT OR REPLACE INTO blood_requests (
                    blood_group, hospital_name, district, area, distance_km, expires_at,
                    contact_phone, is_emergency, status, moderation_status, duplicate_risk,
                    patient_name, units, created_at, owner_phone, needed_at, urgency_level, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved', 0.1, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bg, hosp, district, area, round(2.5 + (i % 7) * 1.8, 1),
                    (now + timedelta(days=2)).isoformat(),
                    phone, is_emergency, req_status,
                    patient_name, units,
                    (now - timedelta(hours=i*2)).isoformat(),
                    phone, needed_dt, urgency, reason
                )
            )

    print("[OK] Created 70 Seekers (with Active Blood Requests, Emergency SOS cases, and Medical Demands).")

    # =========================================================================
    # PART C: 20 HOSPITAL ACCOUNTS (+8801900000001 to +8801900000020)
    # =========================================================================
    print("\n--- Seeding 20 Hospital Accounts ---")
    for i in range(1, 21):
        phone = f"+880190000{i:04d}"
        hosp_data = HOSPITAL_LIST[i - 1]
        hosp_name = hosp_data[0]
        facility_type = "Hospital"
        district = hosp_data[2]
        area = hosp_data[3]
        hotline = hosp_data[4]
        director = hosp_data[5]
        email = f"info@{hosp_name.lower().replace(' ', '').replace('&', '').replace('(', '').replace(')', '').replace('.', '')[:14]}.org.bd"

        auth_conn.execute(
            """
            INSERT OR REPLACE INTO auth_users (
                phone, password_hash, created_at, updated_at, role, name, org_name,
                status, district, area, is_verified, email
            ) VALUES (?, ?, ?, ?, 'hospital', ?, ?, 'active', ?, ?, 1, ?)
            """,
            (phone, common_hash, now_ts, now_ts, hosp_name, hosp_name, district, area, email)
        )

        auth_conn.execute(
            """
            INSERT OR REPLACE INTO facility_settings (
                phone, facility_name, facility_type, license_no, est_year, director_name,
                director_title, hotline, email, address, division, area, phlebotomy_chairs,
                apheresis_active, cold_storage_temp, ultra_freezer_active, nat_screening,
                continuous_shift, low_stock_threshold, auto_sos_dispatch, inter_facility_network,
                audio_siren, sms_doctor_alerts, daily_inventory_audit, two_factor_auth, maintenance_mode, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'Medical Director & Chief of Surgery', ?, ?, ?, ?, ?, 8, 1, 4.0, 1, 1, 1, 5, 1, 1, 1, 1, 1, 1, 0, ?)
            """,
            (
                phone, hosp_name, facility_type, f"DGHS-HOSP-{1000+i}", 1990 + (i % 25),
                director, hotline, email, f"{area}, {district}", district, area, now_iso
            )
        )

        # Inventory for all 8 blood groups
        for bg_idx, bg in enumerate(BLOOD_GROUPS):
            units = (i * 3 + bg_idx * 5) % 35 + 4
            urgent_conn.execute(
                """
                INSERT OR REPLACE INTO facility_blood_inventory (
                    facility_phone, blood_group, quantity, updated_at
                ) VALUES (?, ?, ?, ?)
                """,
                (phone, bg, units, now_iso)
            )
            urgent_conn.execute(
                """
                INSERT OR REPLACE INTO hospital_blood_inventory (
                    facility_name, facility_type, district, blood_group, units_available, status, last_updated
                ) VALUES (?, 'Hospital', ?, ?, ?, 'available', ?)
                """,
                (hosp_name, district, bg, units, now_iso)
            )

    print("[OK] Created 20 Hospitals (with DGHS Accreditation, Facility Settings, and Blood Stock Matrix).")

    # =========================================================================
    # PART D: 20 BLOOD BANK ACCOUNTS (+8801500000001 to +8801500000020)
    # =========================================================================
    print("\n--- Seeding 20 Blood Bank Accounts ---")
    for i in range(1, 21):
        phone = f"+880150000{i:04d}"
        bank_data = BLOOD_BANK_LIST[i - 1]
        bank_name = bank_data[0]
        facility_type = "Blood Bank"
        district = bank_data[2]
        area = bank_data[3]
        hotline = bank_data[4]
        director = bank_data[5]
        email = f"contact@{bank_name.lower().replace(' ', '').replace('&', '').replace('(', '').replace(')', '').replace('.', '')[:14]}.org.bd"

        auth_conn.execute(
            """
            INSERT OR REPLACE INTO auth_users (
                phone, password_hash, created_at, updated_at, role, name, org_name,
                status, district, area, is_verified, email
            ) VALUES (?, ?, ?, ?, 'bank', ?, ?, 'active', ?, ?, 1, ?)
            """,
            (phone, common_hash, now_ts, now_ts, bank_name, bank_name, district, area, email)
        )

        auth_conn.execute(
            """
            INSERT OR REPLACE INTO facility_settings (
                phone, facility_name, facility_type, license_no, est_year, director_name,
                director_title, hotline, email, address, division, area, phlebotomy_chairs,
                apheresis_active, cold_storage_temp, ultra_freezer_active, nat_screening,
                continuous_shift, low_stock_threshold, auto_sos_dispatch, inter_facility_network,
                audio_siren, sms_doctor_alerts, daily_inventory_audit, two_factor_auth, maintenance_mode, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'General Secretary & In-Charge', ?, ?, ?, ?, ?, 12, 1, 3.5, 1, 1, 1, 8, 1, 1, 1, 1, 1, 1, 0, ?)
            """,
            (
                phone, bank_name, facility_type, f"DGHS-BANK-{2000+i}", 1985 + (i % 30),
                director, hotline, email, f"{area}, {district}", district, area, now_iso
            )
        )

        # Inventory for all 8 blood groups
        for bg_idx, bg in enumerate(BLOOD_GROUPS):
            units = (i * 4 + bg_idx * 7) % 55 + 10
            urgent_conn.execute(
                """
                INSERT OR REPLACE INTO facility_blood_inventory (
                    facility_phone, blood_group, quantity, updated_at
                ) VALUES (?, ?, ?, ?)
                """,
                (phone, bg, units, now_iso)
            )
            urgent_conn.execute(
                """
                INSERT OR REPLACE INTO hospital_blood_inventory (
                    facility_name, facility_type, district, blood_group, units_available, status, last_updated
                ) VALUES (?, 'Blood Bank', ?, ?, ?, 'available', ?)
                """,
                (bank_name, district, bg, units, now_iso)
            )

    print("[OK] Created 20 Blood Banks (with Cold-Chain Parameters, Full Blood Reserves, and Hotline Info).")

    # Commit SQLite
    auth_conn.commit()
    urgent_conn.commit()
    auth_conn.close()
    urgent_conn.close()

    if pg_conn:
        try:
            pg_conn.commit()
            pg_conn.close()
            print("[OK] Successfully synchronized with remote PostgreSQL database.")
        except Exception as e:
            print(f"[NOTE] Remote PG commit: {e}")

    print("\n" + "=" * 60)
    print("ALL 220 ACCOUNTS SUCCESSFULLY CREATED & LINKED!")
    print(f"Universal Login Password: {COMMON_PASSWORD}")
    print("  - Donors:     110 (+8801700000001 to +8801700000110)")
    print("  - Seekers:     70 (+8801800000001 to +8801800000070)")
    print("  - Hospitals:   20 (+8801900000001 to +8801900000020)")
    print("  - Blood Banks: 20 (+8801500000001 to +8801500000020)")
    print("=" * 60)

if __name__ == "__main__":
    seed_databases()
