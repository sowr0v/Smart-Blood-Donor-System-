# 🩸 Smart Blood Donor System

A modern web-based **Smart Blood Donor System (SBDS)** designed to connect blood donors, blood seekers, hospitals, and blood banks through a centralized digital platform.

The system helps users find suitable blood donors based on **blood group and location**, submit emergency blood requests, communicate with donors, manage blood stock, and maintain secure user accounts.

---

## 📌 Project Overview

The **Smart Blood Donor System** is designed to make the blood donation and blood searching process faster, easier, and more organized.

The platform provides separate portals for different user roles:

* 🩸 Blood Donor
* 🏥 Blood Seeker
* 🏨 Hospital / Blood Bank
* 👨‍💼 System Administrator

Users can register and verify their phone numbers using **SMS OTP**, search for nearby donors, create blood requests, communicate with other users, and manage their profiles.

---

# 🎯 Main Objectives

* Connect blood donors with people who need blood.
* Search donors using **blood group and location**.
* Provide nearby donor and map-based search functionality.
* Support urgent and emergency blood requests.
* Enable communication between donors and blood seekers.
* Allow hospitals and blood banks to manage blood stock.
* Provide donor verification and account management.
* Maintain secure authentication using OTP verification.
* Provide an administrative dashboard for system management.

---

# 🗂️ UI/UX Structure

The system interface is organized into the following major sections.

## 01 — Landing Page

The public landing page introduces the platform and provides quick access to important blood-related information.

### Sections

* Global Top Navigation & Verified Donor Ticker
* Hero Section & Dual Action CTAs
* Real-Time Active Requests Feed
* Platform Live Impact Statistics
* How Rokto Lagbe Works — 4-Step Workflow
* Urgent Blood Board — Critical Requirements
* Call-To-Action Join Banner
* Multi-Column Public Footer
* About Public Page
* Contact Public Page

### Public Footer and Information Pages

The public footer is shared by the landing, registration, About, Contact, Terms of Use, and Privacy Notice pages. It links to patient and donor actions, support and safety information, and the official helpline numbers 10666 and 999. The platform is independent and is not affiliated with hospitals or government emergency services.

The About page describes the platform's purpose and limitations. The Contact page form opens an email draft in the visitor's email application when `PUBLIC_CONTACT_EMAIL` is configured. Without that environment variable, the page clearly explains that messages cannot be delivered; it does not store or submit the form. Emergency services should not be contacted through this form.

The landing page's critical blood board reads from `/api/v1/requests/urgent` and displays only unexpired rows with `is_emergency = 1`. The app creates `urgent_requests.db` on startup by default; set `SBDS_DATABASE_PATH` to use another SQLite file. The board refreshes every 15 seconds and updates countdowns every second. Request records need a blood group, hospital name, district, area, expiry timestamp, and emergency flag; `distance_km` and `contact_phone` are optional.

---

# 02 — Authentication

The authentication module manages user registration, login, verification, and account recovery.

### Authentication Features

* Multi-Role User Registration
* Unified Login
* SMS OTP Verification Gateway
* OTP Verification
* Password Recovery
* Password Reset
* Role-Based Login Redirection

### Password Recovery Setup

Password recovery uses the SQLite database at `auth.db` by default; set `SBDS_AUTH_DATABASE_PATH` to use another file. Configure `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER` before enabling SMS delivery. The recovery code expires after 10 minutes, allows up to five verification attempts, and can be reissued once per minute per registered number.

Passwords are stored as PBKDF2 hashes. New passwords must have at least 12 characters, with uppercase and lowercase letters, a number, and a symbol. A successful reset updates `auth_users` and deletes every persisted session for that account. The existing registration page is still a UI-only stub; an account-registration/authentication provider must provision `auth_users` with an E.164 Bangladesh phone number and a password hash before login or recovery is available.

### Authentication Flow

```text
Register
   ↓
Enter Personal Information
   ↓
Phone Number Verification
   ↓
SMS OTP
   ↓
OTP Verification
   ↓
Account Activation
   ↓
Login
   ↓
Role-Based Portal
```

---

# 03 — Multi-Role User Portals

The system provides separate interfaces according to the user's role.

---

## 🩸 1. Donor Portal

The Donor Portal allows blood donors to manage their profile, donation activities, requests, communication, and account settings.

### Screens

* Dashboard
* Profile
* Donation History
* Blood Requests
* Chat List
* Request Details
* Reviews
* Settings

### Main Functions

* View donor profile
* Manage blood group and personal information
* View donation history
* Receive blood requests
* View request details
* Communicate with blood seekers
* Manage reviews
* Update account settings

---

# 🧑‍🩸 2. Blood Seeker Portal

The Blood Seeker Portal allows users to search for donors and create blood requests.

### Screens

* Dashboard
* Find Donor
* Map View
* Nearby Donors
* Donor List
* Donor Details
* Create Request
* Emergency Request
* My Requests
* Chat
* Call / WhatsApp
* Settings

### Main Functions

* Search donors by blood group
* Search donors by location
* View nearby donors
* View donor details
* View donors on a map
* Create blood requests
* Create emergency blood requests
* Track submitted requests
* Chat with donors
* Contact donors through phone/WhatsApp

---

# 🏥 3. Hospital / Blood Bank Portal

The Hospital / Blood Bank Portal allows hospitals and blood banks to manage donors, blood inventory, and blood requests.

### Screens

* Hospital Portal Dashboard
* Find Donor
* Blood Stock Inventory Management
* Hospital Request & Stock Allocation
* Settings

### Main Functions

* Monitor blood stock
* Manage blood inventory
* Search for donors
* Manage hospital blood requests
* Allocate available blood stock
* Update inventory information
* Manage organization settings

---

# 👨‍💼 4. Admin Portal

The Admin Portal provides centralized system management and monitoring.

### Screens

* Dashboard
* User Management
* Donor Verification
* Blood Requests
* Blood Stock
* Reviews
* Analytics

### Main Functions

* Manage system users
* Verify donor accounts
* Monitor blood requests
* Manage blood stock information
* Manage reviews
* Monitor system activity
* View analytics and statistics

---

# 🔔 04 — Notifications

The notification system keeps users informed about important activities.

### Notification Types

* New Blood Request
* Emergency Blood Request
* Donor Request
* Request Status Update
* OTP Notification
* Chat Notification
* Account Notification
* System Notification

---

# ⚙️ 05 — Settings & Privacy

The Settings & Privacy module provides account, privacy, and security controls.

## Account

* Personal Information
* Phone Number
* Password / Authentication

## Privacy

* Profile Visibility
* Location Sharing
* Contact Permissions
* Communication Permissions

## Security

* OTP Security
* Active Sessions
* Logout

## Account Management

* Delete Account

---

# 🔐 Security Features

The Smart Blood Donor System focuses on protecting user accounts and personal information.

### Security Components

* SMS OTP Verification
* Role-Based Access Control
* Secure Authentication
* Profile Visibility Controls
* Location Sharing Controls
* Contact Permissions
* Communication Permissions
* Active Session Management
* Secure Logout
* Account Deletion

---

# 🩸 Core Blood Search Flow

```text
Blood Seeker
     ↓
Select Blood Group
     ↓
Select Location
     ↓
Find Donors
     ↓
Nearby Donor List
     ↓
View Donor Details
     ↓
Contact Donor
     ↓
Create / Respond to Blood Request
```

---

# 🚨 Emergency Blood Request Flow

```text
Blood Seeker
     ↓
Emergency Request
     ↓
Select Blood Group
     ↓
Enter Required Units
     ↓
Select Location
     ↓
Submit Request
     ↓
Emergency Notification
     ↓
Nearby / Matching Donors
     ↓
Donor Response
     ↓
Communication
```

---

# 🗺️ Location & Map Services

The system uses location-based functionality to help blood seekers find nearby donors.

### Features

* Location-based donor search
* Nearby donor list
* Map view
* Donor location information
* Location sharing permissions
* Distance-based donor discovery

---

# 💬 Communication

The platform provides multiple communication methods between blood seekers and donors.

### Communication Methods

* Real-Time Chat
* Phone Call
* WhatsApp
* Emergency Notifications

Communication permissions can be controlled from the user's privacy settings.

---

# 🧑‍💻 Technology Stack

The planned technology stack includes:

| Layer           | Technology            |
| --------------- | --------------------- |
| Frontend        | HTML, CSS, JavaScript |
| Backend         | Python / FastAPI      |
| Database        | PostgreSQL            |
| Authentication  | SMS OTP API           |
| Location        | Map / Location API    |
| API Testing     | Postman               |
| Development     | VS Code               |
| Version Control | Git / GitHub          |

---

# 🏗️ System Architecture

The system follows a layered client-server architecture.

```text
                ┌──────────────────────┐
                │      Frontend        │
                │ HTML / CSS / JS      │
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │    Backend API       │
                │      FastAPI         │
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │    Business Logic    │
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │      Database        │
                │     PostgreSQL       │
                └──────────────────────┘

       ┌──────────────┐       ┌─────────────────┐
       │ SMS OTP API  │       │ Map/Location API│
       └──────────────┘       └─────────────────┘
```

---

# 👥 User Roles

| Role                     | Main Responsibilities                |
| ------------------------ | ------------------------------------ |
| 🩸 Donor                 | Donate blood and respond to requests |
| 🧑‍🩸 Blood Seeker       | Search donors and request blood      |
| 🏥 Hospital / Blood Bank | Manage blood stock and requests      |
| 👨‍💼 Administrator      | Manage and monitor the platform      |

---

# 📁 UI/UX Page Structure

```text
Smart Blood Donor System
│
├── 01 - Landing Page
│   ├── Navigation
│   ├── Hero
│   ├── Active Requests
│   ├── Live Statistics
│   ├── How It Works
│   ├── Urgent Blood Board
│   ├── CTA Banner
│   ├── About
│   ├── Contact
│   └── Footer
│
├── 02 - Authentication
│   ├── Login
│   ├── Register
│   ├── OTP Verification
│   ├── Forgot Password
│   └── Password Reset
│
├── 03 - User Portals
│   │
│   ├── Donor Portal
│   │   ├── Dashboard
│   │   ├── Profile
│   │   ├── Donation History
│   │   ├── Blood Requests
│   │   ├── Chat
│   │   ├── Reviews
│   │   └── Settings
│   │
│   ├── Blood Seeker Portal
│   │   ├── Dashboard
│   │   ├── Find Donor
│   │   ├── Map View
│   │   ├── Nearby Donors
│   │   ├── Donor List
│   │   ├── Donor Details
│   │   ├── Create Request
│   │   ├── Emergency Request
│   │   ├── My Requests
│   │   ├── Chat
│   │   ├── Call / WhatsApp
│   │   └── Settings
│   │
│   ├── Hospital / Blood Bank Portal
│   │   ├── Dashboard
│   │   ├── Find Donor
│   │   ├── Blood Stock
│   │   ├── Request & Allocation
│   │   └── Settings
│   │
│   └── Admin Portal
│       ├── Dashboard
│       ├── User Management
│       ├── Donor Verification
│       ├── Blood Requests
│       ├── Blood Stock
│       ├── Reviews
│       └── Analytics
│
├── 04 - Notifications
│
└── 05 - Settings & Privacy
    ├── Account
    ├── Privacy
    ├── Security
    ├── Active Sessions
    ├── Logout
    └── Delete Account
```

---

# 📊 Main System Modules

The Smart Blood Donor System is divided into the following major modules:

1. **Public Website**
2. **Authentication & OTP**
3. **Donor Management**
4. **Blood Seeker Management**
5. **Blood Request Management**
6. **Emergency Blood Request**
7. **Donor Search & Matching**
8. **Map & Location Services**
9. **Communication & Chat**
10. **Hospital / Blood Bank Management**
11. **Blood Stock Management**
12. **Admin Management**
13. **Notifications**
14. **Reviews & Ratings**
15. **Privacy & Security**
16. **Account Management**

---

# 🚀 Key Features

* 🩸 Blood Group Based Search
* 📍 Location Based Donor Search
* 🗺️ Map View
* 🚨 Emergency Blood Requests
* 🔔 Real-Time Notifications
* 💬 Real-Time Communication
* 📱 Phone & WhatsApp Contact
* 🔐 SMS OTP Verification
* 👥 Multi-Role Authentication
* 🏥 Hospital Blood Stock Management
* 👨‍💼 Admin Dashboard
* ⭐ Reviews & Ratings
* 🔒 Privacy & Security Controls
* 📊 System Analytics

---

# 🎨 UI/UX Design

The UI/UX design is structured around:

* Clean and modern interface
* Blood-focused visual identity
* Simple navigation
* Role-based dashboards
* Responsive design
* Mobile-friendly layouts
* Clear emergency indicators
* Accessible blood search workflow
* Consistent design system

---

# 📌 Project Status

> 🚧 **Currently in UI/UX Design & Development Phase**

### Current Focus

* [x] Project structure
* [x] User roles
* [x] Portal structure
* [x] Authentication flow
* [x] Blood search flow
* [x] Emergency request flow
* [x] Hospital / Blood Bank portal
* [x] Admin portal
* [ ] Complete Figma UI/UX
* [ ] Frontend development
* [ ] Backend API development
* [ ] PostgreSQL integration
* [ ] SMS OTP integration
* [ ] Map API integration
* [ ] Testing
* [ ] Deployment

---

# 📄 Project Documentation

The project documentation includes:

* Software Requirements Specification (SRS)
* UI/UX Design
* System Architecture
* UML Diagrams
* Use Case Diagrams
* Activity Diagrams
* Class Diagram
* Database Design
* API Documentation
* Testing Documentation

---

# 👨‍💻 Development Tools

* **Visual Studio Code**
* **Git**
* **GitHub**
* **Postman**
* **Figma**

---

# 📞 Communication

The system supports communication between donors and blood seekers through:

```text
Donor
 │
 ├── Real-Time Chat
 ├── Phone Call
 ├── WhatsApp
 └── Emergency Notification
```

---

# 🔒 Privacy & User Control

Users have control over important privacy settings, including:

* Profile visibility
* Location sharing
* Contact permissions
* Communication permissions
* Active sessions
* OTP security
* Logout
* Account deletion

---

# 🌟 Vision

The vision of the Smart Blood Donor System is to create a centralized digital platform where people can quickly connect with suitable blood donors, hospitals, and blood banks during both normal and emergency situations.

The system aims to simplify donor discovery, improve communication, organize blood requests, and provide better blood inventory management through a secure and location-aware platform.

---

## 📜 License

This project is developed for **academic and educational purposes**.

---

## 🩸 Smart Blood Donor System

**Connecting Blood Donors with People Who Need Blood.**
