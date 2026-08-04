from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship, selectinload
from core.database import Base, db_session, get_or_create


quote_tag_map = Table(
    "quote_tag_map",
    Base.metadata,
    Column("quote_id", Integer, ForeignKey("quotes.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("quote_tags.id", ondelete="CASCADE"), primary_key=True),
)


class QuoteTag(Base):
    __tablename__ = "quote_tags"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    quotes = relationship("Quote", secondary=quote_tag_map, back_populates="tags")


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String, default="未填", nullable=True)
    speaker = Column(String, default="未填", nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    tags = relationship("QuoteTag", secondary=quote_tag_map, back_populates="quotes")


def _normalize_tags(tags):
    if not tags:
        return []
    if isinstance(tags, str):
        tags = [item.strip() for item in tags.split(",") if item.strip()]
    return [t.strip() for t in tags if str(t).strip()]


def add_quote(user_id, content, source=None, speaker=None, tags=None):
    session = db_session()
    try:
        clean_tags = _normalize_tags(tags)
        quote = Quote(
            user_id=user_id,
            content=content.strip(),
            source=(source or "未填").strip() or "未填",
            speaker=(speaker or "未填").strip() or "未填",
        )
        quote.tags = [
            get_or_create(session, QuoteTag, user_id=user_id, name=tag)
            for tag in clean_tags
        ]
        session.add(quote)
        session.commit()
        return quote.id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def update_quote(user_id, quote_id, content=None, source=None, speaker=None, tags=None):
    session = db_session()
    try:
        quote = session.query(Quote).filter(Quote.id == quote_id, Quote.user_id == user_id).first()
        if not quote:
            return False
        if content is not None:
            quote.content = content.strip()
        if source is not None:
            quote.source = (source or "未填").strip() or "未填"
        if speaker is not None:
            quote.speaker = (speaker or "未填").strip() or "未填"
        if tags is not None:
            clean_tags = _normalize_tags(tags)
            quote.tags = [
                get_or_create(session, QuoteTag, user_id=user_id, name=tag)
                for tag in clean_tags
            ]
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def delete_quote(user_id, quote_id):
    session = db_session()
    try:
        quote = session.query(Quote).filter(Quote.id == quote_id, Quote.user_id == user_id).first()
        if not quote:
            return False
        session.delete(quote)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_quote(user_id, quote_id):
    session = db_session()
    try:
        quote = (
            session.query(Quote)
            .options(selectinload(Quote.tags))
            .filter(Quote.id == quote_id, Quote.user_id == user_id)
            .first()
        )
        if not quote:
            return None
        return {
            "id": quote.id,
            "content": quote.content,
            "source": quote.source or "未填",
            "speaker": quote.speaker or "未填",
            "tags": [tag.name for tag in quote.tags],
        }
    finally:
        session.close()


def list_quotes(user_id, limit=20):
    session = db_session()
    try:
        return (
            session.query(Quote)
            .options(selectinload(Quote.tags))
            .filter(Quote.user_id == user_id)
            .order_by(Quote.created_at.desc())
            .limit(limit)
            .all()
        )
    finally:
        session.close()


def count_quotes(user_id):
    session = db_session()
    try:
        return session.query(Quote).filter(Quote.user_id == user_id).count()
    finally:
        session.close()


def list_quote_tags(user_id):
    session = db_session()
    try:
        return [tag.name for tag in session.query(QuoteTag).filter(QuoteTag.user_id == user_id).all()]
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
    session = db_session()
    sql_statements = []
    tables = [
        (QuoteTag, "quote_tags"),
        (Quote, "quotes")
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

        rel_results = session.execute(quote_tag_map.select()).all()
        for r in rel_results:
            sql_statements.append(
                f"INSERT INTO quote_tag_map (quote_id, tag_id) VALUES ({r[0]}, {r[1]});"
            )
        return "\n".join(sql_statements)
    finally:
        session.close()


def export_data_as_json(user_id=None):
    session = db_session()
    try:
        tags_query = session.query(QuoteTag)
        quotes_query = session.query(Quote).options(selectinload(Quote.tags))
        if user_id:
            tags_query = tags_query.filter(QuoteTag.user_id == user_id)
            quotes_query = quotes_query.filter(Quote.user_id == user_id)

        quote_tags = tags_query.order_by(QuoteTag.id).all()
        quotes = quotes_query.order_by(Quote.created_at.desc()).all()

        return {
            "quote_tags": [
                {
                    "id": tag.id,
                    "user_id": tag.user_id,
                    "name": tag.name,
                }
                for tag in quote_tags
            ],
            "quotes": [
                {
                    "id": quote.id,
                    "user_id": quote.user_id,
                    "content": quote.content,
                    "source": quote.source,
                    "speaker": quote.speaker,
                    "created_at": quote.created_at.isoformat() if quote.created_at else None,
                    "tags": [tag.name for tag in quote.tags],
                }
                for quote in quotes
            ]
        }
    finally:
        session.close()
