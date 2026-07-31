# modules/investment/flex_templates.py
from linebot.v3.messaging.models import QuickReply, QuickReplyItem, MessageAction

def get_quick_reply(options):
    if not options: return None
    items = []
    for opt in options:
        if isinstance(opt, tuple):
            label, text = opt
        else:
            label = text = opt
        items.append(QuickReplyItem(action=MessageAction(label=label[:20], text=text)))
    return QuickReply(items=items)

def create_investment_navigation_footer():
    def btn(label, text):
        return {"type": "button", "style": "link", "height": "sm", "action": {"type": "message", "label": label, "text": text}}

    row1 = [btn("📊 投資總覽", "portfolio"), btn("🔍 探索幫助", "help")]
    row2 = [btn("➕ 新增買入", "買入"), btn("📈 股票清單", "資產")]

    return {
        "type": "box", "layout": "vertical", "margin": "md", "contents": [
            {"type": "separator", "color": "#EEEEEE", "margin": "sm"},
            {"type": "box", "layout": "horizontal", "contents": row1},
            {"type": "box", "layout": "horizontal", "contents": row2}
        ]
    }

def create_portfolio_summary_flex(summary):
    total_market = summary["total_market_value"]
    total_cost = summary["total_cost"]
    total_profit = summary["total_profit"]
    total_rate = summary["total_profit_rate"]

    # 決定顏色 (正獲利為紅/綠，預設台灣股票文化正為紅、負為綠)
    profit_color = "#E74C3C" if total_profit >= 0 else "#27AE60"
    profit_sign = "+" if total_profit >= 0 else ""

    body_contents = [
        {"type": "text", "text": "總資產市值", "size": "xs", "color": "#aaaaaa", "align": "center"},
        {"type": "text", "text": f"${total_market:,.0f} TWD", "weight": "bold", "size": "xxl", "color": "#2c3e50", "align": "center", "margin": "xs"},
        {"type": "box", "layout": "horizontal", "margin": "md", "justifyContent": "center", "contents": [
            {"type": "text", "text": f"總損益: {profit_sign}${total_profit:,.0f} ({profit_sign}{total_rate:.2f}%)", "weight": "bold", "size": "sm", "color": profit_color, "align": "center"}
        ]},
        {"type": "separator", "margin": "lg", "color": "#EEEEEE"},
        {"type": "box", "layout": "horizontal", "margin": "md", "contents": [
            {"type": "text", "text": "總成本", "size": "xs", "color": "#888888", "flex": 1},
            {"type": "text", "text": f"${total_cost:,.0f}", "size": "xs", "weight": "bold", "align": "end", "flex": 1}
        ]},
        {"type": "box", "layout": "horizontal", "margin": "xs", "contents": [
            {"type": "text", "text": "持股標的數", "size": "xs", "color": "#888888", "flex": 1},
            {"type": "text", "text": f"{summary['asset_count']} 檔", "size": "xs", "weight": "bold", "align": "end", "flex": 1}
        ]}
    ]

    # 分類統計資訊
    if summary["by_type"]:
        body_contents.append({"type": "separator", "margin": "md", "color": "#EEEEEE"})
        body_contents.append({"type": "text", "text": "📊 資產配置分布", "size": "xs", "weight": "bold", "color": "#555555", "margin": "md"})
        for asset_type, val in summary["by_type"].items():
            ratio = (val / total_market * 100) if total_market > 0 else 0
            body_contents.append({
                "type": "box", "layout": "horizontal", "margin": "xs", "contents": [
                    {"type": "text", "text": f"• {asset_type}", "size": "xs", "color": "#666666", "flex": 2},
                    {"type": "text", "text": f"${val:,.0f} ({ratio:.1f}%)", "size": "xs", "color": "#333333", "align": "end", "flex": 3}
                ]
            })

    return {
        "type": "bubble",
        "header": {"type": "box", "layout": "vertical", "backgroundColor": "#2C3E50", "paddingAll": "12px", "contents": [
            {"type": "text", "text": "💰 投資組合資產總覽", "weight": "bold", "size": "lg", "color": "#ffffff", "align": "center"}
        ]},
        "body": {"type": "box", "layout": "vertical", "contents": body_contents},
        "footer": create_investment_navigation_footer()
    }

def create_investment_list_flex(assets):
    if not assets: return None

    bubbles = []
    # 拆分為 5 檔股票一頁 Bubble
    chunks = [assets[i:i+5] for i in range(0, len(assets), 5)]

    for idx, chunk in enumerate(chunks):
        contents = []
        for a in chunk:
            profit_color = "#E74C3C" if a["profit"] >= 0 else "#27AE60"
            profit_sign = "+" if a["profit"] >= 0 else ""

            row = {"type": "box", "layout": "vertical", "spacing": "xs", "margin": "sm", "contents": [
                {"type": "box", "layout": "horizontal", "contents": [
                    {"type": "text", "text": f"{a['symbol']} {a['name']}", "weight": "bold", "size": "sm", "color": "#2c3e50", "flex": 3},
                    {"type": "text", "text": f"{profit_sign}{a['profit_rate']:.2f}%", "weight": "bold", "size": "sm", "color": profit_color, "align": "end", "flex": 2}
                ]},
                {"type": "box", "layout": "horizontal", "contents": [
                    {"type": "text", "text": f"數量: {a['quantity']} | 均價: {a['cost_price']:,.1f}", "size": "xxs", "color": "#888888", "flex": 3},
                    {"type": "text", "text": f"現價: {a['current_price']:,.1f}", "size": "xxs", "color": "#555555", "align": "end", "flex": 2}
                ]},
                {"type": "box", "layout": "horizontal", "margin": "xs", "spacing": "sm", "contents": [
                    {"type": "box", "layout": "vertical", "backgroundColor": "#2980B9", "cornerRadius": "sm", "paddingAll": "2px", "flex": 1,
                     "action": {"type": "message", "label": "更新現價", "text": f"更新 {a['symbol']} "},
                     "contents": [{"type": "text", "text": "更新現價", "color": "#ffffff", "size": "xxs", "align": "center"}]},
                    {"type": "box", "layout": "vertical", "backgroundColor": "#BDC3C7", "cornerRadius": "sm", "paddingAll": "2px", "flex": 1,
                     "action": {"type": "message", "label": "刪除", "text": f"刪除投資 {a['id']}"},
                     "contents": [{"type": "text", "text": "刪除", "color": "#333333", "size": "xxs", "align": "center"}]}
                ]}
            ]}
            contents.append(row)
            contents.append({"type": "separator", "margin": "sm", "color": "#F0F0F0"})

        if contents: contents.pop()

        bubbles.append({
            "type": "bubble",
            "header": {"type": "box", "layout": "vertical", "backgroundColor": "#34495E", "paddingAll": "12px", "contents": [
                {"type": "text", "text": f"📈 持股明細卡片 ({idx+1}/{len(chunks)})", "weight": "bold", "size": "md", "color": "#ffffff", "align": "center"}
            ]},
            "body": {"type": "box", "layout": "vertical", "contents": contents},
            "footer": create_investment_navigation_footer()
        })

    return {"type": "carousel", "contents": bubbles} if len(bubbles) > 1 else bubbles[0]

def create_investment_help_flex():
    return {
        "type": "bubble",
        "header": {"type": "box", "layout": "vertical", "backgroundColor": "#2980B9", "paddingAll": "12px", "contents": [
            {"type": "text", "text": "💡 投資助手使用指南", "weight": "bold", "size": "lg", "color": "#ffffff", "align": "center"}
        ]},
        "body": {"type": "box", "layout": "vertical", "spacing": "md", "contents": [
            {"type": "text", "text": "1. 快捷買入新增", "weight": "bold", "size": "sm", "color": "#2c3e50"},
            {"type": "text", "text": "語法：投資 + 類別 + 標的代碼 名稱 + 買入 數量 @ 買入價\n範例：投資 + 台股 + 2330 台積電 + 買入 1000 @ 600", "size": "xs", "color": "#555555", "wrap": True},
            {"type": "separator", "color": "#EEEEEE"},
            {"type": "text", "text": "2. 資產總覽與持股清單", "weight": "bold", "size": "sm", "color": "#2c3e50"},
            {"type": "text", "text": "• 輸入 'portfolio' 或 '總覽' 查看總損益與配置\n• 輸入 '資產' 或 '持股' 檢視持股清單", "size": "xs", "color": "#555555", "wrap": True},
            {"type": "separator", "color": "#EEEEEE"},
            {"type": "text", "text": "3. 更新現價與維護", "weight": "bold", "size": "sm", "color": "#2c3e50"},
            {"type": "text", "text": "• 更新現價：更新 2330 650\n• 刪除標的：刪除投資 <ID>", "size": "xs", "color": "#555555", "wrap": True}
        ]},
        "footer": create_investment_navigation_footer()
    }
