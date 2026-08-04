from flask import Blueprint, request, jsonify
from modules.quote import models as db

quote_api = Blueprint("quote_api", __name__)


@quote_api.get("/api/quotes")
def get_quotes_api():
    try:
        user_id = request.args.get("user_id") or "default_user"
        quotes = db.list_quotes(user_id, limit=50)
        payload = [
            {
                "id": q.id,
                "content": q.content,
                "source": q.source or "未填",
                "speaker": q.speaker or "未填",
                "tags": [tag.name for tag in q.tags],
                "created_at": q.created_at.isoformat() if q.created_at else None,
            }
            for q in quotes
        ]
        return jsonify({"status": "success", "items": payload}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@quote_api.post("/api/quotes/add")
def add_quote_api():
    data = request.json or {}
    user_id = data.get("user_id", "default_user")
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "佳句內容不能為空"}), 400
    try:
        quote_id = db.add_quote(
            user_id=user_id,
            content=content,
            source=data.get("source"),
            speaker=data.get("speaker"),
            tags=data.get("tags", []),
        )
        return jsonify({"status": "success", "id": quote_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@quote_api.post("/api/quotes/edit")
def edit_quote_api():
    data = request.json or {}
    user_id = data.get("user_id", "default_user")
    quote_id = data.get("id")
    if not quote_id:
        return jsonify({"error": "請提供要編輯的 id"}), 400
    try:
        success = db.update_quote(
            user_id=user_id,
            quote_id=int(quote_id),
            content=data.get("content"),
            source=data.get("source"),
            speaker=data.get("speaker"),
            tags=data.get("tags"),
        )
        if success:
            return jsonify({"status": "success"}), 200
        return jsonify({"error": "找不到該佳句"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@quote_api.post("/api/quotes/delete")
def delete_quote_api():
    data = request.json or {}
    user_id = data.get("user_id", "default_user")
    quote_id = data.get("id")
    if not quote_id:
        return jsonify({"error": "請提供要刪除的 id"}), 400
    try:
        success = db.delete_quote(user_id=user_id, quote_id=int(quote_id))
        if success:
            return jsonify({"status": "success"}), 200
        return jsonify({"error": "找不到該佳句"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
