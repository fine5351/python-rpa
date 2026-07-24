import re

def get_or_create_label(service, label_name):
    """查詢標籤 ID，若不存在則建立新標籤"""
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    for label in labels:
        if label['name'].lower() == label_name.lower():
            return label['id']

    # 建立新標籤
    label_object = {
        'name': label_name,
        'labelListVisibility': 'labelShow',
        'messageListVisibility': 'show'
    }
    created_label = service.users().labels().create(userId='me', body=label_object).execute()
    print(f"[建立標籤] 成功新增自定義標籤: {label_name} (ID: {created_label['id']})")
    return created_label['id']


def get_existing_filters(service):
    """取得使用者目前的所有 Gmail Filter 規則"""
    try:
        results = service.users().settings().filters().list(userId='me').execute()
        return results.get('filter', [])
    except Exception as e:
        print(f"[警告] 讀取現有篩選器失敗: {e}")
        return []


def parse_from_conditions(criteria_from):
    """將 Gmail from 搜尋條件字串 (含 |, OR, 括號等) 解析為乾淨的個別條件集合"""
    if not criteria_from:
        return []
    text = criteria_from.strip()
    if text.startswith('(') and text.endswith(')'):
        text = text[1:-1].strip()
    if text.startswith('{') and text.endswith('}'):
        text = text[1:-1].strip()
    
    # 支援以 | 、 OR (忽略大小寫)、逗號進行切割
    items = re.split(r'\s+OR\s+|\s*\|\s*|\s*,\s*', text, flags=re.IGNORECASE)
    return [it.strip() for it in items if it.strip()]


def apply_classification_and_filters(service, filter_proposals):
    """
    執行標籤建立、舊信件批次標籤化，以及將同標籤的舊與新 Filter 規則「100% 聯集合併為單一篩選器」
    並自動檢測與清理「無任何動作」的無效舊篩選器！
    """
    created_filters_count = 0
    deleted_filters_count = 0
    updated_messages_count = 0

    existing_filters = get_existing_filters(service)
    print(f"[資訊] 成功載入現有 {len(existing_filters)} 條 Gmail 篩選器進行深度分析與無效條目清理。")

    # 專門檢查並刪除「無任何動作」的廢棄篩選器 (Empty action filters)
    orphaned_senders_by_label = {
        '娛樂': set(),
        '知識': set(),
        '消費': set(),
        '資訊': set()
    }

    for ef in list(existing_filters):
        action = ef.get('action', {})
        # 若 action 完全為空，或沒有加標籤/移除標籤/轉寄等任何行為
        if not action or (not action.get('addLabelIds') and not action.get('removeLabelIds') and not action.get('forward')):
            criteria_from = ef.get('criteria', {}).get('from', '')
            parsed_items = parse_from_conditions(criteria_from)
            print(f"[發現無動作無效篩選器] ID: {ef['id']}, 條件 from:{criteria_from}")
            
            # 將無動作篩選器中的寄件者按語意自動救援至相應標籤
            for item in parsed_items:
                item_lower = item.lower()
                if any(k in item_lower for k in ['gamer.com.tw', 'patreon', 'nijigengames', 'bookwalker']):
                    orphaned_senders_by_label['娛樂'].add(item)
                elif any(k in item_lower for k in ['perplexity.ai', 'medium.com', 'substack', '104news']):
                    orphaned_senders_by_label['知識'].add(item)
                elif any(k in item_lower for k in ['edenred', 'cashback', 'invoice', 'receipt']):
                    orphaned_senders_by_label['消費'].add(item)
                else:
                    orphaned_senders_by_label['資訊'].add(item)

            # 刪除無效 Filter
            try:
                service.users().settings().filters().delete(userId='me', id=ef['id']).execute()
                deleted_filters_count += 1
                print(f"[清理成功] 已刪除無動作無效篩選器 (ID: {ef['id']})")
                existing_filters.remove(ef)
            except Exception as e:
                print(f"[清理無效篩選器失敗] ID {ef['id']}: {e}")

    # 將救援出來的無動作寄件者併入 filter_proposals
    for lbl_name, add_senders in orphaned_senders_by_label.items():
        if add_senders:
            if lbl_name not in filter_proposals:
                filter_proposals[lbl_name] = {
                    'label': lbl_name,
                    'is_new_label': False,
                    'senders': set(),
                    'email_ids': []
                }
            filter_proposals[lbl_name]['senders'].update(add_senders)

    for label_name, info in filter_proposals.items():
        label_id = get_or_create_label(service, label_name)
        
        # 1. 批次打標籤給歷史信件
        email_ids = info['email_ids']
        if email_ids:
            service.users().messages().batchModify(
                userId='me',
                body={
                    'ids': email_ids,
                    'addLabelIds': [label_id]
                }
            ).execute()
            updated_messages_count += len(email_ids)
            print(f"[標籤套用] 成功為 {len(email_ids)} 封信件加上標籤: [{label_name}]")

        # 2. 收集此標籤下的全新 Sender 提案
        new_senders = set(info['senders'])

        # 3. 在現有 Filters 中尋找所有指向此 label_id 的舊規則
        matching_existing_filters = []
        existing_conditions = set()

        for ef in existing_filters:
            add_labels = ef.get('action', {}).get('addLabelIds', [])
            if label_id in add_labels:
                matching_existing_filters.append(ef)
                criteria_from = ef.get('criteria', {}).get('from', '')
                parsed_items = parse_from_conditions(criteria_from)
                for item in parsed_items:
                    existing_conditions.add(item)

        # 4. 聯集合併「舊有的條件」與「新掃描出來的寄件者」
        all_conditions = sorted(list(existing_conditions.union(new_senders)))
        if not all_conditions:
            continue

        if len(all_conditions) == 1:
            from_query = all_conditions[0]
        else:
            from_query = f"({' OR '.join(all_conditions)})"

        # 5. 如果現有規則剛好只有 1 條，且條件完全一致，就不需刪除與重建
        if len(matching_existing_filters) == 1 and set(parse_from_conditions(matching_existing_filters[0].get('criteria', {}).get('from', ''))) == set(all_conditions):
            print(f"[篩選器比對] 標籤 [{label_name}] 的統整篩選器已是完美最新狀態，不需重設 (條件: from:{from_query})。")
            continue

        # 6. 刪除指向此標籤的所有舊分散 Filters，避免重複堆疊
        for old_filter in matching_existing_filters:
            try:
                service.users().settings().filters().delete(userId='me', id=old_filter['id']).execute()
                deleted_filters_count += 1
                print(f"[清理舊篩選器] 已清理標籤 [{label_name}] 的舊/分散篩選器 (ID: {old_filter['id']})")
            except Exception as e:
                print(f"[清理舊篩選器失敗] ID {old_filter['id']}: {e}")

        # 7. 建立整合後的單一強大 Filter 規則
        filter_body = {
            'criteria': {
                'from': from_query
            },
            'action': {
                'addLabelIds': [label_id]
            }
        }
        try:
            created_filter = service.users().settings().filters().create(
                userId='me',
                body=filter_body
            ).execute()
            created_filters_count += 1
            print(f"✨ [單一強大篩選器建立完成] 標籤 [{label_name}] 已成功將 {len(all_conditions)} 條過濾條件合併為單一 Filter 規則: from:{from_query}")
        except Exception as e:
            print(f"[篩選器建立失敗] for label [{label_name}]: {e}")

    print(f"\n🎉 統整完成！共清理 {deleted_filters_count} 條舊/分散篩選器，新增/更新 {created_filters_count} 條單一合一篩選器，並更新 {updated_messages_count} 封舊信件標籤。")
