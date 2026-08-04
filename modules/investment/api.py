# modules/investment/api.py
from flask import Blueprint, request, jsonify
from modules.investment import models as db

investment_api = Blueprint("investment_api", __name__)

@investment_api.get("/api/investment/summary")
def get_summary_api():
    try:
        user_id = request.args.get("user_id", "default_user")
        summary = db.get_portfolio_summary(user_id)
        return jsonify(summary), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@investment_api.get("/api/investment/assets")
def get_assets_api():
    try:
        user_id = request.args.get("user_id", "default_user")
        asset_type = request.args.get("type")
        assets = db.list_assets(user_id, asset_type=asset_type)
        return jsonify(assets), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@investment_api.post("/api/investment/add")
def add_asset_api():
    data = request.json or {}
    user_id = data.get("user_id", "default_user")
    symbol = data.get("symbol", "").strip()
    name = data.get("name", symbol).strip()
    asset_type = data.get("asset_type", "台股").strip()
    quantity = float(data.get("quantity", 0))
    price = float(data.get("price", 0))
    currency = data.get("currency", "TWD").strip()
    purchase_place = (data.get("purchase_place") or data.get("buy_place") or data.get("place") or "").strip()
    note = data.get("note")

    if not symbol or quantity <= 0 or price <= 0:
        return jsonify({"error": "標體代碼、買入數量與單價為必填"}), 400

    try:
        asset_id = db.add_or_update_asset(user_id, symbol, name, asset_type, quantity, price, currency, note, purchase_place)
        return jsonify({"status": "success", "id": asset_id, "purchase_place": purchase_place}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@investment_api.post("/api/investment/update-price")
def update_price_api():
    data = request.json or {}
    user_id = data.get("user_id", "default_user")
    symbol = data.get("symbol", "").strip()
    current_price = float(data.get("current_price", 0))

    if not symbol or current_price <= 0:
        return jsonify({"error": "標體代碼與現價為必填"}), 400

    try:
        success = db.update_asset_price(user_id, symbol, current_price)
        if success:
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"error": "找不到該標的"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@investment_api.post("/api/investment/delete")
def delete_asset_api():
    data = request.json or {}
    user_id = data.get("user_id", "default_user")
    asset_id = data.get("id")

    if not asset_id:
        return jsonify({"error": "缺少資產 ID"}), 400

    try:
        success = db.delete_asset(user_id, int(asset_id))
        if success:
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"error": "刪除失敗"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
