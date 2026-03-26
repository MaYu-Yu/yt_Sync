import os, sys, yt_dlp, glob, time

class YTDownloader:
    def __init__(self):
        # 基礎路徑設定
        self.base_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.base_path, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.ffmpeg_bin = os.path.join(self.base_path, "ffmpeg", "bin")
        self.is_stop_requested = False
        self.current_status = ""

    def cleanup_temp_files(self, save_path):
        if not os.path.exists(save_path): return
        
        # 必須等待，否則檔案被系統鎖住刪不掉
        time.sleep(1.5) 
        
        # 擴展可能的暫存檔副檔名
        temp_patterns = ['*.part', '*.ytdl', '*.temp', '*.tmp', '*.part.temp']
        for pat in temp_patterns:
            for f in glob.glob(os.path.join(save_path, pat)):
                try:
                    os.remove(f)
                except:
                    pass

    def progress_hook(self, d):
        # 只要有一丁點訊號就立刻爆破下載程序
        if self.is_stop_requested:
            raise Exception("USER_STOP")
            
        if d['status'] == 'downloading':
            self.current_status = f"下載中: {d.get('_percent_str', '0%')}"
        elif d['status'] == 'finished':
            self.current_status = "合併檔案中..."

    def download(self, url, save_path, channel_id, audio_only):
        os.makedirs(self.data_dir, exist_ok=True)
        archive_path = os.path.join(self.data_dir, f"history_{channel_id}.txt")
        
        opts = {
            'ffmpeg_location': self.ffmpeg_bin,
            'outtmpl': os.path.join(save_path, "%(title)s.%(ext)s"),
            'download_archive': archive_path,
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'noprogress': True,
            'extract_flat': False, # 減少對外部 JS runtime 依賴
            'ignoreerrors': True,
        }

        if audio_only:
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]
            })
        else:
            opts.update({'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'})

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

DL = YTDownloader()