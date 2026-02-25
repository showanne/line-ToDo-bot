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
        # Size: 2500x843 (Half-size) or 2500x1686 (Full-size)
        # We'll use 2500x843 for a sleek 3-column menu
        rich_menu_request = RichMenuRequest(
            size=RichMenuSize(width=2500, height=843),
            selected=True,
            name="Main Rich Menu",
            chat_bar_text="選單",
            areas=[
                # Area 1: list (清單)
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                    action=MessageAction(label="list", text="list")
                ),
                # Area 2: help (說明)
                RichMenuArea(
                    bounds=RichMenuBounds(x=833, y=0, width=833, height=843),
                    action=MessageAction(label="help", text="help")
                ),
                # Area 3: contact (聯絡我)
                RichMenuArea(
                    bounds=RichMenuBounds(x=1666, y=0, width=834, height=843),
                    action=MessageAction(label="contact", text="contact")
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
        print("" + "="*50)
        print("Rich Menu has been created, but you still need to:")
        print(f"1. Upload an image (2500x843) to this Rich Menu ID: {rich_menu_id}")
        print(f"2. Set it as the default Rich Menu.")
        print("="*50)

        print("Do you have an image file (e.g., 'rich_menu.png') in this folder?")
        image_path = input("Enter image filename (or press Enter to skip upload): ").strip()

        if image_path and os.path.exists(image_path):
            try:
                with open(image_path, 'rb') as image:
                    image_data = image.read()
                    # In v3, the binary data should be passed directly to 'body'.
                    # If it fails with JSON error, it's often because the content-type header is missing or incorrect.
                    # Content-Type: 'image/png', 'image/jpeg'.
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
            print("Skipped image upload. You can do this later via API or LINE Official Account Manager.")
            print(f"To set as default manually via CLI (if you have an image later):")
            print(f"python setup_rich_menu.py --upload {rich_menu_id} <your_image_path>")

if __name__ == "__main__":
    create_rich_menu()
