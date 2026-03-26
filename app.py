from flask import Flask, render_template, request, jsonify
import sqlite3, os, re, threading, traceback
from downloader import DL
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import filedialog

app = Flask(__name__)
app.secret_key = os.urandom(24)

# 全域狀態
sync_state = {
    "is_running": False, 
    "total": 0, 
    "current_idx": 0, 
    "current_name": "", 
    "msg": "", 
    "error": ""
}

def get_db():
    conn = sqlite3.connect('yt_tracker.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/sync_manager', methods=['GET', 'POST'])
def sync_manager():
    conn = get_db()
    if request.method == 'POST' and 'import_url' in request.form:
        url = request.form.get('import_url').strip()
        import yt_dlp
        with yt_dlp.YoutubeDL({'extract_flat': True, 'quiet': True}) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if info:
                    cid = info.get('channel_id') or info.get('id')
                    cname = info.get('uploader') or info.get('title')
                    conn.execute('INSERT OR IGNORE INTO channels VALUES (?,?)', (cid, cname))
                    pl_info = ydl.extract_info(f"https://www.youtube.com/channel/{cid}/playlists", download=False)
                    if pl_info and 'entries' in pl_info:
                        for entry in pl_info.get('entries', []):
                            conn.execute('INSERT OR IGNORE INTO playlists VALUES (?,?,0,?)', (entry['id'], entry['title'], cid))
                    conn.commit()
            except Exception as e:
                print(f"Import Error: {e}")
    
    channels_data = []
    rows = conn.execute('SELECT * FROM channels').fetchall()
    for row in rows:
        c = dict(row)
        c['playlists'] = conn.execute('SELECT * FROM playlists WHERE channel_id=?', (row['id'],)).fetchall()
        channels_data.append(c)
    return render_template('sync_manager.html', channels=channels_data)

@app.route('/start_sync', methods=['POST'])
def start_sync():
    global sync_state
    if sync_state["is_running"]:
        return jsonify({"status": "error", "message": "任務正在進行中"})
    
    path = request.json.get('path')
    if not path or not os.path.exists(path):
        return jsonify({"status": "error", "message": "下載路徑無效"})

    conn = get_db()
    items = conn.execute('''
        SELECT p.*, c.name as c_name 
        FROM playlists p 
        JOIN channels c ON p.channel_id = c.id 
        WHERE p.track_flag > 0
    ''').fetchall()
    
    if not items:
        return jsonify({"status": "error", "message": "請先勾選要同步的播放清單"})

    def run_sync_thread():
        global sync_state
        sync_state.update({"is_running": True, "total": len(items), "current_idx": 0, "msg": "Running", "error": ""})
        DL.is_stop_requested = False
        DL.last_error = ""

        try:
            # 這裡建議使用單執行緒或較少的 worker 避免 YouTube 封鎖 IP
            with ThreadPoolExecutor(max_workers=1) as executor:
                futures = []
                for i, item in enumerate(items):
                    if DL.is_stop_requested: break
                    
                    sync_state.update({"current_idx": i + 1, "current_name": item['title']})
                    c_safe = re.sub(r'[\\/:*?"<>|]', '', item['c_name'])
                    p_safe = re.sub(r'[\\/:*?"<>|]', '', item['title'])
                    save_dir = os.path.join(path, c_safe, p_safe)
                    
                    # 判斷是否僅下載音訊 (track_flag=1 為音樂)
                    audio_only = (item['track_flag'] == 1)
                    
                    f = executor.submit(DL.download, 
                                        f"https://www.youtube.com/playlist?list={item['id']}", 
                                        save_dir, 
                                        item['channel_id'], 
                                        audio_only)
                    futures.append(f)
                
                for f in futures: f.result()
                
        except Exception as e:
            sync_state["error"] = str(e)
        
        sync_state.update({"is_running": False, "msg": "FINISH", "error": DL.last_error})

    threading.Thread(target=run_sync_thread, daemon=True).start()
    return jsonify({"status": "started"})

@app.route('/sync_status')
def sync_status():
    return jsonify({**sync_state, "dl_msg": DL.current_status})

@app.route('/stop_sync', methods=['POST'])
def stop_sync():
    DL.is_stop_requested = True
    return jsonify({"status": "stop_requested"})

@app.route('/toggle_flag_ajax', methods=['POST'])
def toggle_flag_ajax():
    data = request.get_json()
    with get_db() as conn:
        conn.execute('UPDATE playlists SET track_flag=? WHERE id=?', (data['newFlag'], data['playlistId']))
        conn.commit()
    return jsonify({'status': 'ok'})

@app.route('/select_folder', methods=['POST'])
def select_folder():
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askdirectory()
        root.destroy()
        return jsonify({'folder': path})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    conn = sqlite3.connect('yt_tracker.db')
    conn.execute('CREATE TABLE IF NOT EXISTS channels (id TEXT PRIMARY KEY, name TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS playlists (id TEXT PRIMARY KEY, title TEXT, track_flag INTEGER, channel_id TEXT)')
    conn.close()
    app.run(debug=True, port=5000)