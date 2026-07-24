import base64

def get_user_labels(service):
    """取得使用者建立的所有自定義標籤 (User Labels)"""
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    user_labels = [l for l in labels if l.get('type') == 'user']
    return user_labels

def fetch_unlabeled_messages(service, max_results=50):
    """
    抓取未加上自定義標籤的最新信件
    """
    user_labels = get_user_labels(service)
    user_label_ids = set(l['id'] for l in user_labels)
    user_label_map = {l['id']: l['name'] for l in user_labels}

    print(f"[資訊] 目前帳號共有 {len(user_labels)} 個自定義標籤: {[l['name'] for l in user_labels]}")

    # 檢索 INBOX 最新信件（預設 50 封進行分析）
    response = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=max_results).execute()
    messages_meta = response.get('messages', [])


    unlabeled_emails = []

    print(f"[資訊] 正在掃描近 {len(messages_meta)} 封收件匣信件的標籤狀況...")
    for item in messages_meta:
        msg_id = item['id']
        msg = service.users().messages().get(userId='me', id=msg_id, format='metadata', metadataHeaders=['From', 'Subject', 'Date', 'To']).execute()

        label_ids = set(msg.get('labelIds', []))
        
        # 檢查是否含有任何 user label
        has_user_label = len(label_ids.intersection(user_label_ids)) > 0
        if not has_user_label:
            headers = msg.get('payload', {}).get('headers', [])
            header_dict = {h['name']: h['value'] for h in headers}

            unlabeled_emails.append({
                'id': msg_id,
                'threadId': msg.get('threadId'),
                'from': header_dict.get('From', ''),
                'to': header_dict.get('To', ''),
                'subject': header_dict.get('Subject', '(無主旨)'),
                'date': header_dict.get('Date', ''),
                'snippet': msg.get('snippet', ''),
                'existing_labels': [user_label_map[lid] for lid in label_ids if lid in user_label_map]
            })

    print(f"[資訊] 掃描完成！找到 {len(unlabeled_emails)} 封完全未加上自定義標籤的信件。")
    return unlabeled_emails, user_labels
