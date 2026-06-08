"""Encrypted health record persistence using SQLCipher.

Stores triage sessions, user health history (with consent), and
wearable data snapshots. All data is encrypted at rest with AES-256-GCM
before being written to SQLCipher for double-layer protection.

Rule M-5: No raw symptom descriptions or wearable readings are persisted
beyond the active session without explicit user consent.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Integer, LargeBinary, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from storage.encryption import EncryptionKey, decrypt, encrypt


# ── ORM Base ────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class EncryptedHealthRecord(Base):
    __tablename__ = "encrypted_health_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id_hash = Column(String(64), nullable=False, index=True)
    record_type = Column(String(32), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    payload = Column(LargeBinary, nullable=False)


# ── Store / Load API ────────────────────────────────────────────────

class HealthRecordStore:
    def __init__(self, db_path: str, encryption_key: EncryptionKey) -> None:
        engine_url = f"sqlite+pysqlcipher://:{encryption_key.to_base64()}@{db_path}?cipher=aes-256-cbc&kdf_iter=64000"
        self._engine = create_engine(engine_url, echo=False)
        Base.metadata.create_all(self._engine)
        self._Session = sessionmaker(bind=self._engine)
        self._key = encryption_key

    def store(
        self,
        user_id_hash: str,
        record_type: str,
        data: dict[str, Any],
    ) -> int:
        import json

        plaintext = json.dumps(data).encode("utf-8")
        encrypted = encrypt(plaintext, self._key)

        with self._Session() as session:
            record = EncryptedHealthRecord(
                user_id_hash=user_id_hash,
                record_type=record_type,
                payload=encrypted,
            )
            session.add(record)
            session.commit()
            return record.id

    def load(self, record_id: int) -> dict[str, Any] | None:
        import json

        with self._Session() as session:
            record = session.get(EncryptedHealthRecord, record_id)
            if record is None:
                return None
            try:
                plaintext = decrypt(bytes(record.payload), self._key)
                return json.loads(plaintext.decode("utf-8"))
            except Exception:
                return None

    def list_by_user(self, user_id_hash: str, limit: int = 50) -> list[dict[str, Any]]:
        from sqlalchemy import select

        with self._Session() as session:
            stmt = (
                select(EncryptedHealthRecord)
                .where(EncryptedHealthRecord.user_id_hash == user_id_hash)
                .order_by(EncryptedHealthRecord.created_at.desc())
                .limit(limit)
            )
            rows = session.execute(stmt).scalars().all()
            return [
                {
                    "id": r.id,
                    "record_type": r.record_type,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]

    def delete(self, record_id: int) -> bool:
        with self._Session() as session:
            record = session.get(EncryptedHealthRecord, record_id)
            if record is None:
                return False
            session.delete(record)
            session.commit()
            return True

    def delete_all_for_user(self, user_id_hash: str) -> int:
        from sqlalchemy import delete

        with self._Session() as session:
            stmt = delete(EncryptedHealthRecord).where(
                EncryptedHealthRecord.user_id_hash == user_id_hash
            )
            result = session.execute(stmt)
            session.commit()
            return result.rowcount
