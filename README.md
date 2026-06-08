<h1 align="center">⚕️ PHTA — Personal Health Triaging Agent</h1>

<p align="center">
  <strong>AI-powered clinical triage nurse.<br/>Conducts structured symptom interviews, integrates wearable biosensor data,<br/>and provides evidence-based triage recommendations.</strong>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-features">Features</a> •
  <a href="#-safety">Safety</a> •
  <a href="#-usage">Usage</a> •
  <a href="#-contributing">Contributing</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue" alt="Python" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License" />
  <img src="https://img.shields.io/badge/status-pre--release-yellow" alt="Status" />
  <img src="https://img.shields.io/badge/platform-linux%20%7C%20macOS%20%7C%20windows-lightgrey" alt="Platform" />
</p>

---

> **⚠️ MEDICAL DISCLAIMER**
>
> PHTA is a **triage screening tool** — NOT a diagnostic device. It does not diagnose diseases, prescribe medications, or replace professional medical consultation. Always consult a qualified healthcare professional. If you are experiencing a medical emergency, call your local emergency number immediately.

---

## 🌟 Why PHTA?

| Problem | PHTA's Solution |
|---|---|
| Google symptoms → cyberchondria + anxiety | Structured, evidence-based clinical interview |
| 40% delay care they need, 30% seek care they don't | Four-level triage with clear action guidance |
| Wearable data goes clinically unused | Integrates HR, SpO2, HRV, sleep into triage decisions |
| Most health AI is English-only | Vietnam-first, with Vietnamese language + food database |
| Rural populations lack clinic access | Offline-capable, local-first architecture |
| Healthcare system overload (120-180% capacity) | Reduces unnecessary ER visits via structured screening |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE                           │
│        Web Chat (Streamlit) / Mobile / Voice                │
└────────────────────────┬────────────────────────────────────┘
                         │ text / voice
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     NLP LAYER                               │
│  Whisper STT → Language Detection → Medical NER → Profile  │
└────────────────────────┬────────────────────────────────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
┌─────────────────────┐  ┌─────────────────────────────────┐
│  RED FLAG SCREENER  │  │      WEARABLE DATA LAYER         │
│  (rule-based, <1ms) │  │  Apple Health / Google Health /  │
│  ALWAYS runs first  │  │  Fitbit / Garmin / BLE Oximeter  │
└──────────┬──────────┘  └───────────────┬───────────────────┘
           │                             │
           └──────────┬──────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              CLINICAL INTERVIEW ENGINE                      │
│  Question Tree Engine + LLM (Claude / Llama-3)             │
│  5–10 structured, branching clinical questions             │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              TRIAGE CLASSIFICATION ENGINE                   │
│  Hybrid: ML Classifier (LightGBM) + Evidence-Based Rules   │
│  Rules always override ML for safety-critical scenarios    │
└──────────┬──────────────────────┬───────────────────────────┘
           │                      │
    Level 1-2 (Urgent)    Level 3-4 (Monitor)
           │                      │
           ▼                      ▼
    Emergency Alert      ┌─────────────────────────┐
    + Nearest ER         │   MONITORING PLAN        │
    + Emergency Numbers  │   - Check-in reminders   │
                         │   - Wearable alerts      │
                         │   - Nutrition guidance   │
                         │   - Escalation triggers  │
                         │   - Progress tracking    │
                         └─────────────────────────┘
```

### Triage Levels

| Level | Color | Name | Action |
|---|---|---|---|
| 1 | 🔴 RED | EMERGENCY | Call emergency services / go to ER immediately |
| 2 | 🟠 ORANGE | URGENT | Go to urgent care / clinic today |
| 3 | 🟡 YELLOW | SEMI-URGENT | Book appointment this week |
| 4 | 🟢 GREEN | NON-URGENT | Monitor at home, follow-up in 7+ days |

---

## ✨ Features

### 🛡️ Safety-Critical
- **Red flag screener** runs synchronously before any LLM call — rule-based, zero hallucination risk
- **7 emergency categories** with Vietnamese + English keyword matching
- **Wearable-triggered emergencies** — SpO₂ < 92%, HR > 150/< 40, temp > 40°C automatically trigger EMERGENCY
- **Mental health crisis protocol** with Vietnam-specific hotline (1800 599 920)
- **Conservative triage bias** — when uncertain, always recommends more urgent care
- **100% pass rate** on 68 emergency validation fixtures

### 🧠 NLP & Language
- **Medical NER** extracts 12 entity types from free text (symptoms, body locations, severity, duration, medications...)
- **Vietnamese + English** support with auto-detection
- **Whisper STT** for voice input (Vietnamese primary)
- **Edge TTS** for voice output (natural Vietnamese voice)
- **Zero model dependency** baseline — works fully offline with regex + dictionary engine

### 📊 Clinical Interview
- **6 branching question trees** — headache, chest pain, fever, abdominal pain, respiratory, general
- **Max 10 questions** per interview (fatigue limit)
- **Vietnamese + English** questions in every tree
- **Specialty routing** to 15+ medical specialties

### ⌚ Wearable Integration
- **5 device adapters** — Apple HealthKit, Google Health Connect, Fitbit (OAuth 2.0), Garmin, BLE
- **Cross-platform normalizer** with unit conversion and data freshness tracking
- **Biosignal clinical interpretation** — HRV decline, SpO₂ trends, sleep deficit analysis

### 🍜 Nutrition Engine
- **35+ Vietnamese foods** with full nutritional data + Open Food Facts API
- **9 condition-specific** nutrition plans (fever, headache, cough, abdominal pain, fatigue, hypertension, diabetes...)
- **3-day meal plans** with cultural appropriateness (phở, cháo, canh chua, gỏi cuốn...)
- **10 food-condition contraindications** + 3 medication interaction rules

### 📈 Monitoring & Trends
- **Condition-specific check-in schedules** (fever: 4h, headache: 8h, respiratory: 6h)
- **Trend analyzer** — improving / stable / worsening detection
- **Alert manager** with threshold-based escalation
- **Longitudinal health timeline** with encrypted persistence

### 📚 Self-Learning Knowledge
- **PubMed E-utilities** crawler with rate limiting and caching
- **WHO Disease Outbreak News** RSS parsing
- **CDC clinical guidelines** scraper
- **Vietnam MOH** (moh.gov.vn) crawler
- **Clinical summarizer** with 7 action extractors
- **Human-in-the-loop** approval workflow for rule changes

### 🔐 Privacy & Security
- **Local-first** — no cloud dependency, no telemetry
- **AES-256-GCM** encryption at rest for all health data
- **SQLCipher** double-layer database encryption
- **Session-only** data by default — user-controlled persistence
- **GDPR Art. 9 + Vietnam Decree 13/2023/NĐ-CP** compliant

### 🌐 API
- **FastAPI** REST server with OpenAPI spec
- **WebSocket** real-time chat triage
- **Route modules** for triage, wearables, monitoring, health records

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Optional: Ollama (for local LLM), Docker (for containerized deployment)

### Installation

```bash
# Clone
git clone https://github.com/dungnotnull/personal-health-triaging-agent.git
cd personal-health-triaging-agent

# Install with all features
pip install -e .[all]

# Or minimal install
pip install -e .
```

### Run

```bash
# CLI chat interface
phta

# API server
phta-api

# Streamlit web UI
streamlit run ui/app.py

# Generate encryption key
phta-keygen

# Run knowledge crawler
phta-crawler
```

### Docker

```bash
# Start API + Ollama
docker compose up api

# With voice support
docker compose --profile voice up

# Pull LLM model
docker compose exec ollama ollama pull llama3.1:8b
```

### Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

---

## 📂 Repository Structure

```
personal-health-triaging-agent/
├── agent/                           # Core triage agent
│   ├── orchestrator.py              # Main agent loop
│   ├── red_flag_screener.py         # Emergency detection (always first)
│   ├── triage_classifier.py         # ML + rules hybrid classifier
│   ├── intake.py                    # Structured interview agent
│   ├── question_engine.py           # Branching question trees
│   └── session_manager.py           # Conversation state
│
├── clinical/                        # Clinical knowledge & logic
│   ├── red_flags.yaml               # Emergency keyword definitions (vi/en)
│   ├── triage_rules.yaml            # Evidence-based triage decision rules
│   ├── specialty_mapping.yaml       # Symptom → specialist routing
│   ├── symptom_ontology.py          # SNOMED-CT / ICD-11 mapping (200+ codes)
│   ├── config.py                    # Centralized configuration
│   ├── question_trees/              # 6 branching interview trees
│   └── fixtures/                    # Clinical validation cases (175 total)
│
├── wearable/                        # Wearable device integrations
│   ├── base_adapter.py              # Abstract adapter interface
│   ├── normalizer.py                # Cross-platform data normalizer
│   ├── fitbit.py                    # Fitbit (OAuth 2.0 + Web API)
│   ├── google_health.py             # Google Health Connect
│   ├── garmin.py                    # Garmin Health API
│   ├── apple_health.py              # Apple HealthKit webhook
│   └── generic_bluetooth.py         # BLE pulse oximeter / BP cuff
│
├── nlp/                             # NLP & voice processing
│   ├── medical_ner.py               # Medical entity extraction (12 types)
│   ├── symptom_extractor.py         # Structured symptom profiles
│   ├── severity_parser.py           # Severity/duration/onset parsing
│   ├── language_detector.py         # Vietnamese/English auto-detect
│   └── voice/
│       ├── stt.py                   # Whisper speech-to-text
│       └── tts.py                   # Edge TTS / Coqui text-to-speech
│
├── monitoring/                      # Ongoing health monitoring
│   ├── scheduler.py                 # Check-in reminders
│   ├── tracker.py                   # Health timeline
│   ├── trend_analyzer.py            # Improvement/deterioration detection
│   └── alert_manager.py             # Escalation alerts
│
├── nutrition/                       # Nutrition & lifestyle
│   ├── recommender.py               # Condition-based nutrition engine
│   ├── meal_planner.py              # 3-day meal plan generator
│   ├── food_db.py                   # Vietnamese + international food DB
│   └── contraindications.py         # Food-condition warnings
│
├── knowledge_crawler/               # Self-learning knowledge system
│   ├── crawler.py                   # PubMed, WHO, CDC, Vietnam MOH
│   ├── clinical_summarizer.py       # Actionable rule extraction
│   ├── updater.py                   # Knowledge brain writer
│   └── schedule.py                  # Weekly auto-update
│
├── storage/                         # Encrypted data persistence
│   ├── encryption.py                # AES-256-GCM helpers
│   └── health_record_store.py       # SQLCipher-encrypted records
│
├── api/                             # REST/WebSocket API
│   ├── server.py                    # FastAPI server
│   └── routes/                      # Triage, wearable, monitoring, health
│
├── ui/                              # Web UI
│   └── app.py                       # Streamlit chat interface
│
├── tests/                           # Validation & testing
│   └── harness.py                   # Clinical validation runner
│
├── scripts/
│   └── ci_red_flag_gate.py          # CI emergency safety gate
│
├── docs/                            # Documentation
│   ├── architecture.md
│   ├── medical_disclaimer.md
│   ├── wearable_setup_guide.md
│   └── clinical_validation_protocol.md
│
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.whisper
├── pyproject.toml
├── requirements.txt
├── .env.example
├── CLAUDE.md                        # AI agent instruction set
├── PROJECT-detail.md                # Full technical specification
├── PROJECT-DEVELOPMENT-PHASE-TRACKING.md
└── SECOND-KNOWLEDGE-BRAIN.md        # Living clinical knowledge base
```

---

## 🧪 Validation

PHTA includes a clinical validation harness that tests against 175 curated cases:

```bash
# Full validation report
python tests/harness.py --report

# Emergency safety gate only (must be 100%)
python scripts/ci_red_flag_gate.py

# False negative gate only
python tests/harness.py --false-negatives

# Symptom accuracy
python tests/harness.py --symptoms
```

### Current Results

| Metric | Result | Target |
|---|---|---|
| Red flag emergency detection | **100%** | 100% |
| False negative rate (missed emergencies) | **0%** | 0% |
| Overall triage accuracy (rule-based) | 56% | ≥ 85% (with ML) |
| Emergency fixture count | 28 | 50+ |
| Total clinical fixtures | 175 | 500+ |

> **Note:** 56% overall accuracy reflects the rule-based classifier without ML training. The emergency gates achieve 100%. ML model training will improve Levels 2-4 accuracy to meet the ≥ 85% target.

---

## 🛡️ Safety

### Design Principles

1. **Safety-first** — Red flag screener runs synchronously, before any LLM call
2. **No LLM for emergencies** — Rule-based only; zero hallucination risk for critical decisions
3. **Conservative bias** — When uncertain between two triage levels, always recommend the more urgent one
4. **Human-in-the-loop** — Clinical rule changes require physician approval
5. **Never diagnoses** — PHTA is a screening/triage tool, not a diagnostic device

### Emergency Detection

The red flag screener checks for 9 emergency categories across Vietnamese and English:

- Cardiovascular (chest pain, MI, aortic dissection)
- Neurological / Stroke (FAST signs, thunderclap headache)
- Respiratory (severe dyspnea, cyanosis, SpO₂ emergencies)
- Anaphylaxis (throat swelling, breathing difficulty after exposure)
- Mental health crisis (suicidal ideation, self-harm)
- Hemorrhage (massive bleeding, hematemesis, hemoptysis)
- Sepsis / Shock (cold extremities, rigors, confusion)
- Endocrine emergency (thyroid storm, DKA)
- Vietnam-specific (severe dengue, rabies, HFMD with CNS signs, snake bite, leptospirosis)

---

## 🌍 Vietnam-First Design

PHTA is built with Vietnam as the primary target:

- 🇻🇳 **Vietnamese language** — NER, question trees, food database, all bilingual
- 🏥 **Vietnam emergency numbers** — 115 (ambulance), 1800 599 920 (mental health crisis)
- 🦟 **Vietnam-specific diseases** — Dengue, rabies, HFMD, Japanese Encephalitis, leptospirosis, TB
- 🍜 **Vietnamese food culture** — Cháo, phở, gỏi cuốn, canh chua, nước dừa, trà gừng...
- 📋 **Vietnam MOH** integration — Crawls moh.gov.vn for local health updates
- 🔒 **Vietnam privacy law** — Compliant with Decree 13/2023/NĐ-CP

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

## ⚠️ Important

PHTA is **pre-release software**. It has not been reviewed by a licensed physician. The emergency detection gates pass at 100%, but the overall triage accuracy (Levels 2-4) requires ML model training to meet clinical standards. **Do not rely on PHTA for medical decisions without clinical validation.**

---

## 👥 Contributing

Contributions are welcome. Please read [CLAUDE.md](CLAUDE.md) for architecture guidelines and medical safety constraints before contributing.

### Medical Safety Rules for Contributors

1. Never remove or relax a red flag pattern
2. Always test against `clinical/fixtures/red_flag_cases.yaml`
3. The CI gate blocks merge if any emergency fixture fails
4. Clinical rule changes require documentation and review
5. Never use the word "diagnosis" in user-facing output

---

<p align="center">
  <sub>Built with ❤️ for accessible healthcare. Vietnam-first. Privacy-first. Safety-always.</sub>
</p>
