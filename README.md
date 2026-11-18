# AASHA – AI Voice Assistant for Rural Healthcare

> **"Voice for the Worker. Intelligence for the Workflow. Faster Connection to Care."**

A complete, full-stack, AI-powered healthcare web application built specifically for rural healthcare workers (ASHA workers) and Primary/Community Health Centre (PHC/CHC) Doctors in India.

---

## 🌟 The Core Principle: `Speak ➔ Understand ➔ Prioritize ➔ Connect`

Rural healthcare workers often need to record patient information while moving between remote homes and communities. Manual typing and paper forms consume critical time and delay life-saving medical guidance. 

**AASHA** transforms spoken notes in natural language (Hindi, Hinglish, English) into:
1. **Accurate Speech-to-Text Transcription** with live reviewing and editing.
2. **AI Clinical Extraction**: Symptoms, duration, observations, pregnancy notes, and medicines.
3. **Smart Triage Engine**: Configured clinical warning signs (IMNCI & maternal danger flags) automatically categorized into **Urgent**, **Moderate**, and **Routine** priorities.
4. **Dedicated One-to-One Doctor Channel**: Real-time routing to the assigned Medical Officer, who reviews prioritized cases, transmits guidance back to the field worker, and updates case status.

---

## 🎯 Complete 1-to-1 End-to-End Workflow

```
[ASHA Worker Login]
       │
       ▼
[Patient Registration] ── (Auto-generates ASH-PAT-0001)
       │
       ▼
[Voice Recording Studio] ── (Web Speech API + MediaRecorder, Hindi/English)
       │
       ▼
[Speech-to-Text] ── (Worker reviews & edits transcription)
       │
       ▼
[AI Information Extraction] ── (Extracts Symptoms, Duration, Vitals, Pregnancy)
       │
       ▼
[Smart Rule-Based Triage] ── (Flags: Urgent 🚨 | Moderate ⏳ | Routine ✅)
       │
       ▼
[Assigned Doctor Alert] ── (Real-time in-app notification & prioritized dashboard)
       │
       ▼
[Doctor Case Review] ── (Listens to voice note, inspects AI summary & red flags)
       │
       ▼
[Doctor Guidance Transmitted] ── (Prescribes action e.g., 108 ambulance referral)
       │
       ▼
[ASHA Worker Notification] ── (Worker receives guidance in dashboard & follows up)
```

---

## 👥 Demo Test Accounts (Pre-Seeded & Ready to Test)

The database automatically seeds realistic rural healthcare data on first run. You can also use the **1-Click Demo Login** buttons on the login page:

| Role | Name | Email | Password | Location / Specialization |
| :--- | :--- | :--- | :--- | :--- |
| **ASHA Worker** | Anita Devi | `anita.devi@aasha.in` | `aasha123` | Village Madhopur, Bahraich, UP (Assigned to Dr. Rajesh Sharma) |
| **ASHA Worker** | Sunita Yadav | `sunita.yadav@aasha.in` | `aasha123` | Village Shivpur, Bahraich, UP (Assigned to Dr. Priya Verma) |
| **Doctor** | Dr. Rajesh Sharma | `dr.sharma@phc.in` | `aasha123` | Rupaidiha Primary Health Centre (PHC), Bahraich |
| **Doctor** | Dr. Priya Verma | `dr.priya@chc.in` | `aasha123` | Bhinga Community Health Centre (CHC), Shravasti |

---

## 🏗️ Technology Stack

- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons
- **Backend**: Python 3.12, Flask 3.1
- **Database**: SQLite3 (`database.db`) via Flask-SQLAlchemy (PostgreSQL compatible)
- **AI & NLP**:
  - **Speech-to-Text**: Browser Web Speech API (`hi-IN`, `en-IN`, `en-US`), HTML5 MediaRecorder (audio upload & playback)
  - **Clinical Information Extraction**: Dual-engine (Google Gemini API support via `GEMINI_API_KEY`, backed by comprehensive rural clinical NLP regex/parser for Hindi & English medical vocabulary)
  - **Smart Triage System**: Clinical rule-based warning engine based on National Health Mission (NHM) and IMNCI guidelines.

---

## 📁 Project Structure

```
AASHA/
│
├── app.py                      # Flask Application factory & database seeder
├── config.py                   # Configuration settings (Database, Uploads, Keys)
├── requirements.txt            # Python dependencies
├── database.db                 # SQLite database
│
├── models/                     # Database Models (All 9 required tables)
│   ├── __init__.py             # SQLAlchemy instance
│   ├── user.py                 # Users, ASHA_Workers, Doctors
│   ├── patient.py              # Patients
│   └── report.py               # Patient_Reports, Voice_Transcriptions, 
│                               # AI_Summaries, Doctor_Responses, Notifications
│
├── routes/                     # Blueprint Route Handlers
│   ├── __init__.py             # Blueprints export
│   ├── auth.py                 # Login, Registration, Demo Login, Role Decorators
│   ├── worker.py               # ASHA Worker Dashboard & Profile
│   ├── doctor.py               # Doctor Dashboard, Triage Queue & Guidance
│   ├── patients.py             # Patient Registration & Longitudinal History
│   └── reports.py              # Voice Studio, AI APIs, Audio Serving, Notifs
│
├── services/                   # Business Logic & Clinical Engines
│   ├── __init__.py
│   ├── triage.py               # Clinical Warning Rules & Priority Classification
│   ├── ai_extraction.py        # Multilingual Clinical NLP & Gemini Extraction
│   ├── speech_to_text.py       # Audio Storage & Preset Scenario Library
│   └── notifications.py        # Bidirectional Real-Time Alert Engine
│
├── templates/                  # Jinja2 HTML5 Templates
│   ├── base.html               # Shared layout, Nav, Notif drawer, Footer
│   ├── index.html              # Landing page with 4 pillars & role selector
│   ├── login.html              # Dual login with 1-click demo buttons
│   ├── register.html           # ASHA & Doctor registration tabs
│   ├── worker_dashboard.html   # Worker command centre & assigned doctor card
│   ├── doctor_dashboard.html   # Doctor triage dashboard with priority filters
│   ├── patient_register.html   # Patient registration with auto-generated ID
│   ├── patients_list.html      # Community patient directory
│   ├── patient.html            # Patient longitudinal timeline & visit history
│   ├── record_voice.html       # Voice recording studio & live AI preview
│   ├── report.html             # Full clinical report & doctor response form
│   ├── worker_profile.html     # Worker profile & doctor reassignment
│   ├── 404.html                # Friendly 404 handler
│   └── 500.html                # Friendly 500 handler
│
├── static/                     # Static UI Assets
│   ├── css/
│   │   └── style.css           # Custom healthcare CSS theme & animations
│   └── js/
│       ├── main.js             # Notification poller & UI helpers
│       └── voice_recorder.js   # Audio recording, Web Speech & AI preview
│
└── uploads/
    └── audio/                  # Saved patient voice audio files (.webm / .wav)
```

---

## 🗄️ Database Tables (All 9 Implemented)

1. **`users`**: Authentication, hashed credentials, roles (`asha_worker`, `doctor`), contact.
2. **`asha_workers`**: Village, district, state, assigned doctor link.
3. **`doctors`**: Medical registration number, specialization, hospital/PHC affiliation.
4. **`patients`**: Auto-generated patient ID (`ASH-PAT-XXXX`), demographics, pregnancy status, pre-existing conditions.
5. **`patient_reports`**: Core report linking patient, reporting worker, assigned doctor, triage priority (`Urgent`, `Moderate`, `Routine`), and status.
6. **`voice_transcriptions`**: Audio filename, path, raw transcript, edited transcript, language.
7. **`ai_summaries`**: Extracted symptoms JSON, duration, observations, pregnancy notes, medicines, structured bulleted summary, and clinical triage rationale.
8. **`doctor_responses`**: Clinical guidance text, recommended action, updated status, doctor timestamp.
9. **`notifications`**: Bidirectional alerts between doctors and workers with unread badges.

---

## 🚀 How to Run the Project Locally

### 1. Prerequisites
Ensure Python 3.10+ is installed on your computer.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Flask Web Application
```bash
python app.py
```

### 4. Access the Application
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🧪 Testing the Complete Workflow in Under 2 Minutes

1. **Visit Landing Page**: Go to `http://127.0.0.1:5000`.
2. **1-Click Login as ASHA Worker**: Click **"Demo ASHA Worker"** (Anita Devi).
3. **Record Voice**: Click **"Record Patient Voice"**.
   - Select patient **Ramesh Kumar** (or click one of the 1-Click Preset Scenarios on the right, e.g., *"High Fever & Breathlessness"*).
   - Alternatively, click the microphone button to record audio in Hindi or English using your browser mic.
   - Review the live transcription and click **"Preview AI Triage"** to see extracted symptoms and urgent warnings in real time.
   - Click **"Submit Report to Assigned Doctor"**.
4. **Switch to Doctor Portal**:
   - Logout and click **"Demo Doctor"** (Dr. Rajesh Sharma).
   - Observe the new **Urgent Case Alert** in the notification bell and the highlighted row in the **Urgent Queue**.
   - Click **"Review & Respond"**.
   - Listen to the audio / read the transcript, and click any Quick Action preset (e.g., *"108 Ambulance Referral"* or type guidance).
   - Click **"Transmit Guidance to ASHA Worker"**.
5. **Switch Back to ASHA Worker**:
   - Log back in as Anita Devi.
   - Notice the green notification badge: Dr. Rajesh Sharma has provided clinical guidance.
   - Open the case to see the doctor's instructions.
6. **Inspect Patient History**:
   - Go to **"My Patients"** ➔ click on **Ramesh Kumar**.
   - View the complete chronological longitudinal timeline showing every previous visit, voice recording, AI summary, and doctor guidance!

---

## 🛡️ Clinical Safety Disclaimer

**AASHA is an AI-assisted documentation and triage prioritization tool.** It does **NOT** provide autonomous medical diagnosis or prescribe medications. Emergency warnings and clinical directions are supervised by qualified Medical Officers.
