"""
Database initialization script for PostgreSQL.
Creates all required tables, constraints, indexes, and initial records for SBDS.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required.")

SCHEMA_SQL = """
-- 1. Auth Users
CREATE TABLE IF NOT EXISTS auth_users (
    id SERIAL PRIMARY KEY,
    phone TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    role TEXT DEFAULT 'donor',
    name TEXT DEFAULT '',
    blood_group TEXT DEFAULT '',
    org_name TEXT DEFAULT '',
    govt_reg TEXT DEFAULT '',
    manager_name TEXT DEFAULT '',
    address TEXT DEFAULT '',
    email TEXT DEFAULT '',
    district TEXT DEFAULT '',
    area TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    is_verified INTEGER DEFAULT 0
);

-- 2. Auth Sessions
CREATE TABLE IF NOT EXISTS auth_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    created_at BIGINT NOT NULL,
    expires_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);

-- 3. Password Reset Challenges
CREATE TABLE IF NOT EXISTS password_reset_challenges (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    phone TEXT NOT NULL,
    otp_hash TEXT NOT NULL,
    otp_salt TEXT NOT NULL,
    created_at BIGINT NOT NULL,
    expires_at BIGINT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    verified_at BIGINT,
    reset_token_hash TEXT,
    reset_expires_at BIGINT,
    consumed_at BIGINT
);
CREATE INDEX IF NOT EXISTS idx_reset_challenges_phone ON password_reset_challenges(phone, created_at);

-- 4. Account Phone Update Challenges
CREATE TABLE IF NOT EXISTS account_phone_update_challenges (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    current_phone TEXT NOT NULL,
    target_phone TEXT NOT NULL,
    otp_hash TEXT NOT NULL,
    otp_salt TEXT NOT NULL,
    created_at BIGINT NOT NULL,
    expires_at BIGINT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    consumed_at BIGINT
);
CREATE INDEX IF NOT EXISTS idx_account_phone_update_user ON account_phone_update_challenges(user_id, created_at DESC);

-- 5. Donor Profiles
CREATE TABLE IF NOT EXISTS donor_profiles (
    phone TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    date_of_birth TEXT,
    gender TEXT,
    blood_group TEXT NOT NULL,
    district TEXT NOT NULL,
    area TEXT NOT NULL,
    address TEXT NOT NULL,
    last_donation TEXT,
    medical_conditions TEXT,
    medications TEXT,
    allergies TEXT,
    fitness_status TEXT NOT NULL DEFAULT 'Eligible',
    preferred_donation_types TEXT NOT NULL DEFAULT 'Whole Blood',
    share_direct_contact INTEGER NOT NULL DEFAULT 0,
    is_available INTEGER NOT NULL DEFAULT 1,
    updated_at BIGINT NOT NULL
);

-- 6. Donor Privacy Settings
CREATE TABLE IF NOT EXISTS donor_privacy_settings (
    phone TEXT PRIMARY KEY,
    allow_hospital_calls INTEGER NOT NULL DEFAULT 1,
    mask_public_phone INTEGER NOT NULL DEFAULT 1,
    public_directory INTEGER NOT NULL DEFAULT 1,
    show_badges INTEGER NOT NULL DEFAULT 1,
    share_direct_contact INTEGER NOT NULL DEFAULT 0,
    phone_visibility TEXT NOT NULL DEFAULT 'hospital_only',
    updated_at BIGINT NOT NULL
);

-- 7. Donor Settings
CREATE TABLE IF NOT EXISTS donor_settings (
    phone TEXT PRIMARY KEY,
    settings_json TEXT NOT NULL,
    updated_at BIGINT NOT NULL
);

-- 8. Communication Preferences
CREATE TABLE IF NOT EXISTS communication_preferences (
    phone TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('donor', 'seeker')),
    preferences_json TEXT NOT NULL,
    updated_at BIGINT NOT NULL,
    PRIMARY KEY (phone, role)
);

-- 9. Donor Location Settings
CREATE TABLE IF NOT EXISTS donor_location_settings (
    phone TEXT PRIMARY KEY,
    granularity TEXT NOT NULL DEFAULT 'approximate',
    share_exact_location INTEGER NOT NULL DEFAULT 0,
    allow_gps_detection INTEGER NOT NULL DEFAULT 1,
    emergency_elevation INTEGER NOT NULL DEFAULT 1,
    fuzzy_radius_km DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    last_latitude DOUBLE PRECISION DEFAULT 23.7461,
    last_longitude DOUBLE PRECISION DEFAULT 90.3742,
    updated_at BIGINT NOT NULL
);

-- 10. Facility Settings
CREATE TABLE IF NOT EXISTS facility_settings (
    phone TEXT PRIMARY KEY,
    facility_name TEXT NOT NULL,
    facility_type TEXT NOT NULL,
    license_no TEXT DEFAULT '',
    est_year TEXT DEFAULT '',
    director_name TEXT DEFAULT '',
    director_title TEXT DEFAULT '',
    hotline TEXT DEFAULT '',
    email TEXT DEFAULT '',
    address TEXT DEFAULT '',
    division TEXT DEFAULT 'Dhaka',
    area TEXT DEFAULT '',
    gps_coords TEXT DEFAULT '',
    landmark TEXT DEFAULT '',
    phlebotomy_chairs INTEGER DEFAULT 8,
    components_json TEXT DEFAULT '["PRBC", "Platelets", "FFP", "Cryo", "Whole Blood"]',
    apheresis_active INTEGER DEFAULT 1,
    cold_storage_temp TEXT DEFAULT '3.8°C',
    ultra_freezer_active INTEGER DEFAULT 1,
    nat_screening INTEGER DEFAULT 1,
    continuous_shift INTEGER DEFAULT 1,
    low_stock_threshold INTEGER DEFAULT 5,
    auto_sos_dispatch INTEGER DEFAULT 1,
    inter_facility_network INTEGER DEFAULT 1,
    audio_siren INTEGER DEFAULT 1,
    sms_doctor_alerts INTEGER DEFAULT 1,
    daily_inventory_audit INTEGER DEFAULT 1,
    two_factor_auth INTEGER DEFAULT 1,
    maintenance_mode INTEGER DEFAULT 0,
    updated_at BIGINT NOT NULL
);

-- 11. Blood Stock Thresholds
CREATE TABLE IF NOT EXISTS blood_stock_thresholds (
    blood_group TEXT PRIMARY KEY,
    threshold INTEGER NOT NULL CHECK (threshold >= 0 AND threshold <= 50),
    updated_at BIGINT NOT NULL
);

-- 12. Blood Requests
CREATE TABLE IF NOT EXISTS blood_requests (
    id SERIAL PRIMARY KEY,
    blood_group TEXT NOT NULL,
    hospital_name TEXT NOT NULL,
    district TEXT,
    area TEXT,
    distance_km DOUBLE PRECISION,
    expires_at TEXT NOT NULL,
    contact_phone TEXT,
    is_emergency INTEGER DEFAULT 0,
    owner_phone TEXT,
    patient_name TEXT NOT NULL DEFAULT '',
    units INTEGER NOT NULL DEFAULT 1,
    needed_at TEXT,
    urgency_level TEXT NOT NULL DEFAULT 'Standard',
    reason TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Active',
    moderation_status TEXT DEFAULT 'approved',
    duplicate_risk DOUBLE PRECISION DEFAULT 0.0,
    duplicate_of_id INTEGER DEFAULT NULL,
    moderation_notes TEXT DEFAULT '',
    moderated_at TEXT DEFAULT '',
    moderated_by TEXT DEFAULT '',
    created_at TEXT
);

-- 13. Donor Request Responses
CREATE TABLE IF NOT EXISTS donor_request_responses (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES blood_requests(id),
    donor_phone TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('accept', 'decline')),
    eta TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    responded_at TEXT NOT NULL,
    UNIQUE (request_id, donor_phone)
);

-- 14. Seeker Notifications
CREATE TABLE IF NOT EXISTS seeker_notifications (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES blood_requests(id),
    donor_phone TEXT NOT NULL,
    response TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- 15. Donor Donation History
CREATE TABLE IF NOT EXISTS donor_donation_history (
    id SERIAL PRIMARY KEY,
    donor_phone TEXT NOT NULL,
    request_id INTEGER REFERENCES blood_requests(id),
    donated_at TEXT NOT NULL,
    donation_type TEXT NOT NULL DEFAULT 'Whole Blood',
    notes TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_donation_history_donor_date ON donor_donation_history(donor_phone, donated_at DESC);

-- 16. Chat Threads
CREATE TABLE IF NOT EXISTS chat_threads (
    id TEXT PRIMARY KEY,
    donor_phone TEXT NOT NULL,
    seeker_phone TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (donor_phone, seeker_phone)
);

-- 17. Chat Messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
    sender_phone TEXT NOT NULL,
    text TEXT NOT NULL,
    sent_at TEXT NOT NULL,
    read_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_chat_messages_thread_time ON chat_messages(thread_id, sent_at, id);

-- 18. Chat Blocks
CREATE TABLE IF NOT EXISTS chat_blocks (
    blocker_phone TEXT NOT NULL,
    blocked_phone TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (blocker_phone, blocked_phone),
    CHECK (blocker_phone != blocked_phone)
);

-- 19. Chat Reports
CREATE TABLE IF NOT EXISTS chat_reports (
    id SERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
    reporter_phone TEXT NOT NULL,
    reported_phone TEXT NOT NULL,
    message_id TEXT REFERENCES chat_messages(id) ON DELETE SET NULL,
    reason TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE (thread_id, reporter_phone, message_id)
);

-- 20. Facility Blood Inventory
CREATE TABLE IF NOT EXISTS facility_blood_inventory (
    facility_phone TEXT NOT NULL,
    blood_group TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    updated_at TEXT,
    PRIMARY KEY (facility_phone, blood_group)
);

-- 21. Facility Inventory Audit
CREATE TABLE IF NOT EXISTS facility_inventory_audit (
    id SERIAL PRIMARY KEY,
    facility_phone TEXT NOT NULL,
    blood_group TEXT NOT NULL,
    previous_quantity INTEGER NOT NULL CHECK (previous_quantity >= 0),
    new_quantity INTEGER NOT NULL CHECK (new_quantity >= 0),
    actor_phone TEXT NOT NULL,
    changed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_facility_inventory_audit_recent ON facility_inventory_audit(facility_phone, changed_at DESC, id DESC);

-- 22. Facility Inventory Alerts
CREATE TABLE IF NOT EXISTS facility_inventory_alerts (
    id SERIAL PRIMARY KEY,
    facility_phone TEXT NOT NULL,
    blood_group TEXT NOT NULL,
    threshold INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'resolved')),
    triggered_at TEXT NOT NULL,
    resolved_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_facility_inventory_alert_active ON facility_inventory_alerts(facility_phone, blood_group) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_facility_inventory_alert_recent ON facility_inventory_alerts(facility_phone, triggered_at DESC, id DESC);

-- 23. Donor KYC Verifications
CREATE TABLE IF NOT EXISTS donor_kyc_verifications (
    id SERIAL PRIMARY KEY,
    donor_phone TEXT NOT NULL,
    donor_name TEXT NOT NULL,
    blood_group TEXT NOT NULL,
    nid_number TEXT NOT NULL,
    document_type TEXT NOT NULL DEFAULT 'National ID (NID)',
    document_url TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    rejection_reason TEXT DEFAULT '',
    submitted_at TEXT NOT NULL,
    reviewed_at TEXT DEFAULT '',
    reviewed_by TEXT DEFAULT ''
);

-- 24. Hospital Blood Inventory
CREATE TABLE IF NOT EXISTS hospital_blood_inventory (
    id SERIAL PRIMARY KEY,
    facility_name TEXT NOT NULL,
    facility_type TEXT NOT NULL DEFAULT 'hospital',
    district TEXT NOT NULL,
    blood_group TEXT NOT NULL,
    units_available INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'adequate',
    last_updated TEXT NOT NULL
);

-- 25. User Moderation Reports
CREATE TABLE IF NOT EXISTS user_moderation_reports (
    id SERIAL PRIMARY KEY,
    reporter_phone TEXT NOT NULL,
    reporter_name TEXT NOT NULL,
    target_phone TEXT NOT NULL,
    target_name TEXT NOT NULL,
    target_role TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'open',
    resolution_notes TEXT DEFAULT '',
    resolved_by TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 26. User Reviews
CREATE TABLE IF NOT EXISTS user_reviews (
    id SERIAL PRIMARY KEY,
    reviewer_phone TEXT NOT NULL,
    reviewer_name TEXT NOT NULL,
    target_phone TEXT NOT NULL,
    target_name TEXT NOT NULL,
    rating INTEGER NOT NULL DEFAULT 5,
    comment TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- 27. App Notifications
CREATE TABLE IF NOT EXISTS app_notifications (
    id SERIAL PRIMARY KEY,
    recipient_phone TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'system',
    link TEXT DEFAULT '',
    is_read INTEGER NOT NULL DEFAULT 0,
    priority TEXT NOT NULL DEFAULT 'normal',
    created_at TEXT NOT NULL
);

-- 28. Push Subscriptions
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id SERIAL PRIMARY KEY,
    user_phone TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    auth_key TEXT DEFAULT '',
    p256dh_key TEXT DEFAULT '',
    browser TEXT DEFAULT 'Chrome',
    device_type TEXT DEFAULT 'Desktop',
    created_at TEXT NOT NULL
);

-- 29. Push Dispatch Logs
CREATE TABLE IF NOT EXISTS push_dispatch_logs (
    id SERIAL PRIMARY KEY,
    sender TEXT NOT NULL,
    recipient_phone TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    click_url TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'delivered',
    fcm_message_id TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

-- 30. SMS Dispatch Logs
CREATE TABLE IF NOT EXISTS sms_dispatch_logs (
    id SERIAL PRIMARY KEY,
    sender TEXT NOT NULL,
    recipient_phone TEXT NOT NULL,
    blood_group TEXT DEFAULT '',
    hospital_name TEXT DEFAULT '',
    district TEXT DEFAULT '',
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    provider TEXT NOT NULL DEFAULT 'Twilio/SSL Wireless',
    tracking_id TEXT NOT NULL,
    request_id INTEGER,
    campaign_key TEXT DEFAULT '',
    failure_reason TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sms_dispatch_campaign_recent ON sms_dispatch_logs(campaign_key, recipient_phone, status, created_at);

-- 31. Request Moderation Logs
CREATE TABLE IF NOT EXISTS request_moderation_logs (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    admin_phone TEXT NOT NULL,
    admin_name TEXT NOT NULL,
    previous_status TEXT DEFAULT '',
    new_status TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    duplicate_of_id INTEGER DEFAULT NULL,
    ip_address TEXT DEFAULT '127.0.0.1',
    created_at TEXT NOT NULL
);

-- 32. Admin Settings
CREATE TABLE IF NOT EXISTS admin_settings (
    id SERIAL PRIMARY KEY,
    admin_phone TEXT NOT NULL,
    two_factor_auth INTEGER DEFAULT 1,
    session_timeout_minutes INTEGER DEFAULT 60,
    max_otp_attempts INTEGER DEFAULT 5,
    emergency_broadcast_lock INTEGER DEFAULT 0,
    auto_moderation_enabled INTEGER DEFAULT 1,
    sms_gateway_provider TEXT DEFAULT 'Twilio / SSL Wireless',
    fcm_enabled INTEGER DEFAULT 1,
    updated_at TEXT NOT NULL
);

-- 33. Admin Audit Logs
CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id SERIAL PRIMARY KEY,
    admin_phone TEXT NOT NULL,
    admin_name TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    target_phone TEXT DEFAULT '',
    details TEXT NOT NULL,
    ip_address TEXT DEFAULT '127.0.0.1',
    created_at TEXT NOT NULL
);

-- 34. Contact Messages & Support Inquiries
CREATE TABLE IF NOT EXISTS contact_messages (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'unread',
    created_at TEXT NOT NULL,
    ip_address TEXT DEFAULT '127.0.0.1'
);
CREATE INDEX IF NOT EXISTS idx_contact_messages_status ON contact_messages(status, id DESC);
"""

def init_db():
    print(f"Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    with conn:
        with conn.cursor() as cur:
            print("Creating tables and indexes...")
            cur.execute(SCHEMA_SQL)
            print("Seeding initial data if missing...")
            # Seed blood stock thresholds
            import time
            blood_groups = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
            now = int(time.time())
            for bg in blood_groups:
                cur.execute(
                    "INSERT INTO blood_stock_thresholds (blood_group, threshold, updated_at) VALUES (%s, 5, %s) ON CONFLICT DO NOTHING",
                    (bg, now)
                )

            # Ensure admin_audit_logs has target_phone
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'admin_audit_logs' AND column_name = 'target_phone'
                    ) THEN
                        ALTER TABLE admin_audit_logs ADD COLUMN target_phone TEXT DEFAULT '';
                    END IF;
                END $$;
            """)
    conn.close()
    print("Database tables initialized successfully on PostgreSQL!")

if __name__ == "__main__":
    init_db()
