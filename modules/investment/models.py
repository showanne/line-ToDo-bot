# modules/investment/models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, func, case
from sqlalchemy.orm import relationship
from core.database import Base, db_session, get_or_create

class InvestmentAsset(Base):
    __tablename__ = "investment_assets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    symbol = Column(String, nullable=False)        # 標的代碼 (例: 2330, AAPL, BTC, 0050)
    name = Column(String, nullable=False)          # 標的名稱 (例: 台積電, 蘋果)
    asset_type = Column(String, default="台股")    # 資產類別 (台股 / 美股 / 加密貨幣 / 基金 / 債券)
    quantity = Column(Float, default=0.0)          # 持有數量/股數
    cost_price = Column(Float, default=0.0)        # 平均成本單價
    current_price = Column(Float, default=0.0)     # 最新現價
    currency = Column(String, default="TWD")       # 幣別 (TWD / USD)
    purchase_place = Column(String, nullable=True)  # 購買地點
    note = Column(Text)                            # 備註
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    updated_at = Column(String, default=lambda: datetime.now().isoformat())

class InvestmentTransaction(Base):
    __tablename__ = "investment_transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    asset_id = Column(Integer, ForeignKey('investment_assets.id', ondelete='CASCADE'), nullable=False)
    tx_type = Column(String, nullable=False)       # BUY / SELL / DIVIDEND
    quantity = Column(Float, default=0.0)
    price = Column(Float, default=0.0)
    fee = Column(Float, default=0.0)
    tx_date = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d"))
    note = Column(Text)

# --- CRUD API Helper Functions ---

def add_or_update_asset(user_id, symbol, name, asset_type, quantity, price, currency="TWD", note=None, purchase_place=None):
    session = db_session()
    try:
        asset = session.query(InvestmentAsset).filter(
            InvestmentAsset.user_id == user_id,
            InvestmentAsset.symbol == symbol.upper()
        ).first()

        if asset:
            # 重新計算平均成本
            total_qty = asset.quantity + quantity
            if total_qty > 0:
                asset.cost_price = ((asset.quantity * asset.cost_price) + (quantity * price)) / total_qty
                asset.quantity = total_qty
            asset.current_price = price
            asset.updated_at = datetime.now().isoformat()
            if note: asset.note = note
            if purchase_place: asset.purchase_place = purchase_place
        else:
            asset = InvestmentAsset(
                user_id=user_id,
                symbol=symbol.upper(),
                name=name,
                asset_type=asset_type,
                quantity=quantity,
                cost_price=price,
                current_price=price,
                currency=currency,
                purchase_place=purchase_place,
                note=note
            )
            session.add(asset)
            session.flush()

        # 寫入交易紀錄
        tx = InvestmentTransaction(
            user_id=user_id,
            asset_id=asset.id,
            tx_type="BUY",
            quantity=quantity,
            price=price,
            note=note
        )
        session.add(tx)
        session.commit()
        return asset.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def update_asset_price(user_id, symbol, current_price):
    session = db_session()
    try:
        asset = session.query(InvestmentAsset).filter(
            InvestmentAsset.user_id == user_id,
            InvestmentAsset.symbol == symbol.upper()
        ).first()
        if not asset: return False
        asset.current_price = current_price
        asset.updated_at = datetime.now().isoformat()
        session.commit()
        return True
    except:
        session.rollback()
        return False
    finally:
        session.close()

def delete_asset(user_id, asset_id):
    session = db_session()
    try:
        asset = session.query(InvestmentAsset).filter(
            InvestmentAsset.id == asset_id,
            InvestmentAsset.user_id == user_id
        ).first()
        if not asset: return False
        session.delete(asset)
        session.commit()
        return True
    except:
        session.rollback()
        return False
    finally:
        session.close()

def list_assets(user_id, asset_type=None):
    session = db_session()
    try:
        query = session.query(InvestmentAsset).filter(InvestmentAsset.user_id == user_id)
        if asset_type:
            query = query.filter(InvestmentAsset.asset_type == asset_type)
        assets = query.order_by(InvestmentAsset.asset_type, InvestmentAsset.symbol).all()

        result = []
        for a in assets:
            cost_val = a.quantity * a.cost_price
            market_val = a.quantity * a.current_price
            profit = market_val - cost_val
            profit_rate = (profit / cost_val * 100) if cost_val > 0 else 0.0

            result.append({
                "id": a.id,
                "symbol": a.symbol,
                "name": a.name,
                "asset_type": a.asset_type,
                "quantity": a.quantity,
                "cost_price": a.cost_price,
                "current_price": a.current_price,
                "currency": a.currency,
                "purchase_place": a.purchase_place,
                "cost_value": cost_val,
                "market_value": market_val,
                "profit": profit,
                "profit_rate": profit_rate,
                "note": a.note
            })
        return result
    finally:
        session.close()

def get_asset_detail(user_id, symbol):
    assets = list_assets(user_id)
    symbol = symbol.upper()
    for asset in assets:
        if asset["symbol"] == symbol:
            return asset
    return None

def import_data_from_sql(sql_text):
    from sqlalchemy import text
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
        (InvestmentAsset, "investment_assets"),
        (InvestmentTransaction, "investment_transactions")
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


def export_data_as_json(user_id=None):
    session = db_session()
    try:
        assets_query = session.query(InvestmentAsset)
        tx_query = session.query(InvestmentTransaction)
        if user_id:
            assets_query = assets_query.filter(InvestmentAsset.user_id == user_id)
            tx_query = tx_query.filter(InvestmentTransaction.user_id == user_id)

        assets = assets_query.order_by(InvestmentAsset.id).all()
        transactions = tx_query.order_by(InvestmentTransaction.id).all()

        return {
            "assets": [
                {
                    "id": a.id,
                    "user_id": a.user_id,
                    "symbol": a.symbol,
                    "name": a.name,
                    "asset_type": a.asset_type,
                    "quantity": a.quantity,
                    "cost_price": a.cost_price,
                    "current_price": a.current_price,
                    "currency": a.currency,
                    "purchase_place": a.purchase_place,
                    "note": a.note,
                    "created_at": a.created_at,
                    "updated_at": a.updated_at,
                }
                for a in assets
            ],
            "transactions": [
                {
                    "id": t.id,
                    "user_id": t.user_id,
                    "asset_id": t.asset_id,
                    "tx_type": t.tx_type,
                    "quantity": t.quantity,
                    "price": t.price,
                    "fee": t.fee,
                    "tx_date": t.tx_date,
                    "note": t.note,
                }
                for t in transactions
            ]
        }
    finally:
        session.close()


def get_portfolio_summary(user_id):
    assets = list_assets(user_id)
    total_cost = sum(a["cost_value"] for a in assets)
    total_market_val = sum(a["market_value"] for a in assets)
    total_profit = total_market_val - total_cost
    total_profit_rate = (total_profit / total_cost * 100) if total_cost > 0 else 0.0

    # 按資產類別分組
    by_type = {}
    for a in assets:
        t = a["asset_type"]
        if t not in by_type: by_type[t] = 0.0
        by_type[t] += a["market_value"]

    return {
        "total_cost": total_cost,
        "total_market_value": total_market_val,
        "total_profit": total_profit,
        "total_profit_rate": total_profit_rate,
        "asset_count": len(assets),
        "by_type": by_type,
        "assets": assets
    }
