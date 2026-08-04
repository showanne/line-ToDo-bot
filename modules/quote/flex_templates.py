def _quote_values(quote):
    if isinstance(quote, dict):
        return (
            quote.get("id"),
            quote.get("content", ""),
            quote.get("source") or "未填",
            quote.get("speaker") or "未填",
            quote.get("tags", []),
        )

    tags = getattr(quote, "tags", None) or []
    return (
        getattr(quote, "id", None),
        getattr(quote, "content", ""),
        getattr(quote, "source", None) or "未填",
        getattr(quote, "speaker", None) or "未填",
        [tag.name if hasattr(tag, "name") else str(tag) for tag in tags],
    )


QUOTE_HEADER_BG = "#2F5D50"
QUOTE_HEADER_BG_ALT = "#415C7F"
QUOTE_ACTION_PRIMARY = "#2C6E5F"
QUOTE_ACTION_SECONDARY = "#B45309"
QUOTE_TAG_BG = "#EEF4E8"
QUOTE_TAG_TEXT = "#365C44"


def create_quote_navigation_footer():
    def btn(label, text):
        return {
            "type": "button",
            "style": "link",
            "height": "sm",
            "action": {"type": "message", "label": label, "text": text},
        }

    return {
        "type": "box",
        "layout": "vertical",
        "margin": "md",
        "contents": [
            {"type": "separator", "color": "#EEEEEE", "margin": "sm"},
            {"type": "box", "layout": "horizontal", "contents": [
                btn("📜 列出佳句", "列出佳句"),
                btn("🔍 幫助", "help")
            ]},
            {"type": "box", "layout": "horizontal", "contents": [
                btn("➕ 新增佳句", "新增佳句"),
                btn("💬 佳句模式", "@佳句")
            ]}
        ]
    }


def _quote_tag_pills(tags):
    if not tags:
        return []

    return [{
        "type": "box",
        "layout": "vertical",
        "backgroundColor": QUOTE_TAG_BG,
        "cornerRadius": "sm",
        "paddingAll": "4px",
        "margin": "sm",
        "contents": [
            {"type": "text", "text": f"#{tag}", "color": QUOTE_TAG_TEXT, "size": "xxs", "align": "center"}
        ]
    } for tag in tags]


def build_quote_help_flex():
    return {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": QUOTE_HEADER_BG_ALT,
            "paddingAll": "12px",
            "contents": [
                {
                    "type": "text",
                    "text": "💡 佳句助手說明",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#ffffff",
                    "align": "center"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": "1. 快速新增",
                    "weight": "bold",
                    "size": "sm",
                    "color": "#2F5D50"
                },
                {
                    "type": "text",
                    "text": "輸入：新增佳句\n再依序回覆內容、出處、誰說的、標籤即可。",
                    "size": "xs",
                    "color": "#555555",
                    "wrap": True
                },
                {
                    "type": "separator",
                    "margin": "sm",
                    "color": "#EEEEEE"
                },
                {
                    "type": "text",
                    "text": "2. 一行速記格式",
                    "weight": "bold",
                    "size": "sm",
                    "color": "#2F5D50"
                },
                {
                    "type": "text",
                    "text": "範例：佳句 + 人生如逆旅，我亦是行人 + 《論語》 + 孔子 + #人生 #哲學",
                    "size": "xs",
                    "color": "#555555",
                    "wrap": True
                },
                {
                    "type": "separator",
                    "margin": "sm",
                    "color": "#EEEEEE"
                },
                {
                    "type": "text",
                    "text": "3. 列表與維護",
                    "weight": "bold",
                    "size": "sm",
                    "color": "#2F5D50"
                },
                {
                    "type": "text",
                    "text": "• 輸入 列出佳句 可以查看收藏列表\n• 輸入 佳句數量 看目前筆數\n• 輸入 編輯佳句 5 或 刪除佳句 5 來修改/移除",
                    "size": "xs",
                    "color": "#555555",
                    "wrap": True
                }
            ]
        },
        "footer": create_quote_navigation_footer()
    }


def build_quote_success_flex(quote):
    quote_id, content, source, speaker, tags = _quote_values(quote)

    return {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": QUOTE_HEADER_BG,
            "paddingAll": "12px",
            "contents": [
                {
                    "type": "text",
                    "text": "✅ 已新增佳句",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#ffffff",
                    "align": "center"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": content,
                    "wrap": True,
                    "size": "lg",
                    "weight": "bold",
                    "color": "#1f2937"
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "🗂️ 出處", "size": "xs", "color": "#888888", "flex": 1},
                        {"type": "text", "text": source, "size": "xs", "weight": "bold", "align": "end", "flex": 2}
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "🧑‍💼 誰說的", "size": "xs", "color": "#888888", "flex": 1},
                        {"type": "text", "text": speaker, "size": "xs", "weight": "bold", "align": "end", "flex": 2}
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "wrap": True,
                    "spacing": "sm",
                    "contents": _quote_tag_pills(tags)
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "button",
                            "action": {
                                "type": "postback",
                                "label": "編輯",
                                "data": f"edit_quote:{quote_id}"
                            },
                            "style": "primary",
                            "color": QUOTE_ACTION_PRIMARY
                        },
                        {
                            "type": "button",
                            "action": {
                                "type": "postback",
                                "label": "刪除",
                                "data": f"delete_quote:{quote_id}"
                            },
                            "style": "secondary",
                            "color": QUOTE_ACTION_SECONDARY
                        }
                    ]
                },
                create_quote_navigation_footer()
            ]
        }
    }


def build_quote_flex_message(quotes):
    if not quotes:
        return None

    cards = []
    for q in quotes:
        q_id, content, source, speaker, tags = _quote_values(q)
        cards.append({
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": QUOTE_HEADER_BG_ALT,
                "paddingAll": "12px",
                "contents": [
                    {
                        "type": "text",
                        "text": "💬 佳句紀錄",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#ffffff",
                        "align": "center"
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": content,
                        "wrap": True,
                        "size": "lg",
                        "weight": "bold",
                        "color": "#1f2937"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "🗂️ 出處", "size": "xs", "color": "#888888", "flex": 1},
                            {"type": "text", "text": source, "size": "xs", "weight": "bold", "align": "end", "flex": 2}
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "🧑‍💼 誰說的", "size": "xs", "color": "#888888", "flex": 1},
                            {"type": "text", "text": speaker, "size": "xs", "weight": "bold", "align": "end", "flex": 2}
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "wrap": True,
                        "spacing": "sm",
                        "contents": _quote_tag_pills(tags)
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "button",
                                "action": {
                                    "type": "postback",
                                    "label": "編輯",
                                    "data": f"edit_quote:{q_id}"
                                },
                                "style": "primary",
                                "color": QUOTE_ACTION_PRIMARY
                            },
                            {
                                "type": "button",
                                "action": {
                                    "type": "postback",
                                    "label": "刪除",
                                    "data": f"delete_quote:{q_id}"
                                },
                                "style": "secondary",
                                "color": QUOTE_ACTION_SECONDARY
                            }
                        ]
                    },
                    create_quote_navigation_footer()
                ]
            }
        })

    return {"type": "carousel", "contents": cards} if len(cards) > 1 else cards[0]
