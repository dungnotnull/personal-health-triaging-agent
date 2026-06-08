# PHTA Architecture

## Overview

PHTA is a **local-first**, **privacy-preserving** clinical triage agent. It combines rule-based emergency detection, natural language processing, machine learning triage classification, and wearable device integration to provide structured health screening recommendations.

## Architecture Principles

1. **Safety first** — Red flag screener runs synchronously before any LLM call
2. **Local-first** — All health data stays on-device by default
3. **Hybrid intelligence** — Rules handle safety-critical edges; ML handles nuanced presentations
4. **Conservative bias** — When uncertain, escalate to more urgent triage level
5. **Medical accountability** — Clinical advisor review required for rule changes
6. **Vietnam-first** — Vietnamese language, food database, disease priorities
7. **Offline capable** — Core triage works without internet (Llama-3.1-8B local)

## System Layers

```
┌─────────────────────────────────────────┐
│  UI Layer (Streamlit / React Native)     │
├─────────────────────────────────────────┤
│  API Layer (FastAPI + WebSocket)         │
├─────────────────────────────────────────┤
│  Agent Orchestrator                      │
│  ┌─────────┬──────────┬──────────────┐  │
│  │ Red Flag│ Intake   │ Triage Class │  │
│  │ Screener│ (LLM+QE) │ (ML+Rules)   │  │
│  └─────────┴──────────┴──────────────┘  │
├─────────────────────────────────────────┤
│  NLP Layer (NER, STT, TTS, Lang Detect) │
├─────────────────────────────────────────┤
│  Clinical Layer (Rules, Ontology, Trees)│
├─────────────────────────────────────────┤
│  Wearable Layer (Device Adapters)        │
├─────────────────────────────────────────┤
│  Storage Layer (Encrypted SQLite)        │
└─────────────────────────────────────────┘
```

## Data Flow

1. User input (text/voice) → NLP Layer → Structured symptom data
2. Red Flag Screener checks for emergencies (O(1), <200ms)
3. If no emergency: Wearable data pulled (async)
4. Structured interview via LLM + question tree (5-10 questions)
5. Triage classifier: ML prediction + rule engine override
6. Output: Emergency alert OR monitoring plan

## Security

- AES-256-GCM encryption at rest for all health data
- SQLCipher for database-level encryption
- No telemetry, no cloud dependency
- User-controlled data retention and deletion
- OAuth tokens stored in OS-level keychain

## Deployment

```bash
# Local development
pip install -e .[all]
phta                    # CLI chat interface
phta-api                # FastAPI server

# Docker
docker compose up api   # API + Ollama
docker compose --profile voice up  # + Whisper STT
```
