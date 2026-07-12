from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
import os
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== AYARLAR ====================
# Render.com Environment Variables'dan okur
JSONBIN_ID  = os.environ.get("6a530100f5f4af5e2982c769", "")
JSONBIN_KEY = os.environ.get("$2a$10$mEKH6YEVi.0L4O2UFuU8LuP4e5MDauKOM/N09qQn.Wdfjb8NnOzhq", "")

# ==================== FONKSİYONLAR ====================
def veri_oku():
    try:
        url  = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}/latest"
        resp = requests.get(
            url,
            headers={
                "X-Master-Key": JSONBIN_KEY,
                "X-Bin-Meta":   "false"
            },
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            # Bazen jsonbin direkt veriyi, bazen record icinde dondurur
            if "record" in data:
                return data["record"]
            return data
    except Exception as e:
        print(f"OKUMA HATASI: {e}")
    return {"playlists": [], "m3u_url": ""}

def veri_kaydet(data):
    try:
        url  = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"
        resp = requests.put(
            url,
            headers={
                "X-Master-Key":  JSONBIN_KEY,
                "Content-Type":  "application/json"
            },
            json=data,
            timeout=10
        )
        print(f"KAYIT SONUCU: {resp.status_code} - {resp.text[:200]}")
        return resp.status_code == 200
    except Exception as e:
        print(f"KAYIT HATASI: {e}")
        return False

# ==================== TV ENDPOİNTİ ====================
@app.get("/get", response_class=PlainTextResponse)
def playlist_getir():
    data    = veri_oku()
    m3u_url = data.get("m3u_url", "")
    if not m3u_url:
        return "#EXTM3U\n#EXTINF:-1,Henuz playlist eklenmedi\nhttp://localhost"
    try:
        r = requests.get(
            m3u_url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        return r.text
    except Exception as e:
        return f"#EXTM3U\n#EXTINF:-1,Hata: {str(e)}\nhttp://localhost"

# ==================== API ====================
@app.get("/api/data")
def api_veri():
    return veri_oku()

@app.get("/api/debug")
def api_debug():
    """JSONBin baglantisini test eder"""
    sonuc = {
        "jsonbin_id":  JSONBIN_ID[:8] + "..." if JSONBIN_ID else "BOŞ",
        "jsonbin_key": JSONBIN_KEY[:8] + "..." if JSONBIN_KEY else "BOŞ",
    }
    try:
        url  = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}/latest"
        resp = requests.get(
            url,
            headers={
                "X-Master-Key": JSONBIN_KEY,
                "X-Bin-Meta":   "false"
            },
            timeout=10
        )
        sonuc["jsonbin_status"] = resp.status_code
        sonuc["jsonbin_yanit"]  = resp.text[:300]
    except Exception as e:
        sonuc["jsonbin_hata"] = str(e)
    return sonuc

@app.post("/api/ekle")
def api_ekle(body: dict):
    isim = body.get("isim", "").strip()
    url  = body.get("url",  "").strip()

    if not url.startswith("http"):
        return JSONResponse({"hata": "Gecersiz link"}, status_code=400)

    data      = veri_oku()
    playlists = data.get("playlists", [])

    playlists.append({
        "isim":  isim,
        "url":   url,
        "tarih": datetime.now().strftime("%d.%m.%Y %H:%M")
    })

    if not data.get("m3u_url"):
        data["m3u_url"] = url

    data["playlists"] = playlists
    basari = veri_kaydet(data)

    return {"durum": "ok" if basari else "hata"}

@app.post("/api/aktif/{index}")
def api_aktif(index: int):
    data      = veri_oku()
    playlists = data.get("playlists", [])
    if 0 <= index < len(playlists):
        data["m3u_url"] = playlists[index]["url"]
        veri_kaydet(data)
    return {"durum": "ok"}

@app.post("/api/sil/{index}")
def api_sil(index: int):
    data      = veri_oku()
    playlists = data.get("playlists", [])
    if 0 <= index < len(playlists):
        silinen = playlists.pop(index)
        if data.get("m3u_url") == silinen["url"]:
            data["m3u_url"] = playlists[0]["url"] if playlists else ""
        data["playlists"] = playlists
        veri_kaydet(data)
    return {"durum": "ok"}

# ==================== WEB PANELİ ====================
@app.get("/", response_class=HTMLResponse)
def panel():
    return """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IPTV Panelim</title>
        <style>
            * { margin:0; padding:0; box-sizing:border-box; }
            body {
                font-family: 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
                min-height: 100vh;
                color: #fff;
                padding: 20px;
            }
            .container { max-width: 700px; margin: 0 auto; }
            h1 {
                text-align: center;
                font-size: 2em;
                margin: 30px 0 10px;
                background: linear-gradient(90deg, #00d2ff, #3a7bd5);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .subtitle { text-align:center; color:#888; margin-bottom:30px; }
            .durum {
                text-align: center;
                padding: 12px;
                border-radius: 10px;
                margin-bottom: 25px;
                font-weight: bold;
                border: 1px solid;
                background: rgba(0,0,0,0.2);
            }
            .card {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 16px;
                padding: 25px;
                margin-bottom: 20px;
            }
            .card h2 { color:#00d2ff; margin-bottom:20px; font-size:1.2em; }
            .form-group { margin-bottom: 15px; }
            label { display:block; color:#aaa; font-size:0.85em; margin-bottom:6px; }
            input[type=text] {
                width: 100%;
                padding: 12px 15px;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 10px;
                background: rgba(255,255,255,0.08);
                color: #fff;
                font-size: 0.95em;
            }
            input[type=text]:focus { outline:none; border-color:#00d2ff; }
            .btn {
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
            }
            .btn:hover { opacity: 0.85; }
            .playlist-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 14px;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
                margin-bottom: 10px;
                background: rgba(255,255,255,0.03);
            }
            .playlist-info { display:flex; flex-direction:column; gap:4px; flex:1; }
            .playlist-info small { color:#666; font-size:0.8em; word-break:break-all; }
            .playlist-actions { display:flex; gap:8px; margin-left:10px; }
            .btn-aktif {
                padding: 8px 14px;
                border: 1px solid #00d2ff;
                border-radius: 8px;
                background: transparent;
                color: #00d2ff;
                cursor: pointer;
                font-size: 0.8em;
                white-space: nowrap;
            }
            .btn-sil {
                padding: 8px 14px;
                border: 1px solid #ff4757;
                border-radius: 8px;
                background: transparent;
                color: #ff4757;
                cursor: pointer;
                font-size: 0.8em;
            }
            .tv-box {
                background: rgba(0,210,255,0.08);
                border: 1px solid rgba(0,210,255,0.25);
                border-radius: 12px;
                padding: 20px;
                text-align: center;
                margin-top: 20px;
            }
            .tv-box h3 { color:#00d2ff; margin-bottom:12px; }
            .tv-link {
                background: rgba(0,0,0,0.3);
                border-radius: 8px;
                padding: 12px;
                font-family: monospace;
                font-size: 0.95em;
                color: #00d2ff;
                word-break: break-all;
                margin: 10px 0;
                cursor: pointer;
                border: 1px dashed rgba(0,210,255,0.3);
            }
            .tv-box p { color:#888; font-size:0.85em; line-height:1.8; }
            #mesaj {
                display: none;
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 15px;
                text-align: center;
                font-weight: bold;
            }
            .basari { background:rgba(0,255,136,0.1); border:1px solid #00ff88; color:#00ff88; }
            .hata   { background:rgba(255,71,87,0.1);  border:1px solid #ff4757; color:#ff4757; }
            .bos    { color:#555; text-align:center; padding:20px; }
            @media(max-width:600px) {
                .playlist-item    { flex-direction:column; gap:10px; }
                .playlist-actions { width:100%; margin-left:0; }
                .btn-aktif, .btn-sil { flex:1; text-align:center; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📺 IPTV Panelim</h1>
            <p class="subtitle">M3U linkinizi webden yonetin, Android TV'den izleyin</p>

            <div id="durum" class="durum">⏳ Yukleniyor...</div>

            <div class="card">
                <h2>➕ Yeni Playlist Ekle</h2>
                <div id="mesaj"></div>
                <div class="form-group">
                    <label>Playlist Adi</label>
                    <input type="text" id="isim" placeholder="Ornek: Ana Liste">
                </div>
                <div class="form-group">
                    <label>M3U Linki</label>
                    <input type="text" id="url" placeholder="http://ornek.com/playlist.m3u">
                </div>
                <button class="btn" onclick="ekle()">💾 Playlist Ekle</button>
            </div>

            <div class="card">
                <h2>📋 Kayitli Playlistler</h2>
                <div id="liste-container">
                    <p class="bos">⏳ Yukleniyor...</p>
                </div>
            </div>

            <div class="tv-box">
                <h3>📺 Android TV Linki</h3>
                <p>Asagidaki linki Televizo veya TiviMate'e M3U olarak ekleyin:</p>
                <div class="tv-link" id="tv-link" onclick="kopyala()">⏳ Yukleniyor...</div>
                <p>📋 Kopyalamak icin uzerine tiklayin</p>
                <br>
                <p>
                    1. Televizo'yu ac<br>
                    2. Playlist Ekle > M3U Link sec<br>
                    3. Yukaridaki linki gir ve kaydet<br>
                    4. Izlemeye basla!
                </p>
            </div>
        </div>

        <script>
            const BASE_URL = window.location.origin;
            document.getElementById('tv-link').textContent = BASE_URL + '/get';

            window.onload = verileriYukle;

            function verileriYukle() {
                fetch('/api/data')
                    .then(r => r.json())
                    .then(data => {
                        durumGuncelle(data.m3u_url);
                        listeGuncelle(data.playlists || [], data.m3u_url);
                    })
                    .catch(e => {
                        document.getElementById('durum').textContent = '❌ Baglanti hatasi: ' + e;
                    });
            }

            function durumGuncelle(aktifUrl) {
                const el = document.getElementById('durum');
                if (aktifUrl) {
                    el.style.color       = '#00ff88';
                    el.style.borderColor = '#00ff88';
                    el.textContent       = '● AKTIF PLAYLIST MEVCUT';
                } else {
                    el.style.color       = '#ff4757';
                    el.style.borderColor = '#ff4757';
                    el.textContent       = '● PLAYLIST EKLENMEDI';
                }
            }

            function listeGuncelle(playlists, aktifUrl) {
                const el = document.getElementById('liste-container');
                if (!playlists.length) {
                    el.innerHTML = '<p class="bos">Henuz playlist eklenmedi</p>';
                    return;
                }
                el.innerHTML = playlists.map((p, i) => `
                    <div class="playlist-item">
                        <div class="playlist-info">
                            <strong>${p.isim} ${p.url === aktifUrl ? '<span style="color:#00ff88;font-size:11px;">✅ AKTIF</span>' : ''}</strong>
                            <small>${p.url}</small>
                            <small>${p.tarih || ''}</small>
                        </div>
                        <div class="playlist-actions">
                            <button class="btn-aktif" onclick="aktifYap(${i})">Aktif</button>
                            <button class="btn-sil"   onclick="sil(${i})">🗑️</button>
                        </div>
                    </div>
                `).join('');
            }

            function mesajGoster(metin, tip) {
                const el    = document.getElementById('mesaj');
                el.textContent = metin;
                el.className   = tip;
                el.style.display = 'block';
                setTimeout(() => el.style.display = 'none', 3000);
            }

            function ekle() {
                const isim = document.getElementById('isim').value.trim();
                const url  = document.getElementById('url').value.trim();
                if (!isim) {
                    mesajGoster('❌ Playlist adi bos olamaz', 'hata');
                    return;
                }
                if (!url.startsWith('http')) {
                    mesajGoster('❌ Gecerli bir link girin', 'hata');
                    return;
                }
                fetch('/api/ekle', {
                    method:  'POST',
                    headers: {'Content-Type': 'application/json'},
                    body:    JSON.stringify({isim, url})
                })
                .then(r => r.json())
                .then(d => {
                    if (d.durum === 'ok') {
                        mesajGoster('✅ Playlist basariyla eklendi!', 'basari');
                        document.getElementById('isim').value = '';
                        document.getElementById('url').value  = '';
                        setTimeout(verileriYukle, 1000);
                    } else {
                        mesajGoster('❌ Eklenemedi, tekrar deneyin', 'hata');
                    }
                })
                .catch(e => mesajGoster('❌ Hata: ' + e, 'hata'));
            }

            function aktifYap(index) {
                fetch(`/api/aktif/${index}`, {method: 'POST'})
                    .then(() => setTimeout(verileriYukle, 1000));
            }

            function sil(index) {
                if (confirm('Bu playlist silinsin mi?')) {
                    fetch(`/api/sil/${index}`, {method: 'POST'})
                        .then(() => setTimeout(verileriYukle, 1000));
                }
            }

            function kopyala() {
                const link = document.getElementById('tv-link').textContent;
                navigator.clipboard.writeText(link)
                    .then(() => alert('✅ Kopyalandi:\n' + link))
                    .catch(() => prompt('Linki kopyalayin:', link));
            }
        </script>
    </body>
    </html>
    """
