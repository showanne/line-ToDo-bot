import os
import sys
from dotenv import load_dotenv
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob
)
from linebot.v3.messaging.models import (
    RichMenuRequest,
    RichMenuSize,
    RichMenuArea,
    RichMenuBounds,
    MessageAction,
    RichMenuResponse
)

# Load environment variables
load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

if not CHANNEL_ACCESS_TOKEN:
    print("Error: LINE_CHANNEL_ACCESS_TOKEN not found in .env")
    sys.exit(1)

def create_rich_menu():
    configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        messaging_api_blob = MessagingApiBlob(api_client)

        # 1. Define the Rich Menu structure
        # Size: 2500x1686 (Standard Full-size for 6-grid layout)
        rich_menu_request = RichMenuRequest(
            size=RichMenuSize(width=2500, height=1686),
            selected=True,
            name="ToDo Bot Main Rich Menu",
            chat_bar_text="開啟選單",
            areas=[
                # Row 1, Col 1: 新增 (add)
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                    action=MessageAction(label="新增", text="新增")
                ),
                # Row 1, Col 2: 清單 (list)
                RichMenuArea(
                    bounds=RichMenuBounds(x=833, y=0, width=833, height=843),
                    action=MessageAction(label="清單", text="list")
                ),
                # Row 1, Col 3: 分類管理 (cat)
                RichMenuArea(
                    bounds=RichMenuBounds(x=1666, y=0, width=834, height=843),
                    action=MessageAction(label="分類", text="cat")
                ),
                # Row 2, Col 1: 標籤搜尋 (tags)
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=843, width=833, height=843),
                    action=MessageAction(label="標籤", text="tags")
                ),
                # Row 2, Col 2: 地點搜尋 (places)
                RichMenuArea(
                    bounds=RichMenuBounds(x=833, y=843, width=833, height=843),
                    action=MessageAction(label="地點", text="places")
                ),
                # Row 2, Col 3: 指令說明 (help)
                RichMenuArea(
                    bounds=RichMenuBounds(x=1666, y=843, width=834, height=843),
                    action=MessageAction(label="幫助", text="help")
                )
            ]
        )

        # 2. Create Rich Menu
        try:
            rich_menu_response: RichMenuResponse = messaging_api.create_rich_menu(rich_menu_request=rich_menu_request)
            rich_menu_id = rich_menu_response.rich_menu_id
            print(f"Successfully created rich menu: {rich_menu_id}")
        except Exception as e:
            print(f"Error creating rich menu: {e}")
            return

        # 3. Next steps for the user
        print("\n" + "="*60)
        print("Rich Menu 結構已建立！")
        print(f"Rich Menu ID: {rich_menu_id}")
        print("-" * 60)
        print("注意事項：")
        print("1. 請準備一張 2500x1686 像素的圖片。")
        print("2. 確保圖片的按鈕位置與上述 2x3 佈局相符。")
        print("="*60 + "\n")

        image_path = input("請輸入圖片檔案路徑 (例如 'rich_menu.png'，直接按 Enter 跳過上傳): ").strip()

        if image_path and os.path.exists(image_path):
            try:
                with open(image_path, 'rb') as image:
                    image_data = image.read()
                    messaging_api_blob.set_rich_menu_image(
                        rich_menu_id=rich_menu_id,
                        body=image_data,
                        _headers={'Content-Type': 'image/png'}
                    )
                print(f"Successfully uploaded image: {image_path}")

                # 4. Set as default
                messaging_api.set_default_rich_menu(rich_menu_id=rich_menu_id)
                print("Successfully set as default rich menu!")
            except Exception as e:
                print(f"Error uploading image or setting default: {e}")
        else:
            print("已跳過圖片上傳。您可以之後再手動上傳。")

if __name__ == "__main__":
    create_rich_menu()
