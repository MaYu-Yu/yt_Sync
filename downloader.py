import os, sys, yt_dlp, glob, time, urllib.request, subprocess, shutil

class YTDownloader:
    def __init__(self):
        # 基礎路徑設定
        self.base_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.base_path, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # FFmpeg 相關路徑
        self.ffmpeg_dir = os.path.join(self.base_path, "ffmpeg")
        self.ffmpeg_bin = os.path.join(self.ffmpeg_dir, "bin")
        
        self.is_stop_requested = False
        self.current_status = ""
        
        # 啟動時自動檢查 FFmpeg
        self.auto_setup_ffmpeg()

    def auto_setup_ffmpeg(self):
        """檢查並在本地下載配置 FFmpeg"""
        # 如果 bin 目錄已存在，視為已安裝
        if os.path.exists(self.ffmpeg_bin):
            return

        try:
            self.current_status = "正在初始化環境 (下載 FFmpeg)..."
            print(">>> 偵測到缺少 FFmpeg，開始自動下載...")
            
            ffmpeg_zip = os.path.join(self.base_path, "ffmpeg_temp.zip")
            # 使用 yt-dlp 推薦的 FFmpeg 編譯版本
            ffmpeg_url = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
            
            # 下載壓縮檔
            urllib.request.urlretrieve(ffmpeg_url, ffmpeg_zip)
            
            print(">>> 正在解壓縮 FFmpeg...")
            # 使用 Windows 內建 tar 指令解壓
            subprocess.run(
                ["tar", "-xf", ffmpeg_zip], 
                cwd=self.base_path, 
                shell=True, 
                creationflags=0x08000000 # 隱藏 CMD 視窗
            )
            
            # 尋找解壓後的資料夾 (通常名稱會帶有 master-latest)
            extracted_folders = glob.glob(os.path.join(self.base_path, "ffmpeg-master-latest*"))
            if extracted_folders:
                if os.path.exists(self.ffmpeg_dir):
                    shutil.rmtree(self.ffmpeg_dir)
                os.rename(extracted_folders[0], self.ffmpeg_dir)
            
            # 清理暫存檔
            if os.path.exists(ffmpeg_zip):
                os.remove(ffmpeg_zip)
                
            print(">>> FFmpeg 本地化設置完成")
            self.current_status = "環境檢查完成"
            
        except Exception as e:
            self.current_status = f"FFmpeg 下載失敗: {e}"
            print(f"!!! FFmpeg setup error: {e}")

    def cleanup_temp_files(self, save_path):
        if not os.path.exists(save_path): return
        time.sleep(1.5) 
        temp_patterns = ['*.part', '*.ytdl', '*.temp', '*.tmp', '*.part.temp']
        for pat in temp_patterns:
            for f in glob.glob(os.path.join(save_path, pat)):
                try: os.remove(f)
                except: pass

    def progress_hook(self, d):
        if self.is_stop_requested:
            raise Exception("USER_STOP")
            
        if d['status'] == 'downloading':
            self.current_status = "下載中..."
        elif d['status'] == 'finished':
            self.current_status = "合併檔案中..."

    def download(self, url, save_path, channel_id, audio_only):
        os.makedirs(self.data_dir, exist_ok=True)
        archive_path = os.path.join(self.data_dir, f"history_{channel_id}.txt")
        
        # 核心設定：確保 ffmpeg_location 指向我們剛才下載的目錄
        opts = {
            'ffmpeg_location': self.ffmpeg_bin,
            'outtmpl': os.path.join(save_path, "%(title)s.%(ext)s"),
            'download_archive': archive_path,
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'noprogress': True,
            'extract_flat': False,
            'ignoreerrors': False,
        }

        if audio_only:
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192'
                }]
            })
        else:
            # 優先下載 mp4 格式以減少轉碼時間
            opts.update({'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'})

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

DL = YTDownloader()