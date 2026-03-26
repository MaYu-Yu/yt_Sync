🛠️ Mayuyu's Gadget - 個人工具整合平台
一個基於 Flask 開發的個人輕量級工具箱。目前核心功能為強大的 YouTube 播放清單同步管理器，未來將持續擴充更多實用的小工具。

🌟 核心功能：YouTube 自動同步管理器 (Sync Manager)
這是專為 FFXIV 玩家或音樂愛好者設計的同步工具，能將你關注的 YouTube 頻道與播放清單自動備份至本地空間。

⚡ 免安裝 FFmpeg：啟動時自動偵測並在本地下載配置 FFmpeg，無需手動設定系統環境變數。

📂 頻道與清單管理：輸入 YouTube 頻道 ID 即可自動解析所有公開播放清單。

🔄 增量更新技術：內建 download_archive 歷史記錄，只下載新出的影片，絕不重複下載。

🎶 多模式支援：支援「最高畫質 MP4」或「純音訊 MP3」轉檔。

🎨 現代化 UI：採用 Inter 字體與漸層風格設計，具備流暢的動畫效果與即時進度監控。

🚀 快速開始
1. 環境需求
Python 3.8+

Windows 10/11 (支援自動解壓 tar 指令)

2. 安裝套件
克隆專案並安裝必要的 Python 庫：

Bash
git clone <你的專案網址>
cd <專案目錄>
pip install flask yt-dlp psutil
3. 啟動程式
Bash
python app.py
啟動後，請訪問：http://127.0.0.1:5000

📖 使用指南
首頁導航：在 index.html 中選擇 YouTube Sync Manager。

自動化初始化：程式首次啟動會檢查目錄下是否有 ffmpeg 資料夾。若無，將自動從 GitHub 下載最新 master 分支版本（約 100MB），請耐心等待。

導入頻道：進入管理頁面，輸入頻道 ID（如 UCxxxxxxxx），點擊導入。

設定路徑：點擊資料夾圖示，透過視窗選取本地儲存路徑。

一鍵同步：按下「開始同步」，程式將自動輪詢所有勾選的清單並進行下載。

📂 專案架構
Plaintext
.
├── app.py              # Flask Web 服務與資料庫 API
├── downloader.py       # 核心下載邏輯 (自動部署 FFmpeg 與 yt-dlp 調用)
├── yt_tracker.db       # SQLite 資料庫 (儲存頻道與清單設定)
├── data/               # 儲存下載歷史記錄 (*.txt)
├── templates/          # 前端 HTML 模板 (index, sync_manager, base)
└── ffmpeg/             # (自動生成) 本地 FFmpeg 執行檔目錄
⚠️ 注意事項
首下載時間：初次啟動因需下載 ffmpeg，可能會有一段時間進度條無反應，請查看終端機 (Terminal) 的下載進度。

權限說明：本工具僅供個人備份與學術研究使用，請遵守 YouTube 服務條款及尊重創作者版權。