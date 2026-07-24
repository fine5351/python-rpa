import re

def parse_sender_email(from_header):
    """從 From Header 中提取純 Email 地址"""
    match = re.search(r'<([^>]+)>', from_header)
    if match:
        return match.group(1).strip()
    return from_header.strip()

def analyze_and_group_emails(unlabeled_emails, existing_user_labels):
    """
    分析未標籤信件並建議適當的標籤名稱與 Filter 篩選條件
    """
    existing_label_names = [l['name'] for l in existing_user_labels]
    
    classification_results = []
    rule_proposals = []

    # 按寄件者網域或關鍵字進行特徵分類
    domain_groups = {}

    for email in unlabeled_emails:
        sender_email = parse_sender_email(email['from'])
        domain = sender_email.split('@')[-1] if '@' in sender_email else sender_email
        subject = email['subject']
        snippet = email['snippet']

        # 根據使用者精準語意標準進行分類：
        # 1. 職缺 ➡️ 真的有職務推薦 (如 104 職務推薦、徵才、求職職缺信)
        # 2. 消費 / 消費/節稅 ➡️ 真的有花錢 (如 發票, 收據, 購買確認 'purchase', 明細, 帳單)
        # 3. 知識 ➡️ 真的可以學習東西 (如 課程, 技能證書, 技術文, 研報, 教學, 深度專題)
        # 4. 娛樂 ➡️ 動漫畫、遊戲訊息 (如 遊戲, patreon, 動漫, 虛寶, 回歸福利, 娛樂)
        # 5. 資訊 ➡️ 一般通知 (無學習價值的宣傳信, 帳戶通知, 政策變更, 蛋糕預購等)

        target_label = None
        combined_text = f"{subject} {snippet} {email['from']}".lower()

        # 1. 職缺：真的有職務推薦、徵才、工作推薦
        if any(k in combined_text for k in ['職務推薦', '適合您的職缺', '推薦職缺', '職缺推薦', '徵才職缺', '求職推薦', 'hiring for', 'job recommendation']):
            target_label = "職缺" if "職缺" in existing_label_names else "資訊"

        # 2. 消費 / 消費/節稅：真的有花錢（發票、收據、購買 confirmation、帳單、扣款明細）
        elif any(k in combined_text for k in ['thanks for your recent', 'purchase', 'receipt', 'invoice', '電子發票', '繳費明細', '扣款通知', '交易成功', '購買成功', '帳單']):
            if "消費/節稅" in existing_label_names and any(k in combined_text for k in ['節稅', '電子發票', '收據']):
                target_label = "消費/節稅"
            elif "消費" in existing_label_names:
                target_label = "消費"
            else:
                target_label = "資訊"

        # 3. 娛樂：動漫畫、遊戲訊息、ACG、Patreon、福利、BookWalker 電子書漫畫
        elif any(k in combined_text for k in ['patreon', 'preview', 'cheerleader', 'tier', 'miku', 'game', 'gaming', '遊戲', '動漫', '福利', 'enjoygm', 'bookwalker', 'book_walker', '新番']):
            target_label = "娛樂" if "娛樂" in existing_label_names else "資訊"

        # 4. 知識：真的可以學習東西（研報, 技術指南, 課程, 技能證書, 論文, 趨勢解析）
        elif any(k in combined_text for k in ['研報', '課程', '技能證書', '證書', '直播班', '教學', 'guide', 'architecture', 'best practices', 'agent', 'book', '論文', '技術解析', '專家一次解析']):
            target_label = "知識" if "知識" in existing_label_names else "資訊"

        # 5. 資訊：一般通知 (行銷廣告, 蛋糕預購, 帳戶通知, 政策變更, 一般理財宣傳等)
        else:
            target_label = "資訊" if "資訊" in existing_label_names else (existing_label_names[0] if existing_label_names else "資訊")

        # 確保 target_label 必須在既有標籤列表中
        matched_existing = next((l for l in existing_user_labels if l['name'].lower() == target_label.lower()), None)
        final_label_name = matched_existing['name'] if matched_existing else (existing_label_names[0] if existing_label_names else "資訊")
        
        classification_results.append({
            'email_id': email['id'],
            'from': email['from'],
            'sender_email': sender_email,
            'subject': subject,
            'suggested_label': final_label_name,
            'is_new_label': False  # 絕對不建立新標籤
        })

    # 針對建議標籤進行匯總並產生 Filter 規則
    suggested_filters = {}

    for item in classification_results:
        lbl = item['suggested_label']
        sender = item['sender_email']
        
        if lbl not in suggested_filters:
            suggested_filters[lbl] = {
                'label': lbl,
                'is_new_label': item['is_new_label'],
                'senders': set(),
                'email_ids': []
            }
        suggested_filters[lbl]['senders'].add(sender)
        suggested_filters[lbl]['email_ids'].append(item['email_id'])

    return classification_results, suggested_filters
