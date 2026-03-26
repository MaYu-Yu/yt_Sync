import os, sys, yt_dlp, traceback, glob

class YTDownloader:
    def __init__(self):
        self.base_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.base_path, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.ffmpeg_bin = os.path.join(self.base_path, "ffmpeg", "bin")
        self.is_stop_requested = False
        self.current_status = ""
        self.last_error = ""

    def cleanup_temp_files(self, save_path):
        """ 清理下載中斷或失敗產生的臨時檔案 """
        temp_exts = ['*.part', '*.temp', '*.ytdl', '*.tmp', '*.webp', '*.jpg']
        for ext in temp_exts:
            files = glob.glob(os.path.join(save_path, ext))
            for f in files:
                try:
                    os.remove(f)
                except:
                    pass

    def progress_hook(self, d):
        # 這是觸發中斷的核心點
        if self.is_stop_requested:
            raise Exception("USER_STOP")
            
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%')
            s = d.get('_speed_str', 'N/A')
            self.current_status = f"正在下載: {p} ({s})"
        elif d['status'] == 'finished':
            self.current_status = "🎨 正在寫入標籤、章節與封面..."

    def download(self, url, save_path, channel_id, audio_only=False):
        try:
            self.is_stop_requested = False
            os.makedirs(save_path, exist_ok=True)
            archive_path = os.path.join(self.data_dir, f"history_{channel_id}.txt")
            
            opts = {
                'ffmpeg_location': self.ffmpeg_bin,
                'outtmpl': os.path.join(save_path, "%(title)s.%(ext)s"),
                'download_archive': archive_path,
                'ignoreerrors': True,
                'nooverwrites': True,
                'progress_hooks': [self.progress_hook],
                'quiet': True,
                'merge_output_format': 'mp4',
                'writethumbnail': True, 
            }

            pp = [
                {'key': 'FFmpegMetadata', 'add_metadata': True, 'add_chapters': True},
                {'key': 'EmbedThumbnail'},
            ]
            
            if audio_only:
                opts['format'] = 'bestaudio/best'
                opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192'
                }] + pp
            else:
                opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                opts['postprocessors'] = pp

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

        except Exception as e:
            if "USER_STOP" in str(e):
                self.current_status = "STOPPED"
                self.cleanup_temp_files(save_path)
            else:
                self.last_error = str(e)
                print(f"DL Error: {traceback.format_exc()}")

DL = YTDownloader()