# 📧 Gmail 信件自動分類與篩選器規則預覽提案 (Classification Proposal)

掃描時間：共找到 **22** 封未加上自定義標籤的舊信件。

## 📌 擬定的標籤分類與篩選器規則清單

### 🏷️ 現有標籤：`資訊`
- **涵蓋歷史信件數**：19 封
- **統整合併後的單一篩選條件 (Unified Filter Rule)**：
  - `from: (enews@newmx.cnyes.com OR itservice@tozostore.com OR lia_service@mail.lia-roc.org.tw OR marketing@hueiyeh.com.tw OR newsletter@customer.foreo.com OR no-reply@hhgalaxy.com.tw OR noreply-accounts@google.com OR reply@em.surveymonkey.com)` ➡️ 自動加上標籤 `[資訊]`

### 🏷️ 現有標籤：`知識`
- **涵蓋歷史信件數**：2 封
- **統整合併後的單一篩選條件 (Unified Filter Rule)**：
  - `from: (104news@ms1.104.com.tw OR subscriptions@medium.com)` ➡️ 自動加上標籤 `[知識]`

### 🏷️ 現有標籤：`娛樂`
- **涵蓋歷史信件數**：1 封
- **統整合併後的單一篩選條件 (Unified Filter Rule)**：
  - `from: no-reply@newsletter.bookwalker.com.tw` ➡️ 自動加上標籤 `[娛樂]`


## ✉️ 未標籤信件詳細分類對照表

| 寄件者 (From) | 信件主旨 (Subject) | 建議標籤 (Label) | 狀態 |
| --- | --- | --- | --- |
| FOREO <newsletter@customer.foreo.com> | Get even more out of your LUNA™ ✨ | `資訊` | 現有標籤 |
| FOREO <newsletter@customer.foreo.com> | NEW! Oral care just got more sensible with issa™ Teeth Whitening Set ✨ | `資訊` | 現有標籤 |
| "鉅亨會員報 " <enews@newmx.cnyes.com> | 🚨 倒數 9 天！下半年大盤變局，你的「保命裝備」領了沒？7/25 散戶生存特訓班 | `資訊` | 現有標籤 |
| Simon Liu <subscriptions@medium.com> | [ Model Fine-Tuning ] 我要一個「做事情」的 Fine-Tuned Model — 來看做事小模型 Agent 的可能性（APMIC PrivStationDay 演講內容精華） | `知識` | 現有標籤 |
| "輝葉良品" <marketing@hueiyeh.com.tw> | 輝葉良品父親節指定商品55折起最高省萬元 | `資訊` | 現有標籤 |
| FOREO <newsletter@customer.foreo.com> | Wrapping up our birthday! 24 hours left! 🎂 | `資訊` | 現有標籤 |
| FOREO <newsletter@customer.foreo.com> | Welcome to the beautiful world of FOREO! | `資訊` | 現有標籤 |
| FOREO <newsletter@customer.foreo.com> | Enjoy the beautiful world of FOREO 💕 | `資訊` | 現有標籤 |
| Google <noreply-accounts@google.com> | 您與「project-1081059688934」分享了部分 Google 帳戶資料 | `資訊` | 現有標籤 |
| "保險存摺" <lia_service@mail.lia-roc.org.tw> | [保險存摺] 您已申請升級為白金會員，請進行繳費，謝謝您。 | `資訊` | 現有標籤 |
| "保險存摺" <lia_service@mail.lia-roc.org.tw> | [保險存摺] 您已申請升級為白金會員，請進行繳費，謝謝您。 | `資訊` | 現有標籤 |
| "保險存摺" <lia_service@mail.lia-roc.org.tw> | [續約優惠] 您的白金會員即將到期，續約優惠價75元，逾期未繳者將恢復為普通會員 | `資訊` | 現有標籤 |
| FOREO <newsletter@customer.foreo.com> | Red LED is here to stay. Our Birthday offers aren't... 🔴🎂 | `資訊` | 現有標籤 |
| FOREO <newsletter@customer.foreo.com> | Birthday party: full body edition! 🎂✨ | `資訊` | 現有標籤 |
| "BOOK☆WALKER" <no-reply@newsletter.bookwalker.com.tw> | 2026 夏季新番開播⏰ 7/16 前還有限定套書😍 | `娛樂` | 現有標籤 |
| SurveyMonkey <reply@em.surveymonkey.com> | 歡迎使用！帳戶資訊 | `資訊` | 現有標籤 |
| Google <noreply-accounts@google.com> | 您與「SurveyMonkey」分享了部分 Google 帳戶資料 | `資訊` | 現有標籤 |
| FOREO <newsletter@customer.foreo.com> | The wand LED devices are having their moment! ✨ | `資訊` | 現有標籤 |
| TOZO <itservice@tozostore.com> | [TOZO] Message | `資訊` | 現有標籤 |
| "meijishop 明治官方購物網站" <no-reply@hhgalaxy.com.tw> | 🖤meijishop SAVAS運動蛋白盛夏祭典 結帳57折起🖤｜明治官方購物網站 | `資訊` | 現有標籤 |
| "104人力銀行" <104news@ms1.104.com.tw> | 【最後５位｜7/25 (六) 開課】領券最高折$1,399↘NVIDIA 官方獨家課程 - 擴散模型的生成式AI應用：2日假日直播班+NVIDIA AI實作+課程GPU免費+104獨家履歷標註=助攻您職涯發展｜104課程中心 | `知識` | 現有標籤 |
| FOREO <newsletter@customer.foreo.com> | 13 years, two bestsellers. Can you guess them? 👀✨ | `資訊` | 現有標籤 |

---

> **提示**：若您認同以上標籤與 Filter 規則，請執行 `python gmail_service/main.py --apply` 來批次套用標籤並寫入 Gmail 篩選器！