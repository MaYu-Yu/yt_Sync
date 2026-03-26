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
@app.route('/delete_channel', methods=['POST'])
def delete_channel():
    data = request.get_json()
    cid = data.get('channel_id')
    if not cid:
        return jsonify({'status': 'error', 'message': '接收到的頻道ID為空'}), 400
    
    try:
        with get_db() as conn:
            # 刪除播放清單
            conn.execute('DELETE FROM playlists WHERE channel_id = ?', (cid,))
            # 刪除頻道（根據你的庫結構，這裡通常是 id）
            conn.execute('DELETE FROM channels WHERE id = ?', (cid,))
            conn.commit()
        
        return jsonify({'status': 'ok'}) 
        
    except Exception as e:
        print(f"刪除報錯: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
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

@app.route('/stop_sync', methods=['POST'])
def stop_sync():
    global sync_state
    DL.is_stop_requested = True
    sync_state["is_running"] = False # 強行停止，讓前端 polling 讀到 False
    sync_state["msg"] = "USER_STOPPED"
    return jsonify({"status": "stop_requested"})

@app.route('/start_sync', methods=['POST'])
def start_sync():
    global sync_state
    if sync_state["is_running"]:
        return jsonify({"status": "error", "message": "任務進行中"})
    
    path = request.json.get('path')
    conn = get_db()
    # 取得所有待同步的清單
    items = conn.execute('SELECT p.*, c.name as c_name FROM playlists p JOIN channels c ON p.channel_id = c.id WHERE p.track_flag > 0').fetchall()
    
    if not items: return jsonify({"status": "error", "message": "未選擇清單"})

    def run_sync_logic():
        global sync_state
        sync_state.update({"is_running": True, "total": len(items), "current_idx": 0, "msg": "RUNNING"})
        DL.is_stop_requested = False
        save_dir = ""

        try:
            for i, item in enumerate(items):
                # 檢查點 1：清單切換時立即檢查
                if not sync_state["is_running"] or DL.is_stop_requested:
                    break

                # 【修正】先更新索引，這樣進度條才會立刻從 0/5 變成 1/5
                sync_state.update({"current_idx": i + 1, "current_name": item['title']})
                
                c_safe = re.sub(r'[\\/:*?"<>|]', '', item['c_name'])
                p_safe = re.sub(r'[\\/:*?"<>|]', '', item['title'])
                save_dir = os.path.join(path, c_safe, p_safe)
                os.makedirs(save_dir, exist_ok=True)

                try:
                    DL.download(f"https://www.youtube.com/playlist?list={item['id']}", 
                                save_dir, item['channel_id'], (item['track_flag'] == 1))
                except Exception as e:
                    # 【核心修正】如果捕捉到使用者停止的訊號，直接 break 整個迴圈
                    if "USER_STOP" in str(e) or DL.is_stop_requested:
                        print("偵測到停止信號，終止後續所有清單下載")
                        break
                    continue
        finally:
            if DL.is_stop_requested and save_dir:
                DL.cleanup_temp_files(save_dir)
            sync_state["is_running"] = False
            DL.is_stop_requested = False

    threading.Thread(target=run_sync_logic, daemon=True).start()
    return jsonify({"status": "started"})

@app.route('/sync_status')
def sync_status():
    return jsonify({**sync_state, "dl_msg": DL.current_status})

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