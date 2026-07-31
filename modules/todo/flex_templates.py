# modules/todo/flex_templates.py
import re
from linebot.v3.messaging.models import QuickReply, QuickReplyItem, MessageAction

def extract_metadata(text):
    """
    從訊息字串中提取標籤（#）與地點（@）
    返回：標籤列表, 地點, 移除標籤與地點後的原始文字
    """
    tags = re.findall(r'#([^\s#@]+)', text)
    place_match = re.search(r'@([^\s#@]+)', text)
    place = place_match.group(1) if place_match else None

    clean_text = re.sub(r'#[^\s#@]+', '', text)
    clean_text = re.sub(r'@[^\s#@]+', '', clean_text).strip()
    return tags, place, clean_text

def get_quick_reply(options):
    """
    生成 LINE Quick Reply 選項按鈕。
    """
    if not options: return None
    items = []
    for opt in options:
        if isinstance(opt, tuple):
            label, text = opt
        else:
            label = text = opt
        items.append(QuickReplyItem(action=MessageAction(label=label[:20], text=text)))
    return QuickReply(items=items)

def create_context_navigation_footer(context_type, target_val=None):
    """
    根據當前情境生成 2x2 四格智慧導覽列。
    """
    def btn(label, text):
        return {"type": "button", "style": "link", "height": "sm", "action": {"type": "message", "label": label, "text": text}}

    row1 = []; row2 = []

    if context_type == "main":
        row1 = [btn("⬅️ 首頁", "help"), btn("🔍 探索", "help")]
        row2 = [btn("➕ 新增分類", "新增"), btn("📜 全部", "list")]

    elif context_type == "category":
        cat = target_val
        row1 = [btn("⬅️ 主分類", "cat"), btn("🔍 探索", "help")]
        row2 = [btn("➕ 新增子分類", f"新增 {cat}"), btn("📜 全部", f"list {cat}")]

    elif context_type == "subcategory":
        path = target_val
        main_cat = path.split("/")[0] if "/" in path else path
        row1 = [btn("⬅️ 上一層", f"list {main_cat}"), btn("🔍 探索", "help")]
        row2 = [btn("➕ 新增至此", f"新增 {path}"), btn("🔄 排序", f"list {path}")]

    elif context_type in ["success", "deleted"]:
        path = target_val or ""
        row1 = [btn("⬅️ 返回清單", f"list {path}" if path else "list"), btn("🔍 探索", "help")]
        row2 = [btn("➕ 再新增", f"新增 {path}" if path else "新增"), btn("📜 查看清單", f"list {path}" if path else "list")]

    elif context_type == "search":
        val = target_val or ""
        search_type = "tags" if val.startswith("#") else "places"
        row1 = [btn("⬅️ 搜尋", search_type), btn("🔍 探索", "help")]
        row2 = [btn("🔁 重新搜尋", val), btn("📜 查看清單", f"list {val}")]

    elif context_type == "mgmt_cat":
        row1 = [btn("⬅️ 返回", "help"), btn("🔍 探索", "help")]
        row2 = [btn("➕ 新增分類", "新增"), btn("📜 查看清單", "list")]

    elif context_type == "mgmt_subcat":
        cat = target_val or ""
        row1 = [btn("⬅️ 返回", "cat"), btn("🔍 探索", "help")]
        row2 = [btn("➕ 新增子分類", f"新增 {cat}" if cat else "新增"), btn("📜 查看清單", f"list {cat}" if cat else "list")]

    else:
        row1 = [btn("⬅️ 首頁", "help"), btn("🔍 探索", "help")]
        row2 = [btn("➕ 新增項目", "新增"), btn("📜 全部清單", "list")]

    return {
        "type": "box", "layout": "vertical", "margin": "md", "contents": [
            {"type": "separator", "color": "#EEEEEE", "margin": "sm"},
            {"type": "box", "layout": "horizontal", "contents": row1},
            {"type": "box", "layout": "horizontal", "contents": row2}
        ]
    }

def create_todo_flex_message(items, group_by_sub_category=False, offset=0, base_command="list", compact=False, header_title=None, context_info=None):
    if not items: return None

    groups = {}
    for i in items:
        if group_by_sub_category:
            sub_cat_str = i[7]
            sub_cat_list = [s.strip() for s in sub_cat_str.split(",")] if sub_cat_str else ["未分類"]
            for sc in sub_cat_list:
                if sc not in groups: groups[sc] = []
                groups[sc].append(i)
        else:
            cat_name = str(i[6]) if i[6] else "未分類"
            if cat_name not in groups: groups[cat_name] = []
            groups[cat_name].append(i)

    bubble_specs = []
    for group_name, group_items in groups.items():
        sorted_items = sorted(group_items, key=lambda x: x[0], reverse=True)
        chunks = [sorted_items[x:x+3] for x in range(0, len(sorted_items), 3)]

        if compact:
            bubble_specs.append({
                "name": group_name, "items": chunks[0],
                "show_more": len(sorted_items) > 3, "total_count": len(sorted_items)
            })
        else:
            for idx, chunk in enumerate(chunks):
                label = f"{group_name} ({idx+1}/{len(chunks)})" if len(chunks) > 1 else group_name
                bubble_specs.append({"name": label, "items": chunk, "show_more": False})

    total_bubbles = len(bubble_specs)
    has_next = False

    if total_bubbles > offset + 10:
        display_specs = bubble_specs[offset:offset+9]
        has_next = True
        next_offset = offset + 9
    else:
        display_specs = bubble_specs[offset:offset+10]
        has_next = False

    bubbles = []
    for spec in display_specs:
        contents = []
        curr_ctx = "main"; curr_val = None

        if compact and spec.get("name"):
            if context_info and context_info.get("type") == "category":
                curr_ctx = "subcategory"; curr_val = f"{context_info['val']}/{spec['name']}"
            else:
                curr_ctx = "category"; curr_val = spec["name"]
        elif context_info:
            c_type = context_info.get("type")
            if c_type == "subcategory":
                curr_ctx = "subcategory"; curr_val = header_title if header_title and "/" in header_title else context_info.get("val")
            elif c_type in ["tag", "place"]:
                curr_ctx = "search"; curr_val = f"#{context_info['val']}" if c_type == "tag" else f"@{context_info['val']}"
            else:
                curr_ctx = c_type; curr_val = context_info.get("val")

        bubble_footer = create_context_navigation_footer(curr_ctx, curr_val)

        for idx, item in enumerate(spec["items"]):
            item_id, title, _, is_done, place, _, _, sub_cats, tags = item

            item_box = {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [
                {"type": "box", "layout": "horizontal", "contents": [
                    {"type": "text", "text": f"#{item_id}", "size": "xs", "color": "#aaaaaa", "flex": 0},
                    {"type": "text", "text": title, "weight": "bold", "size": "md", "flex": 1, "margin": "md", "wrap": True}
                ]}
            ]}

            details = []
            if tags: details.append({"type": "text", "text": "#" + str(tags).replace(", ", " #"), "size": "xs", "color": "#1db446", "wrap": True})
            info = f"子分類: {sub_cats or '無'}" if not group_by_sub_category else f"主分類: {item[6] or '無'}"
            if place: info += f" | 地點: {place}"
            details.append({"type": "text", "text": info, "size": "xxs", "color": "#999999", "wrap": True})
            item_box["contents"].append({"type": "box", "layout": "vertical", "margin": "sm", "contents": details})

            btn_box = {"type": "box", "layout": "horizontal", "margin": "md", "spacing": "sm", "contents": []}
            if not is_done:
                btn_box["contents"].append({
                    "type": "box", "layout": "vertical", "backgroundColor": "#8D6E63", "cornerRadius": "sm", "paddingAll": "4px",
                    "action": {"type": "message", "label": "完成", "text": f"完成 {item_id}"},
                    "contents": [{"type": "text", "text": "完成", "color": "#ffffff", "size": "xs", "align": "center"}]
                })
            btn_box["contents"].append({
                "type": "box", "layout": "vertical", "backgroundColor": "#EEEEEE", "cornerRadius": "sm", "paddingAll": "4px",
                "action": {"type": "message", "label": "刪除", "text": f"刪除 {item_id}"},
                "contents": [{"type": "text", "text": "刪除", "color": "#616161", "size": "xs", "align": "center"}]
            })
            item_box["contents"].append(btn_box)

            contents.append(item_box)
            if idx < len(spec["items"]) - 1:
                contents.append({"type": "separator", "margin": "lg", "color": "#F5F5F5"})

        if compact and spec.get("show_more"):
            target_cmd = f"list {spec['name']}" if not group_by_sub_category else f"list {header_title}/{spec['name']}"
            contents.append({"type": "separator", "margin": "xl", "color": "#F5F5F5"})
            contents.append({
                "type": "button", "style": "link", "height": "sm", "color": "#8D6E63",
                "action": {"type": "message", "label": f"查看全部 ({spec['total_count']})", "text": target_cmd}
            })

        bubbles.append({
            "type": "bubble",
            "header": {"type": "box", "layout": "vertical", "backgroundColor": "#E67E22",
                "contents": [{"type": "text", "text": spec["name"], "weight": "bold", "size": "xl", "color": "#ffffff", "align": "center"}]},
            "body": {"type": "box", "layout": "vertical", "contents": contents},
            "footer": bubble_footer
        })

    if has_next:
        bubbles.append({"type": "bubble", "body": {"type": "box", "layout": "vertical", "justifyContent": "center", "spacing": "md", "contents": [
            {"type": "text", "text": "還有更多內容", "weight": "bold", "size": "md", "align": "center"},
            {"type": "button", "style": "primary", "color": "#E67E22", "margin": "xl",
                "action": {"type": "message", "label": "下一頁", "text": f"{base_command} @{next_offset}"}}]}})

    return {"type": "carousel", "contents": bubbles} if len(bubbles) > 1 else bubbles[0]

def create_item_detail_carousel(items, context_info=None, is_new=False, is_fail=False, is_deleted=False):
    if not items and not is_fail: return None
    bubbles = []

    ctx_type = "success" if (is_new or not is_deleted) else "deleted"
    if is_fail: ctx_type = "main"

    target_path = None
    if context_info:
        target_path = context_info.get("val")
    elif items:
        cat = items[0][6]; sub = items[0][7]
        target_path = f"{cat}/{sub}" if sub else cat

    bubble_footer = create_context_navigation_footer(ctx_type, target_path)

    if is_fail:
        bubbles.append({
            "type": "bubble",
            "header": {"type": "box", "layout": "vertical", "backgroundColor": "#E74C3C", "paddingAll": "12px",
                       "contents": [{"type": "text", "text": "操作失敗", "weight": "bold", "size": "lg", "color": "#ffffff", "align": "center"}]},
            "body": {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "請檢查輸入格式或重試。", "align": "center", "size": "sm"}]},
            "footer": bubble_footer
        })
    else:
        display_items = items[:10]
        has_more = len(items) > 10

        for item in display_items:
            item_id, title, _, is_done, place, _, cat_name, sub_cats, tags = item

            if is_deleted:
                bg_color = "#E74C3C"
                status_label = "🗑️ 事項已刪除"
            elif is_new:
                bg_color = "#27AE60"
                status_label = f"{cat_name} / {sub_cats}" if sub_cats else cat_name
            elif is_done:
                bg_color = "#3498DB"
                status_label = f"{cat_name} / {sub_cats}" if sub_cats else cat_name
            else:
                bg_color = "#E67E22"
                status_label = f"{cat_name} / {sub_cats}" if sub_cats else cat_name

            header = {
                "type": "box", "layout": "vertical", "backgroundColor": bg_color, "paddingAll": "12px",
                "contents": [{"type": "text", "text": status_label, "weight": "bold", "size": "lg", "color": "#ffffff", "align": "center"}]
            }

            body_contents = [
                {"type": "box", "layout": "horizontal", "contents": [
                    {"type": "text", "text": f"#{item_id}", "size": "xs", "color": "#aaaaaa", "flex": 0},
                    {"type": "text", "text": title, "weight": "bold", "size": "lg", "flex": 1, "margin": "md", "wrap": True}
                ]}
            ]

            if tags:
                body_contents.append({"type": "text", "text": "#" + str(tags).replace(", ", " #"), "size": "sm", "color": "#1db446", "wrap": True, "margin": "md"})
            if place:
                body_contents.append({"type": "box", "layout": "horizontal", "margin": "md", "contents": [
                    {"type": "text", "text": "📍", "size": "sm", "flex": 0},
                    {"type": "text", "text": f"地點: {place}", "size": "sm", "color": "#666666", "flex": 1, "margin": "sm", "wrap": True}
                ]})

            if not is_deleted:
                btn_contents = []
                if not is_done:
                    btn_contents.append({
                        "type": "button", "style": "primary", "color": "#E67E22", "height": "sm",
                        "action": {"type": "message", "label": "✅ 標記完成", "text": f"完成 {item_id}"}
                    })

                btn_contents.append({
                    "type": "box", "layout": "horizontal", "spacing": "sm", "contents": [
                        {"type": "button", "style": "secondary", "height": "sm", "flex": 1, "action": {"type": "message", "label": "✏️ 編輯", "text": f"編輯 {item_id}"}},
                        {"type": "button", "style": "secondary", "height": "sm", "flex": 1, "action": {"type": "message", "label": "🗑️ 刪除", "text": f"刪除 {item_id}"}}
                    ]
                })
                body_contents.append({"type": "box", "layout": "vertical", "margin": "xl", "spacing": "sm", "contents": btn_contents})
            else:
                body_contents.append({"type": "box", "layout": "vertical", "margin": "xl", "contents": [
                    {"type": "button", "style": "primary", "color": "#27AE60", "height": "sm", "action": {"type": "message", "label": "復原事項", "text": f"復原 {item_id}"}}
                ]})

            bubbles.append({
                "type": "bubble",
                "header": header,
                "body": {"type": "box", "layout": "vertical", "contents": body_contents},
                "footer": bubble_footer
            })

        if has_more:
            bubbles.append({
                "type": "bubble",
                "body": {
                    "type": "box", "layout": "vertical", "spacing": "md", "justifyContent": "center",
                    "contents": [
                        {"type": "text", "text": f"還有其餘 {len(items) - 10} 筆", "weight": "bold", "size": "md", "align": "center"},
                        {"type": "text", "text": "已同步處理成功", "size": "xs", "color": "#aaaaaa", "align": "center"}
                    ]
                },
                "footer": bubble_footer
            })
    return {"type": "carousel", "contents": bubbles} if len(bubbles) > 1 else bubbles[0]

def create_category_management_flex(grouped_data, is_sub=False, offset=0, base_command="categories"):
    bubble_specs = []
    if is_sub:
        for main_cat, subs in grouped_data.items():
            chunks = [subs[x:x+3] for x in range(0, len(subs), 3)]
            for idx, chunk in enumerate(chunks):
                label = f"{main_cat} ({idx+1}/{len(chunks)})" if len(chunks) > 1 else main_cat
                bubble_specs.append({"type": "sub", "header": label, "main": main_cat, "items": chunk})
    else:
        main_cats = list(grouped_data.items())
        chunks = [main_cats[x:x+4] for x in range(0, len(main_cats), 4)]
        for idx, chunk in enumerate(chunks):
            label = f"主分類管理 ({idx+1}/{len(chunks)})" if len(chunks) > 1 else "主分類管理"
            bubble_specs.append({"type": "main", "header": label, "items": chunk})

    total_bubbles = len(bubble_specs); has_next = False; next_offset = offset + 10
    display_specs = bubble_specs[offset:offset+10]
    if total_bubbles > offset + 10: has_next = True

    bubbles = []
    for spec in display_specs:
        contents = []
        bubble_footer = create_context_navigation_footer("mgmt_cat")
        if spec["type"] == "sub":
            for idx, item in enumerate(spec["items"]):
                sub, count = item; path = f"{spec['main']}/{sub}"; display_name = f"{sub} ({count})" if count > 0 else sub
                row = {"type": "box", "layout": "horizontal", "spacing": "sm", "alignItems": "center", "contents": [
                    {"type": "text", "text": display_name, "weight": "bold", "size": "sm", "color": "#424242", "flex": 4, "action": {"type": "message", "label": sub, "text": f"list {path}"}},
                    {"type": "box", "layout": "vertical", "backgroundColor": "#BDBDBD", "cornerRadius": "sm", "paddingAll": "4px", "flex": 2, "action": {"type": "message", "label": "改名", "text": f"rename_sub {path} -> "}, "contents": [{"type": "text", "text": "改名", "color": "#ffffff", "size": "xxs", "align": "center"}]},
                    {"type": "box", "layout": "vertical", "backgroundColor": "#E67E22", "cornerRadius": "sm", "paddingAll": "4px", "flex": 2, "action": {"type": "message", "label": "新增", "text": f"新增 {path}"}, "contents": [{"type": "text", "text": "新增", "color": "#ffffff", "size": "xxs", "align": "center"}]}
                ]}
                contents.append(row)
                if idx < len(spec["items"]) - 1: contents.append({"type": "separator", "margin": "sm", "color": "#F5F5F5"})
            bubble_footer = create_context_navigation_footer("mgmt_subcat", spec["main"])
        else:
            for idx, item in enumerate(spec["items"]):
                m, count = item; display_name = f"{m} ({count})" if count > 0 else m
                row = {"type": "box", "layout": "vertical", "spacing": "xs", "contents": [
                    {"type": "box", "layout": "horizontal", "contents": [
                        {"type": "text", "text": display_name, "weight": "bold", "size": "md", "color": "#5D4037", "flex": 1, "action": {"type": "message", "label": m, "text": f"list {m}"}},
                        {"type": "text", "text": "子類 >", "size": "xs", "color": "#E67E22", "align": "end", "gravity": "center", "action": {"type": "message", "label": "子類", "text": f"subcat {m}"}}
                    ]},
                    {"type": "box", "layout": "horizontal", "spacing": "sm", "contents": [
                        {"type": "box", "layout": "vertical", "backgroundColor": "#EEEEEE", "cornerRadius": "sm", "paddingAll": "4px", "flex": 1, "action": {"type": "message", "label": "更名", "text": f"rename_cat {m} -> "}, "contents": [{"type": "text", "text": "更名", "color": "#616161", "size": "xxs", "align": "center"}]},
                        {"type": "box", "layout": "vertical", "backgroundColor": "#E67E22", "cornerRadius": "sm", "paddingAll": "4px", "flex": 1, "action": {"type": "message", "label": "新增", "text": f"新增 {m}"}, "contents": [{"type": "text", "text": "新增", "color": "#ffffff", "size": "xxs", "align": "center"}]}
                    ]}
                ]}
                contents.append(row)
                if idx < len(spec["items"]) - 1: contents.append({"type": "separator", "margin": "md", "color": "#EEEEEE"})

        bubbles.append({
            "type": "bubble",
            "header": {"type": "box", "layout": "vertical", "backgroundColor": "#F5F5F5", "contents": [
                {"type": "text", "text": f" {spec['header']}", "weight": "bold", "size": "lg", "color": "#424242", "align": "center"}
            ]},
            "body": {"type": "box", "layout": "vertical", "spacing": "md", "contents": contents},
            "footer": bubble_footer
        })

    if has_next:
        bubbles.append({"type": "bubble", "body": {"type": "box", "layout": "vertical", "justifyContent": "center", "spacing": "md", "contents": [
            {"type": "text", "text": "還有更多內容", "weight": "bold", "size": "md", "align": "center"},
            {"type": "button", "style": "primary", "color": "#E67E22", "margin": "xl",
                "action": {"type": "message", "label": "下一頁", "text": f"{base_command} @{next_offset}"}}]}})

    return {"type": "carousel", "contents": bubbles} if len(bubbles) > 1 else bubbles[0]

def create_simple_list_flex(title, items, prefix="", base_command="list", context_type="main"):
    if not items: return None
    chunks = [items[x:x+20] for x in range(0, len(items), 20)]; bubbles = []
    bubble_footer = create_context_navigation_footer("search", "#" if prefix == "#" else "@")
    for idx, chunk in enumerate(chunks):
        rows = []
        for i in range(0, len(chunk), 2):
            pair = chunk[i:i+2]; row_contents = []
            for item, count in pair:
                display_name = f"{prefix}{item}"
                if count > 0: display_name += f" ({count})"
                row_contents.append({"type": "box", "layout": "vertical", "flex": 1, "margin": "xs", "backgroundColor": "#F5F5F5", "cornerRadius": "md", "paddingAll": "8px", "action": {"type": "message", "label": item, "text": f"{base_command} {prefix}{item}"}, "contents": [{"type": "text", "text": display_name, "size": "xs", "align": "center", "color": "#5D4037", "weight": "bold"}]})
            if len(pair) == 1:
                row_contents.append({"type": "box", "layout": "vertical", "flex": 1, "contents": []})
            rows.append({"type": "box", "layout": "horizontal", "spacing": "sm", "margin": "sm", "contents": row_contents})
        bubbles.append({
            "type": "bubble",
            "header": {"type": "box", "layout": "vertical", "backgroundColor": "#F5F5F5", "contents": [{"type": "text", "text": f"{title} ({idx+1}/{len(chunks)})", "weight": "bold", "size": "lg", "color": "#424242", "align": "center"}]},
            "body": {"type": "box", "layout": "vertical", "spacing": "none", "contents": rows},
            "footer": bubble_footer
        })
    return {"type": "carousel", "contents": bubbles} if len(bubbles) > 1 else bubbles[0]

def create_help_flex_message():
    def make_bubble(title, color, items):
        contents = []
        for icon, cmd, desc, fill_text in items:
            contents.append({"type": "box", "layout": "horizontal", "spacing": "md", "margin": "md", "contents": [
                {"type": "text", "text": icon, "flex": 0, "size": "sm"},
                {"type": "box", "layout": "vertical", "flex": 1, "contents": [
                    {"type": "text", "text": cmd, "weight": "bold", "size": "sm", "color": "#424242",
                     "action": {
                         "type": "postback",
                         "label": cmd,
                         "data": f"action=help_prefill&command={cmd}",
                         "inputOption": "openKeyboard",
                         "fillInText": fill_text
                     }},
                    {"type": "text", "text": desc, "size": "xxs", "color": "#999999", "wrap": True}
                ]}
            ]})
            contents.append({"type": "separator", "margin": "md", "color": "#F0F0F0"})
        if contents: contents.pop()

        return {
            "type": "bubble",
            "header": {"type": "box", "layout": "vertical", "backgroundColor": color, "contents": [
                {"type": "text", "text": title, "weight": "bold", "color": "#ffffff", "size": "md"}
            ]},
            "body": {"type": "box", "layout": "vertical", "contents": contents},
            "footer": create_context_navigation_footer("help")
        }

    bubbles = [
        make_bubble("📝 基本操作", "#E67E22", [
            ("➕", "新增", "逐步引導新增待辦事項", "新增 "),
            ("✅", "完成 <ID>", "標記事項為已完成 (多筆用逗號)", "完成 "),
            ("🗑️", "刪除 <ID>", "移除待辦事項 (多筆用逗號)", "刪除 "),
            ("♻️", "復原 <ID>", "恢復已刪除的待辦事項", "復原 "),
            ("✏️", "編輯 <ID>", "修改事項名稱或地點", "編輯 ")
        ]),
        make_bubble("🔍 查詢與管理", "#8D6E63", [
            ("📁", "cat", "管理主分類（更名、快速新增）", "cat"),
            ("🌿", "subcat", "查看所有子分類事項分佈", "subcat"),
            ("🏷️", "tags", "依標籤瀏覽所有事項", "tags"),
            ("📍", "places", "依地點瀏覽所有事項", "places"),
            ("📜", "list", "列出所有未完成事項", "list")
        ]),
        make_bubble("⚡ 快捷語法", "#1DB446", [
            ("⌨️", "主+子+內容", "新增事項可包含 #標籤 與 @地點", "追劇清單 + 言情 + 事項 #標籤 @地點"),
            ("🚀", "主+子+A,B,C", "批次新增多個事項", "追劇清單 + 言情 + 事項 #標籤 @地點"),
            ("🏷️", "#標籤名", "快速搜尋特定標籤", "#待播"),
            ("📍", "@地點名", "快速搜尋特定地點", "@地點"),
            ("💡", "list 主分類/子分類", "直接進入特定路徑清單", "list 主分類/子分類")
        ])
    ]
    return {"type": "carousel", "contents": bubbles}
