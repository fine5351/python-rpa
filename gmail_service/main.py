import os
import sys
import json
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gmail_service.gmail_auth import get_gmail_service
from gmail_service.fetch_unlabeled import fetch_unlabeled_messages
from gmail_service.analyzer import analyze_and_group_emails
from gmail_service.apply_rules import apply_classification_and_filters

CACHE_PLAN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'proposed_plan.json')
PROPOSAL_MD_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gmail_classification_proposal.md')


def run_scan_and_plan(max_results=50):
    print("==================================================")
    print("🔍 [階段一] 連結 Gmail 並掃描無自定義標籤信件...")
    print("==================================================")
    
    try:
        service = get_gmail_service()
    except FileNotFoundError:
        return None

    unlabeled_emails, user_labels = fetch_unlabeled_messages(service, max_results=max_results)
    
    if not unlabeled_emails:
        print("🎉 太棒了！您所有的信件都已經加上自定義標籤，目前沒有未分類信件！")
        return None

    classification_results, filter_proposals = analyze_and_group_emails(unlabeled_emails, user_labels)

    # 序列化 set 為 list 以便存為 JSON
    serializable_proposals = {}
    for lbl, info in filter_proposals.items():
        serializable_proposals[lbl] = {
            'label': info['label'],
            'is_new_label': info['is_new_label'],
            'senders': list(info['senders']),
            'email_ids': info['email_ids']
        }

    with open(CACHE_PLAN_FILE, 'w', encoding='utf-8') as f:
        json.dump(serializable_proposals, f, ensure_ascii=False, indent=2)

    # 產生 Markdown 預覽報告
    md_content = []
    md_content.append("# 📧 Gmail 信件自動分類與篩選器規則預覽提案 (Classification Proposal)\n")
    md_content.append(f"掃描時間：共找到 **{len(unlabeled_emails)}** 封未加上自定義標籤的舊信件。\n")
    md_content.append("## 📌 擬定的標籤分類與篩選器規則清單\n")
    
    for lbl, info in serializable_proposals.items():
        status_tag = "🆕 新增標籤" if info['is_new_label'] else "🏷️ 現有標籤"
        senders = sorted(info['senders'])
        md_content.append(f"### {status_tag}：`{lbl}`")
        md_content.append(f"- **涵蓋歷史信件數**：{len(info['email_ids'])} 封")
        
        if len(senders) == 1:
            unified_query = senders[0]
        else:
            unified_query = f"({' OR '.join(senders)})"

        md_content.append(f"- **統整合併後的單一篩選條件 (Unified Filter Rule)**：")
        md_content.append(f"  - `from: {unified_query}` ➡️ 自動加上標籤 `[{lbl}]`")
        md_content.append("")

    md_content.append("\n## ✉️ 未標籤信件詳細分類對照表\n")
    md_content.append("| 寄件者 (From) | 信件主旨 (Subject) | 建議標籤 (Label) | 狀態 |")
    md_content.append("| --- | --- | --- | --- |")
    
    for res in classification_results:
        status = "新標籤" if res['is_new_label'] else "現有標籤"
        # 替換管道符號避免 Markdown 表格錯亂
        subj = res['subject'].replace('|', '&#124;')
        sender = res['from'].replace('|', '&#124;')
        md_content.append(f"| {sender} | {subj} | `{res['suggested_label']}` | {status} |")

    md_content.append("\n---\n")
    md_content.append("> **提示**：若您認同以上標籤與 Filter 規則，請執行 `python gmail_service/main.py --apply` 來批次套用標籤並寫入 Gmail 篩選器！")

    with open(PROPOSAL_MD_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_content))

    print(f"\n✅ 掃描與計畫擬定完成！分析報告已產出至: {PROPOSAL_MD_FILE}")
    print("請查看 `gmail_classification_proposal.md` 確認擬定的分類與篩選器規則！")
    return serializable_proposals


def run_apply():
    print("==================================================")
    print("🚀 [階段二] 批次套用標籤與寫入 Gmail Filter 規則...")
    print("==================================================")

    if not os.path.exists(CACHE_PLAN_FILE):
        print("❌ 找不到先前的分類計畫 cache 檔案 (proposed_plan.json)。請先執行 --scan！")
        return

    with open(CACHE_PLAN_FILE, 'r', encoding='utf-8') as f:
        serializable_proposals = json.load(f)

    # 轉回原本 expected structure
    filter_proposals = {}
    for lbl, info in serializable_proposals.items():
        filter_proposals[lbl] = {
            'label': info['label'],
            'is_new_label': info['is_new_label'],
            'senders': set(info['senders']),
            'email_ids': info['email_ids']
        }

    service = get_gmail_service()
    apply_classification_and_filters(service, filter_proposals)
    print("\n🎉 成功完成了信件標籤批次套用與未來篩選器規則建立！")


def main():
    parser = argparse.ArgumentParser(description="Gmail Auto-Categorizer & Filter Manager")
    parser.add_argument('--scan', action='store_true', help="掃描未標籤信件並產生分類建議預覽")
    parser.add_argument('--apply', action='store_true', help="執行標籤建立、舊信件套用與 Filter 規則寫入")
    parser.add_argument('--max', type=int, default=50, help="最多掃描幾封未標籤信件 (預設 50)")

    args = parser.parse_args()

    if args.scan:
        run_scan_and_plan(max_results=args.max)
    elif args.apply:
        run_apply()
    else:
        # 預設行為：若有 credentials 則執行 scan
        run_scan_and_plan(max_results=args.max)

if __name__ == '__main__':
    main()
