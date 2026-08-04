def _row(label, value):
    return {
        "type": "box",
        "layout": "horizontal",
        "margin": "sm",
        "contents": [
            {"type": "text", "text": label, "size": "sm", "color": "#888888", "flex": 1},
            {"type": "text", "text": value, "size": "sm", "color": "#333333", "flex": 2, "wrap": True},
        ],
    }


def create_card_flex(profile=None):
    profile = profile or {
        "name": "未填寫",
        "title": "未填寫",
        "company": "未填寫",
        "phone": "未填寫",
        "email": "未填寫",
        "website": "未填寫",
        "note": "未填寫",
    }

    return {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "👔 個人名片", "weight": "bold", "size": "md", "color": "#1A73E8"}
            ],
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "18px",
            "contents": [
                {"type": "text", "text": profile.get("name", "未填寫"), "weight": "bold", "size": "xl"},
                {"type": "text", "text": profile.get("title", "未填寫"), "size": "sm", "color": "#555555"},
                {"type": "text", "text": profile.get("company", "未填寫"), "size": "sm", "color": "#555555"},
                {"type": "separator", "margin": "lg"},
                _row("電話", profile.get("phone", "未填寫")),
                _row("Email", profile.get("email", "未填寫")),
                _row("網站", profile.get("website", "未填寫")),
                _row("備註", profile.get("note", "未填寫")),
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#1A73E8",
                    "action": {"type": "message", "label": "編輯名片", "text": "編輯名片"},
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "action": {"type": "message", "label": "分享名片", "text": "分享名片"},
                },
            ],
        },
    }


def create_card_help_flex():
    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "18px",
            "contents": [
                {"type": "text", "text": "👔 名片模組說明", "weight": "bold", "size": "lg"},
                {"type": "text", "text": "1. 輸入「我的名片」查看目前名片", "wrap": True},
                {"type": "text", "text": "2. 輸入「編輯名片」依序補齊欄位", "wrap": True},
                {"type": "text", "text": "3. 輸入「分享名片 <recipient_user_id>」立即紀錄給誰", "wrap": True},
                {"type": "text", "text": "4. 可使用「取消」離開編輯流程", "wrap": True},
            ]
        }
    }
