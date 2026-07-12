from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, HTMLResponse
import requests
import json
from datetime import datetime

app = FastAPI()

# ==================== AYARLAR ====================
GIST_ID = "0711dfba4936dc2c74e360d4255b14c9"
GITHUB_TOKEN = "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"

# ==================== GIST FONKSİYONLARI ====================
def veri_oku():
    try:
        url = f"https://api.github.com/gists/{GIST_ID}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            content = resp.json()["files"]["playlist.json"]["content"]
            return json.loads(content)
    except:
        pass
    return {"playlists": [], "aktif_index": 0, "m3u_url": ""}

def veri_kaydet(data):
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {
        "files": {
            "playlist.json": {
                "content": json.dumps(data, ensure_ascii=False, indent=2)
            }
        }
    }
    requests.patch(url, headers=headers, json=payload)

# ==================== TV ENDPOİNTİ (M3U) ====================
@app.get("/get", response_class=PlainTextResponse)
def playlist_getir():
    data = veri_oku()
    m3u_url = data.get("m3u_url", "")
    if not m3u_url:
        return "#EXTM3U\n#EXTINF:-1,Henuz playlist eklenmedi\nhttp://localhost"
    try:
        r = requests.get(m3u_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        return r.text
    except Exception as e:
        return f"#EXTM3U\n#EXTINF:-1,Hata: {str(e)}\nhttp://localhost"

# ==================== WEB PANELİ ====================
@app.get("/", response_class=HTMLResponse)
def panel():
    data = veri_oku()
    playlists = data.get("playlists", [])
    aktif_url = data.get("m3u_url", "")

    playlist_html = ""
    for i, p in enumerate(playlists):
        aktif_badge = '<span style="color:#00ff88;font-size:12px;"> ✅ AKTİF</span>' if p["url"] == aktif_url else ""
        playlist_html += f"""
        <div class="playlist-item">
            <div class="playlist-info">
                <strong>{p['isim']}{aktif_badge}</strong>
                <small>{p['url'][:60]}...</small>
                <small style="color:#555;">{p.get('tarih', '')}</small>
            </div>
            <div class="playlist-actions">
                <form method="post" action="/aktif/{i}" style="display:inline;">
                    <button type="submit" class="btn-aktif">Aktif Yap</button>
                </form>
                <form method="post" action="/sil/{i}" style="display:inline;">
                    <button type="submit" class="btn-sil">Sil</button>
                </form>
            </div>
        </div>
        """

    if not playlist_html:
        playlist_html = '<p style="color:#555;text-align:center;">Henuz playlist eklenmedi</p>'

    durum_renk = "#00ff88" if aktif_url else "#ff4757"
    durum_yazi = "AKTİF PLAYLİST MEVCUT" if aktif_url else "PLAYLİST EKLENMEDİ"

    return f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IPTV Panelim</title>
        <style>
            * {{ margin:0; padding:0; box-sizing:border-box; }}
            body {{
                font-family: 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
                min-height: 100vh;
                color: #fff;
                padding: 20px;
            }}
            .container {{ max-width: 700px; margin: 0 auto; }}
            h1 {{
                text-align: center;
                font-size: 2em;
                margin: 30px 0 10px;
                background: linear-gradient(90deg, #00d2ff, #3a7bd5);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            .subtitle {{
                text-align: center;
                color: #888;
                margin-bottom: 30px;
            }}
            .durum {{
                text-align: center;
                padding: 12px;
                border-radius: 10px;
                margin-bottom: 25px;
                font-weight: bold;
                color: {durum_renk};
                border: 1px solid {durum_renk};
                background: rgba(0,0,0,0.2);
            }}
            .card {{
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 16px;
                padding: 25px;
                margin-bottom: 20px;
            }}
            .card h2 {{
                color: #00d2ff;
                margin-bottom: 20px;
                font-size: 1.2em;
            }}
            .form-row {{
                display: flex;
                gap: 10px;
                margin-bottom: 12px;
            }}
            .form-group {{ flex: 1; }}
            label {{
                display: block;
                color: #aaa;
                font-size: 0.85em;
                margin-bottom: 6px;
            }}
            input[type=text] {{
                width: 100%;
                padding: 12px 15px;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 10px;
                background: rgba(255,255,255,0.08);
                color: #fff;
                font-size: 0.95em;
            }}
            input[type=text]:focus {{
                outline: none;
                border-color: #00d2ff;
            }}
            .btn-ekle {{
                width: 100%;
                padding: 14px;
                border: none;
                border-radius: 10px;
                background: linear-gradient(90deg, #00d2ff, #3a7bd5);
                color: #fff;
                font-size: 1.05em;
                font-weight: bold;
                cursor: pointer;
                margin-top: 10px;
            }}
            .btn-ekle:hover {{ opacity: 0.85; }}
            .playlist-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 14px;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
                margin-bottom: 10px;
                background: rgba(255,255,255,0.03);
            }}
            .playlist-info {{
                display: flex;
                flex-direction: column;
                gap: 4px;
            }}
            .playlist-info small {{ color: #555; font-size: 0.8em; }}
            .playlist-actions {{ display: flex; gap: 8px; }}
            .btn-aktif {{
                padding: 8px 14px;
                border: 1px solid #00d2ff;
                border-radius: 8px;
                background: transparent;
                color: #00d2ff;
                cursor: pointer;
                font-size: 0.8em;
            }}
            .btn-sil {{
                padding: 8px 14px;
                border: 1px solid #ff4757;
                border-radius: 8px;
                background: transparent;
                color: #ff4757;
                cursor: pointer;
                font-size: 0.8em;
            }}
            .tv-box {{
                background: rgba(0,210,255,0.08);
                border: 1px solid rgba(0,210,255,0.25);
                border-radius: 12px;
                padding: 20px;
                text-align: center;
                margin-top: 20px;
            }}
            .tv-box h3 {{ color: #00d2ff; margin-bottom: 12px; }}
            .tv-link {{
                background: rgba(0,0,0,0.3);
                border-radius: 8px;
                padding: 12px;
                font-family: monospace;
                font-size: 1em;
                color: #00d2ff;
                word-break: break-all;
                margin: 10px 0;
            }}
            .tv-box p {{ color: #888; font-size: 0.85em; line-height: 1.8; }}
            @media(max-width:600px) {{
                .form-row {{ flex-direction: column; }}
                .playlist-item {{ flex-direction: column; gap: 10px; }}
                .playlist-actions {{ width: 100%; }}
                .btn-aktif, .btn-sil {{ flex: 1; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📺 IPTV Panelim</h1>
            <p class="subtitle">M3U linkinizi webden yonetin, Android TV'den izleyin</p>

            <div class="durum">● {durum_yazi}</div>

            <div class="card">
                <h2>➕ Yeni Playlist Ekle</h2>
                <form method="post" action="/ekle">
                    <div class="form-row">
                        <div class="form-group">
                            <label>Playlist Adi</label>
                            <input type="text" name="isim" placeholder="Ornek: Ana Liste" required>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>M3U Linki</label>
                        <input type="text" name="url" placeholder="http://ornek.com/playlist.m3u" required>
                    </div>
                    <button type="submit" class="btn-ekle">💾 Playlist Ekle</button>
                </form>
            </div>

            <div class="card">
                <h2>📋 Kayitli Playlistler</h2>
                {playlist_html}
            </div>

            <div class="tv-box">
                <h3>📺 Android TV Linki</h3>
                <p>Asagidaki linki Televizo veya TiviMate'e M3U olarak ekleyin:</p>
                <div class="tv-link">https://iptv-panelim.onrender.com/get</div>
                <p>
                    1. Televizo'yu ac<br>
                    2. Playlist Ekle > M3U Link sec<br>
                    3. Yukaridaki linki gir ve kaydet<br>
                    4. Izlemeye basla!
                </p>
            </div>
        </div>
    </body>
    </html>
    """

# ==================== PLAYLIST EKLEME ====================
from fastapi import Form
from fastapi.responses import RedirectResponse

@app.post("/ekle")
def ekle(isim: str = Form(...), url: str = Form(...)):
    data = veri_oku()
    playlists = data.get("playlists", [])
    playlists.append({
        "isim": isim,
        "url": url,
        "tarih": datetime.now().strftime("%d.%m.%Y %H:%M")
    })
    aktif_url = data.get("m3u_url", "")
    if not aktif_url:
        aktif_url = url
    veri_kaydet({
        "playlists": playlists,
        "m3u_url": aktif_url
    })
    return RedirectResponse(url="/", status_code=303)

@app.post("/aktif/{index}")
def aktif_yap(index: int):
    data = veri_oku()
    playlists = data.get("playlists", [])
    if 0 <= index < len(playlists):
        data["m3u_url"] = playlists[index]["url"]
        veri_kaydet(data)
    return RedirectResponse(url="/", status_code=303)

@app.post("/sil/{index}")
def sil(index: int):
    data = veri_oku()
    playlists = data.get("playlists", [])
    if 0 <= index < len(playlists):
        silinen = playlists.pop(index)
        if data.get("m3u_url") == silinen["url"]:
            data["m3u_url"] = playlists[0]["url"] if playlists else ""
        data["playlists"] = playlists
        veri_kaydet(data)
    return RedirectResponse(url="/", status_code=303)
