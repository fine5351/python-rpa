import os
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.settings.basic'
]

CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'token.json')


def get_gmail_service():
    """
    取得 Gmail API 服務物件。
    若本地無憑證檔，會輸出詳細教學引導使用者提供 credentials.json。
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"[警告] 讀取權限 Token 失敗: {e}，將重新驗證。")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("[資訊] 正在更新過期的 Gmail 權限 Token...")
                creds.refresh(Request())
            except Exception as e:
                print(f"[警告] 刷新 Token 失敗: {e}，需要重新登入。")
                creds = None

        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                print("\n=======================================================")
                print("❌ 找不到 Gmail API 憑證檔案 (credentials.json)！")
                print("-------------------------------------------------------")
                print("請按照以下步驟取得 credentials.json 並放置於專案根目錄：")
                print(f"檔案放置路徑: {CREDENTIALS_FILE}")
                print("\n1. 前往 Google Cloud Console (https://console.cloud.google.com/)")
                print("2. 建立新專案或選擇現有專案。")
                print("3. 啟用 'Gmail API' 服務 (APIs & Services -> Enable APIs and Services)。")
                print("4. 設定 OAuth 同意畫面 (OAuth consent screen)，選擇 External / Internal 並新增您的 Gmail 為 Testing User。")
                print("5. 建立憑證 (Credentials -> Create Credentials -> OAuth client ID)。")
                print("   - Application type 選擇：Desktop App (桌面應用程式)")
                print("6. 下載 JSON 憑證檔案，將其重新命名為 `credentials.json`，並貼至專案目錄。")
                print("=======================================================\n")
                raise FileNotFoundError(f"Missing {CREDENTIALS_FILE}")

            print("[資訊] 啟動 OAuth 2.0 登入瀏覽器驗證流程...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # 儲存認證 token
        with open(TOKEN_FILE, 'w', encoding='utf-8') as token_f:
            token_f.write(creds.to_json())
        print("[成功] Gmail API 認證完成，Token 已儲存。")

    service = build('gmail', 'v1', credentials=creds)
    return service

if __name__ == '__main__':
    try:
        service = get_gmail_service()
        print("Gmail API 連線測試成功！")
    except Exception as e:
        print(f"連線失敗: {e}")
