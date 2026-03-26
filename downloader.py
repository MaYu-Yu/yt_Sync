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
        if os.path.exists(self.ffmpeg_bin):
            return

        try:
            self.current_status = "正在初始化環境 (下載 FFmpeg)..."
            print(">>> 偵測到缺少 FFmpeg，開始自動下載...")
            
            ffmpeg_zip = os.path.join(self.base_path, "ffmpeg_temp.zip")
            ffmpeg_url = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
            
            urllib.request.urlretrieve(ffmpeg_url, ffmpeg_zip)
            
            print(">>> 正在解壓縮 FFmpeg...")
            subprocess.run(
                ["tar", "-xf", ffmpeg_zip], 
                cwd=self.base_path, 
                shell=True, 
                creationflags=0x08000000 
            )
            
            extracted_folders = glob.glob(os.path.join(self.base_path, "ffmpeg-master-latest*"))
            if extracted_folders:
                if os.path.exists(self.ffmpeg_dir):
                    shutil.rmtree(self.ffmpeg_dir)
                os.rename(extracted_folders[0], self.ffmpeg_dir)
            
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
            self.current_status = "處理檔案中..."

    def download(self, url, save_path, channel_id, audio_only):
        os.makedirs(self.data_dir, exist_ok=True)
        archive_path = os.path.join(self.data_dir, f"history_{channel_id}.txt")
        
        # 核心設定
        opts = {
            'ffmpeg_location': self.ffmpeg_bin,
            'outtmpl': os.path.join(save_path, "%(title)s.%(ext)s"),
            'download_archive': archive_path,
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'noprogress': True,
            'extract_flat': False,
            'ignoreerrors': False,
            'overwrites': True,
            
            # 啟用縮圖與 Metadata 功能
            'writethumbnail': True,
            'addmetadata': True,
        }

        # 定義後處理器清單
        postprocessors = [
            # 寫入影片/音樂詳細資訊
            {'key': 'FFmpegMetadata', 'add_chapters': True},
            # 將下載的縮圖嵌入檔案
            {'key': 'EmbedThumbnail'},
        ]

        if audio_only:
            opts.update({'format': 'bestaudio/best'})
            # 音頻轉檔必須放在後處理器的第一位
            postprocessors.insert(0, {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            })
        else:
            opts.update({'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'})

        # 將組合好的後處理器寫入 opts
        opts['postprocessors'] = postprocessors

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

if __name__ == "__main__":
    DL = YTDownloader()