from flask import Blueprint, request, jsonify
from modules.card import models as db

card_api = Blueprint("card_api", __name__)


@card_api.get("/api/cards/profile")
def get_card_profile_api():
    try:
        user_id = request.args.get("user_id") or "default_user"
        return jsonify({"status": "success", "profile": db.get_profile(user_id)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@card_api.post("/api/cards/upsert")
def upsert_card_profile_api():
    data = request.json or {}
    user_id = data.get("user_id") or "default_user"
    payload = {
        "name": data.get("name"),
        "title": data.get("title"),
        "company": data.get("company"),
        "phone": data.get("phone"),
        "email": data.get("email"),
        "website": data.get("website"),
        "note": data.get("note"),
    }
    try:
        db.upsert_profile(user_id, payload)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@card_api.post("/api/cards/share")
def share_card_api():
    data = request.json or {}
    sender_user_id = data.get("sender_user_id") or "default_user"
    recipient_user_id = data.get("recipient_user_id")
    if not recipient_user_id:
        return jsonify({"error": "請提供 recipient_user_id"}), 400
    payload = data.get("payload") or db.get_profile(sender_user_id)
    try:
        share_id = db.record_share(sender_user_id, recipient_user_id, payload)
        return jsonify({"status": "success", "share_id": share_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@card_api.get("/api/cards/share-history")
def share_history_api():
    try:
        user_id = request.args.get("user_id") or "default_user"
        return jsonify({"status": "success", "items": db.list_share_history(user_id, limit=20)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
