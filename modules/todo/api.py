# modules/todo/api.py
from flask import Blueprint, request, jsonify, Response
from core import database as core_db
from modules.todo import models as db

todo_api = Blueprint("todo_api", __name__)

@todo_api.get("/api/data")
def get_data():
    try:
        user_id = request.args.get("user_id")
        data = db.get_all_data_json(user_id=user_id)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@todo_api.get("/api/users")
def get_users_api():
    try:
        users = db.get_all_users()
        return jsonify(users), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@todo_api.post("/api/items/add")
def add_item_api():
    data = request.json or {}
    user_id = data.get("user_id", "default_user")
    category = data.get("category", "未分類").strip()
    sub_categories = data.get("sub_categories", [])
    if isinstance(sub_categories, str):
        sub_categories = [s.strip() for s in sub_categories.split(",") if s.strip()]
    title = data.get("title", "").strip()
    tags = data.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    place = data.get("place", "").strip() or None
    if not title:
        return jsonify({"error": "標題不能為空"}), 400
    try:
        item_id = db.add_item(user_id, category, sub_categories, title, tags=tags, place=place)
        return jsonify({"status": "success", "id": item_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@todo_api.post("/api/items/edit")
def edit_item_api():
    data = request.json or {}
    user_id = data.get("user_id", "default_user")
    item_id = data.get("id")
    category = data.get("category", "未分類").strip()
    sub_categories = data.get("sub_categories", [])
    if isinstance(sub_categories, str):
        sub_categories = [s.strip() for s in sub_categories.split(",") if s.strip()]
    title = data.get("title", "").strip()
    tags = data.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    place = data.get("place", "").strip() or None
    done = data.get("done")
    if not item_id or not title:
        return jsonify({"error": "ID 與標題不能為空"}), 400
    try:
        success = db.update_item(user_id, item_id, category, sub_categories, title, tags=tags, place=place, done=done)
        if success:
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"error": "更新失敗，找不到該項目"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@todo_api.post("/api/items/delete")
def delete_items_api():
    data = request.json or {}
    user_id = data.get("user_id", "default_user")
    ids = data.get("ids", [])
    if not ids:
        return jsonify({"error": "請提供要刪除的 ID 清單"}), 400
    try:
        count = db.delete_item(user_id, ids)
        return jsonify({"status": "success", "count": count}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@todo_api.post("/api/items/restore")
def restore_items_api():
    data = request.json or {}
    user_id = data.get("user_id", "default_user")
    ids = data.get("ids", [])
    if not ids:
        return jsonify({"error": "請提供要復原的 ID 清單"}), 400
    try:
        count = db.restore_item(user_id, ids)
        return jsonify({"status": "success", "count": count}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@todo_api.post("/api/items/complete")
def complete_items_api():
    data = request.json or {}
    user_id = data.get("user_id", "default_user")
    ids = data.get("ids", [])
    if not ids:
        return jsonify({"error": "請提供要完成的 ID 清單"}), 400
    try:
        count = db.mark_item_as_done(user_id, ids)
        return jsonify({"status": "success", "count": count}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@todo_api.post("/api/items/incomplete")
def incomplete_items_api():
    data = request.json or {}
    user_id = data.get("user_id", "default_user")
    ids = data.get("ids", [])
    if not ids:
        return jsonify({"error": "請提供要標記未完成的 ID 清單"}), 400
    try:
        count = db.mark_item_as_undone(user_id, ids)
        return jsonify({"status": "success", "count": count}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@todo_api.get("/api/categories")
def get_categories_api():
    uid = request.args.get("user_id")
    return jsonify(db.get_categories_summary(user_id=uid)), 200

@todo_api.get("/api/sub-categories")
def get_sub_categories_api():
    uid = request.args.get("user_id")
    cat = request.args.get("category")
    return jsonify(db.get_sub_categories_summary(user_id=uid, category_name=cat)), 200

@todo_api.get("/api/tags")
def get_tags_api():
    uid = request.args.get("user_id")
    return jsonify(db.get_tags_summary(user_id=uid)), 200

@todo_api.get("/api/places")
def get_places_api():
    uid = request.args.get("user_id")
    return jsonify(db.get_places_summary(user_id=uid)), 200

@todo_api.get("/api/todo/export")
def export_todo_data_api():
    try:
        sql_data = db.export_data_as_sql()
        return Response(sql_data, mimetype="text/plain", headers={"Content-Disposition": "attachment;filename=todo_backup.sql"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@todo_api.get("/api/export")
def export_all_data_api():
    try:
        sql_data = core_db.export_all_data_as_sql()
        return Response(sql_data, mimetype="text/plain", headers={"Content-Disposition": "attachment;filename=all_backup.sql"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
