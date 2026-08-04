# database.py (Backwards Compatibility Proxy)
# 本檔案提供相容性接口，將呼叫轉發至新的 core/ 與 modules/ 結構。

from core.database import (
    Base, engine, engine_url, SessionLocal, db_session,
    UserState, UserContext, init_db, run_migrations,
    get_or_create, set_user_state, get_user_state, clear_user_state,
    get_user_active_mode, set_user_active_mode
)

from modules.todo.models import (
    Category, SubCategory, Tag, Item, item_sub_categories, item_tags,
    add_item, delete_item, restore_item, mark_item_as_done, mark_item_as_undone,
    update_item, get_item, edit_item, list_items, list_categories,
    list_sub_categories, list_tags, list_places, rename_category,
    rename_sub_category, export_data_as_sql, get_all_data_json,
    get_all_users, get_categories_summary, get_sub_categories_summary,
    get_tags_summary, get_places_summary
)

from modules.card.models import (
    CardProfile, CardShareLog,
    upsert_profile, get_profile, record_share, list_share_history
)
