from datetime import datetime
from sqlalchemy import Column, Integer, String, JSON, DateTime, text
from core.database import Base, db_session, engine


class CardProfile(Base):
    __tablename__ = "card_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False, unique=True)
    profile_data = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CardShareLog(Base):
    __tablename__ = "card_share_logs"

    id = Column(Integer, primary_key=True, index=True)
    sender_user_id = Column(String, index=True, nullable=False)
    recipient_user_id = Column(String, index=True, nullable=False)
    profile_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


def ensure_card_tables():
    try:
        Base.metadata.create_all(bind=engine, tables=[CardProfile.__table__, CardShareLog.__table__])
    except Exception:
        pass


ensure_card_tables()


def _normalize_payload(payload):
    if not payload:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    safe = {
        "name": (payload.get("name") or "未填寫").strip() or "未填寫",
        "title": (payload.get("title") or "未填寫").strip() or "未填寫",
        "company": (payload.get("company") or "未填寫").strip() or "未填寫",
        "phone": (payload.get("phone") or "未填寫").strip() or "未填寫",
        "email": (payload.get("email") or "未填寫").strip() or "未填寫",
        "website": (payload.get("website") or "未填寫").strip() or "未填寫",
        "note": (payload.get("note") or "未填寫").strip() or "未填寫",
    }
    return safe


def upsert_profile(user_id, payload):
    ensure_card_tables()
    session = db_session()
    try:
        normalized = _normalize_payload(payload)
        profile = session.query(CardProfile).filter(CardProfile.user_id == user_id).first()
        if profile:
            profile.profile_data = normalized
            profile.updated_at = datetime.utcnow()
        else:
            session.add(CardProfile(user_id=user_id, profile_data=normalized, updated_at=datetime.utcnow()))
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_profile(user_id):
    ensure_card_tables()
    session = db_session()
    try:
        row = session.query(CardProfile).filter(CardProfile.user_id == user_id).first()
        if not row:
            return {
                "name": "未填寫",
                "title": "未填寫",
                "company": "未填寫",
                "phone": "未填寫",
                "email": "未填寫",
                "website": "未填寫",
                "note": "未填寫",
            }
        return _normalize_payload(row.profile_data)
    finally:
        session.close()


def record_share(sender_user_id, recipient_user_id, payload):
    ensure_card_tables()
    session = db_session()
    try:
        normalized = _normalize_payload(payload)
        log = CardShareLog(
            sender_user_id=sender_user_id,
            recipient_user_id=recipient_user_id,
            profile_data=normalized,
            created_at=datetime.utcnow(),
        )
        session.add(log)
        session.commit()
        return log.id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def list_share_history(sender_user_id, limit=20):
    ensure_card_tables()
    session = db_session()
    try:
        rows = session.query(CardShareLog).filter(CardShareLog.sender_user_id == sender_user_id).order_by(CardShareLog.created_at.desc()).limit(limit).all()
        return [
            {
                "id": row.id,
                "sender_user_id": row.sender_user_id,
                "recipient_user_id": row.recipient_user_id,
                "profile": _normalize_payload(row.profile_data),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def _sql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, datetime):
        return f"'{value.isoformat()}'"
    safe_val = str(value).replace("'", "''")
    return f"'{safe_val}'"


def export_data_as_sql(user_id=None):
    ensure_card_tables()
    session = db_session()
    sql_statements = []
    tables = [
        (CardProfile, "card_profiles"),
        (CardShareLog, "card_share_logs"),
    ]
    try:
        for model, table_name in tables:
            query = session.query(model)
            if user_id:
                query = query.filter(model.user_id == user_id)
            rows = query.all()
            for row in rows:
                columns = [c.name for c in model.__table__.columns]
                values = [_sql_literal(getattr(row, col)) for col in columns]
                sql_statements.append(
                    f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(values)});"
                )
        return "\n".join(sql_statements)
    finally:
        session.close()


def import_data_from_sql(sql_text):
    ensure_card_tables()
    session = db_session()
    try:
        statements = []
        for raw_stmt in str(sql_text).split(";"):
            stmt = raw_stmt.strip()
            if not stmt or stmt.startswith("--"):
                continue
            statements.append(stmt)

        for stmt in statements:
            if stmt.upper().startswith("INSERT INTO"):
                session.execute(text(stmt))
        session.commit()
        return len(statements)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
