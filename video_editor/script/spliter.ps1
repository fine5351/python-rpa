# 基本用法（使用預設值：去除 >2 秒靜止畫面，每 30 到 45 分鐘切分，優先切在黑/白畫面）
python .\video_editor\video_splitter.py -i "F:\OBS-VideoRecord\2026-06-22 16-16-57.mp4"

# 進階參數調整
python .\video_editor\video_splitter.py -i "F:\原神-傳說任務-狡兔之章.mp4" `
    -o "F:\原神-傳說任務-狡兔之章\" `
    --min-split 30 `
    --max-split 45 `
    --static-threshold 0.8 `
    --black-threshold 0.90 `
    --white-threshold 0.90 `
    --black-pixel-limit 30 `
    --white-pixel-limit 225
