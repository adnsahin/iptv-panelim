import streamlit as st
import requests
import json
from datetime import datetime

# ==================== SAYFA AYARLARI ====================
st.set_page_config(page_title="IPTV Panelim", page_icon="📺", layout="centered")

# ==================== GITHUB GIST AYARLARI ====================
# Asagidaki iki satira kendi bilgilerini yaz
GIST_ID = "0711dfba4936dc2c74e360d4255b14c9"
GITHUB_TOKEN = "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"

# ==================== STIL ====================
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    }
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0);
    }
    .block-container {
        padding-top: 2rem;
    }
    h1 {
        background: linear-gradient(90deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stTextArea textarea {
        background-color: rgba(255,255,255,0.05) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        border-radius: 10px !important;
    }
    .stButton > button {
        width: 100%;
        height: 55px;
        font-size: 18px;
        font-weight: bold;
        border-radius: 12px;
        background: linear-gradient(90deg, #00d2ff, #3a7bd5);
        color: white;
        border: none;
    }
    .stButton > button:hover {
        opacity: 0.85;
    }
    div[data-testid="stCode"] {
        background-color: rgba(0, 210, 255, 0.08) !important;
        border: 1px solid rgba(0, 210, 255, 0.25) !important;
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================== TV ENDPOINT ====================
query = st.query_params
if query.get("page") == "get":
    try:
        url = f"https://api.github.com/gists/{GIST_ID}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            content = resp.json()["files"]["playlist.json"]["content"]
            data = json.loads(content)
            m3u_url = data.get("m3u_url", "")
            if m3u_url:
                r = requests.get(m3u_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                st.markdown(f"```\n{r.text}\n```")
            else:
                st.text("#EXTM3U\n#EXTINF:-1,Henuz playlist eklenmedi\nhttp://localhost")
        else:
            st.text("#EXTM3U\n#EXTINF:-1,Gist okunamadi\nhttp://localhost")
    except Exception as e:
        st.text(f"#EXTM3U\n#EXTINF:-1,Hata: {str(e)}\nhttp://localhost")
    st.stop()

# ==================== GIST FONKSIYONLARI ====================
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
    return {"playlists": [], "aktif_index": 0}

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

# ==================== ANA SAYFA ====================
st.title("📺 IPTV Panelim")
st.caption("M3U linkinizi buradan yonetin — Android TV'den aninda izleyin")

data = veri_oku()
playlists = data.get("playlists", [])
aktif_index = data.get("aktif_index", 0)
aktif_url = data.get("m3u_url", "")

# Durum Gostergesi
if aktif_url:
    st.success("✅ Aktif playlist mevcut — TV izlemeye hazir")
else:
    st.warning("⚠️ Henuz playlist eklenmedi")

st.divider()

# ==================== PLAYLIST EKLEME ====================
st.subheader("➕ Yeni Playlist Ekle")

col1, col2 = st.columns([1, 2])
with col1:
    isim = st.text_input("Playlist Adi", placeholder="Ornek: Ana Liste")
with col2:
    url_input = st.text_input("M3U Linki", placeholder="http://ornek.com/playlist.m3u")

if st.button("💾 Playlist Ekle", type="primary"):
    if url_input.strip().startswith("http") and isim.strip():
        playlists.append({
            "isim": isim.strip(),
            "url": url_input.strip(),
            "tarih": datetime.now().strftime("%d.%m.%Y %H:%M")
        })
        yeni_data = {
            "playlists": playlists,
            "aktif_index": len(playlists) - 1,
            "m3u_url": url_input.strip()
        }
        veri_kaydet(yeni_data)
        st.success("✅ Playlist basariyla eklendi!")
        st.balloons()
        st.rerun()
    else:
        st.error("❌ Lutfen gecerli bir isim ve link girin")

st.divider()

# ==================== KAYITLI PLAYLISTLER ====================
st.subheader("📋 Kayitli Playlistler")

if playlists:
    for i, p in enumerate(playlists):
        with st.container():
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                durum = " ✅" if p["url"] == aktif_url else ""
                st.markdown(f"**{p['isim']}{durum}**")
                st.caption(f"{p['url'][:50]}... | {p.get('tarih', '')}")
            with c2:
                if st.button("Aktif Yap", key=f"aktif_{i}"):
                    data["aktif_index"] = i
                    data["m3u_url"] = p["url"]
                    data["playlists"] = playlists
                    veri_kaydet(data)
                    st.rerun()
            with c3:
                if st.button("🗑️ Sil", key=f"sil_{i}"):
                    playlists.pop(i)
                    new_url = playlists[0]["url"] if playlists else ""
                    veri_kaydet({
                        "playlists": playlists,
                        "aktif_index": 0,
                        "m3u_url": new_url
                    })
                    st.rerun()
else:
    st.info("Henuz playlist eklenmedi. Yukaridan ekleyebilirsiniz.")

st.divider()

# ==================== TV BILGI ====================
st.subheader("📺 Android TV Ayarlari")

# Streamlit URL'sini otomatik al
try:
    import streamlit.web.bootstrap as bootstrap
    app_url = "https://iptv-panelim.streamlit.app"
except:
    app_url = "https://iptv-panelim.streamlit.app"

tv_link = f"{app_url}/?page=get"

st.markdown("Asagidaki linki TV'deki IPTV uygulamaniza ekleyin:")
st.code(tv_link, language="text")

st.markdown("""
**Kurulum:**
1. Android TV'de **Televizo** veya **TiviMate** acin
2. **Playlist Ekle** > **M3U Link** secin
3. Yukaridaki linki yapisitirin
4. Kaydet ve izlemeye baslayin!

**Not:** Playlist'i degistirdiginizde TV'de
uygulamayi yeniden acmaniz yeterlidir.
""")

st.divider()
st.caption("📺 IPTV Panelim | Tamamen Ucretsiz | Bulut Tabanli")
