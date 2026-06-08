"""API route stubs for triage, wearable, monitoring, and health record endpoints.

These are thin route registrations that delegate to the core modules.
Phase 0: skeleton only — real business logic comes in Phases 1-3.
"""

from api import routes

# Routes are imported and registered in api/server.py
# These files exist as namespace packages for future expansion:
#   routes/triage.py    — extended triage-specific endpoints
#   routes/wearable.py  — wearable OAuth callbacks, data sync
#   routes/monitoring.py — monitoring plan management
#   routes/health_record.py — encrypted health record CRUD
