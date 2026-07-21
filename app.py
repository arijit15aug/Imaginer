import streamlit as st
import requests
import os
from dotenv import load_dotenv
import base64
import tempfile
import io
from streamlit_image_comparison import image_comparison
import replicate
from PIL import Image
import time
import zipfile

# ═══════ AUTO-WRITE CONFIG ═══════ #
import pathlib
config_dir = pathlib.Path(".streamlit")
config_dir.mkdir(exist_ok=True)
(config_dir / "config.toml").write_text("""
[theme]
base = "dark"
backgroundColor = "#071a14"
secondaryBackgroundColor = "#0a2a1e"
textColor = "#e8f8f4"
primaryColor = "#00d4a8"
""")

# ═══════ PAGE CONFIG ═══════ #
st.set_page_config(
    page_title="Imaginer Studio",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════ EARLY BG INJECT ═══════ #
st.markdown("""
<style>
html, body { background: #071a14 !important; min-height: 100vh !important; }
[data-testid="stAppViewContainer"] { background: transparent !important; }
[data-testid="stApp"],[data-testid="stMain"],[data-testid="stMainBlockContainer"],
[data-testid="stAppViewBlockContainer"],[data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"],section.main { background: transparent !important; }
</style>
""", unsafe_allow_html=True)

# ═══════ LOAD ENV ═══════ #
load_dotenv()
STABILITY_API_KEY   = os.getenv("STABILITY_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

# ═══════ SESSION STATE ═══════ #
DEFAULTS = {
    "history": [], "generated_count": 0, "enhanced_count": 0,
    "video_count": 0, "selected_menu": "Dashboard", "last_generated": None,
    "enhance_original": None, "enhance_result": None,
    "enhance_scale": 4, "enhance_result_bytes": None,
    "txt2vid_result": None, "txt2vid_prompt": "",
    "img2vid_result": None, "img2vid_original": None,
    "api_status_checked": False, "stability_ok": False, "replicate_ok": False,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ═══════ MASTER CSS ═══════ #
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Outfit:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── DESIGN TOKENS ── */
:root {
  --bg-dark:    #071a14;
  --teal-dark:  #0a4a35;
  --teal-mid:   #0f8c6a;
  --teal-bright:#00d4a8;
  --teal-pale:  #7eecd8;
  --peach:      #f0a882;
  --peach-warm: #f5c4a8;
  --peach-pale: #fde8d8;

  /* FIXED: Gradient mesh with better readability zones */
  --mesh: radial-gradient(ellipse 80% 70% at 0% 30%,   #062e20 0%, transparent 60%),
          radial-gradient(ellipse 70% 80% at 40% 0%,    #0a5c42 0%, transparent 55%),
          radial-gradient(ellipse 90% 60% at 55% 20%,   #00c49a 0%, transparent 50%),
          radial-gradient(ellipse 60% 70% at 100% 0%,   #c8906a 0%, transparent 55%),
          radial-gradient(ellipse 50% 60% at 100% 60%,  #c88060 0%, transparent 50%),
          radial-gradient(ellipse 40% 40% at 75% 100%,  #a06848 0%, transparent 55%),
          radial-gradient(ellipse 60% 50% at 20% 100%,  #062e20 0%, transparent 60%),
          linear-gradient(145deg, #062e20 0%, #0a4a35 20%, #00b88c 40%, #00d4a8 52%, #b8906a 70%, #c8a080 85%, #be9878 100%);

  /* Glass surfaces */
  --glass:   rgba(4, 28, 18, 0.60);
  --glass-h: rgba(4, 28, 18, 0.75);

  /* FIXED: Improved card colors for readability */
  /* Dark teal cards — light text */
  --ct-bg:  rgba(4, 30, 20, 0.72);
  --ct-bdr: rgba(0, 180, 140, 0.30);
  --ct-val: #7eecd8;
  --ct-lbl: rgba(200, 245, 235, 0.90);   /* FIXED: was too dim */
  --ct-tag: rgba(180, 235, 220, 0.65);

  /* Peach cards — FIXED: dark overlay so text is readable */
  --cp-bg:  rgba(30, 14, 6, 0.68);
  --cp-bdr: rgba(200, 120, 70, 0.35);
  --cp-val: #f5c4a8;
  --cp-lbl: rgba(255, 220, 195, 0.92);   /* FIXED: was illegible */
  --cp-tag: rgba(240, 190, 160, 0.70);

  /* Typography */
  --txt:  rgba(255,255,255,0.96);
  --txt2: rgba(255,255,255,0.75);
  --txt3: rgba(255,255,255,0.50);
  --txt4: rgba(255,255,255,0.28);
  --font-d: 'Syne', sans-serif;
  --font-b: 'Outfit', sans-serif;
  --font-m: 'JetBrains Mono', monospace;

  --r: 18px; --rm: 14px; --rs: 10px; --rpill: 999px;
  --ease: cubic-bezier(0.22,1,0.36,1);
  --t: all 0.28s var(--ease);
}

*, *::before, *::after { box-sizing: border-box; }

/* ── GLOBAL BACKGROUND ── */
.stApp,[data-testid="stApp"],[data-testid="stMain"],[data-testid="stMainBlockContainer"],
[data-testid="stAppViewBlockContainer"],[data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"],section.main,.main .block-container {
  background: transparent !important;
  font-family: var(--font-b) !important;
}
[data-testid="stAppViewContainer"] {
  background: var(--mesh) !important;
  background-attachment: fixed !important;
  min-height: 100vh !important;
}
[data-testid="stAppViewContainer"]::after {
  content: '';
  position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
  background-size: 160px 160px; opacity: 0.6;
}

header[data-testid="stHeader"] { display: none !important; }

.block-container {
  padding: 2.5rem 3rem 3.5rem !important;
  max-width: 1460px !important;
}

/* ── SIDEBAR ── */
section[data-testid="stSidebar"] {
  background: rgba(3, 16, 10, 0.92) !important;
  backdrop-filter: blur(36px) saturate(1.3) !important;
  -webkit-backdrop-filter: blur(36px) saturate(1.3) !important;
  border-right: 1px solid rgba(0,212,168,0.12) !important;
  width: 268px !important;
  box-shadow: 4px 0 48px rgba(0,0,0,0.6) !important;
}
section[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }
section[data-testid="stSidebar"] .block-container   { padding: 0 !important; }

/* ── SIDEBAR BRAND ── */
.sb-brand {
  padding: 26px 20px 20px;
  border-bottom: 1px solid rgba(0,212,168,0.10);
  background: rgba(0,212,168,0.04);
}
.sb-logo-wrap { display: flex; align-items: center; gap: 13px; margin-bottom: 8px; }
.sb-logo-icon {
  width: 44px; height: 44px;
  background: linear-gradient(135deg, #00b88c, #00d4a8 55%, #f0a882);
  border-radius: 13px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  box-shadow: 0 2px 18px rgba(0,212,168,0.32), 0 0 0 1px rgba(255,255,255,0.08);
  flex-shrink: 0;
}
.sb-title {
  font-family: var(--font-d);
  font-size: 21px; font-weight: 800; letter-spacing: 2px; text-transform: uppercase;
  color: var(--txt);
}
.sb-sub {
  font-size: 8px; letter-spacing: 4px; text-transform: uppercase; font-weight: 500;
  font-family: var(--font-m);
  background: linear-gradient(90deg, #00d4a8, #f0a882);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text; margin-top: 2px;
}
.sb-tagline { font-size: 12px; color: var(--txt3); margin-top: 8px; line-height: 1.6; }

/* ── SIDEBAR NAV ── */
.sb-nav-section { padding: 8px 12px 0; }
.sb-nav-label {
  font-size: 9px; font-weight: 600; letter-spacing: 3px; text-transform: uppercase;
  color: var(--txt4); padding: 16px 8px 6px; font-family: var(--font-m);
}
.sb-nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; border-radius: var(--rs);
  cursor: pointer; transition: var(--t);
  margin-bottom: 2px; border: 1px solid transparent; position: relative;
}
.sb-nav-item:hover { background: rgba(0,212,168,0.08); border-color: rgba(0,212,168,0.18); }
.sb-nav-item.active {
  background: rgba(0,212,168,0.12);
  border-color: rgba(0,212,168,0.28);
}
.sb-nav-item.active::before {
  content: ''; position: absolute; left: 0; top: 18%; bottom: 18%;
  width: 2.5px;
  background: linear-gradient(180deg, #00d4a8, #f0a882);
  border-radius: 0 2px 2px 0;
  box-shadow: 0 0 8px rgba(0,212,168,0.5);
}
.sb-nav-icon { font-size: 15px; width: 20px; text-align: center; flex-shrink: 0; }
.sb-nav-text { font-size: 13px; font-weight: 500; color: var(--txt3); font-family: var(--font-b); }
.sb-nav-item.active .sb-nav-text { color: #7eecd8; font-weight: 600; }
.sb-nav-badge {
  margin-left: auto;
  background: rgba(0,212,168,0.16); color: #7eecd8;
  font-size: 10px; font-weight: 700; padding: 1px 8px;
  border-radius: var(--rpill); font-family: var(--font-m);
  border: 1px solid rgba(0,212,168,0.24);
}
/* IMPROVED: More distinct NEW badge */
.sb-nav-new {
  margin-left: auto;
  background: linear-gradient(135deg, rgba(240,168,130,0.25), rgba(240,100,80,0.20));
  color: #f5c4a8;
  font-size: 9px; font-weight: 700; padding: 2px 8px;
  border-radius: var(--rpill); font-family: var(--font-m);
  border: 1px solid rgba(240,168,130,0.40);
  letter-spacing: 1px; text-transform: uppercase;
  box-shadow: 0 0 8px rgba(240,168,130,0.15);
}

/* ── SIDEBAR STATUS INDICATORS ── */
.api-status-row {
  display: flex; align-items: center; gap: 8px;
  padding: 5px 0;
}
.status-dot {
  width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
}
.status-dot.ok  { background: #00d4a8; box-shadow: 0 0 6px rgba(0,212,168,0.6); }
.status-dot.err { background: #f06060; box-shadow: 0 0 6px rgba(240,96,96,0.6); }
.status-dot.unk { background: rgba(255,255,255,0.22); }
.status-label { font-size: 11.5px; color: var(--txt3); font-family: var(--font-b); }
.status-val   { margin-left: auto; font-size: 10px; font-family: var(--font-m); }
.status-val.ok  { color: #7eecd8; }
.status-val.err { color: #f09090; }
.status-val.unk { color: var(--txt4); }

/* ── SIDEBAR STATS ── */
.sb-stats {
  margin: 14px 12px;
  background: rgba(0,180,140,0.07);
  border: 1px solid rgba(0,212,168,0.12);
  border-radius: var(--rm); padding: 16px; position: relative; overflow: hidden;
}
.sb-stats::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0,212,168,0.55) 45%, rgba(240,168,130,0.45) 75%, transparent);
}
.sb-stats-title {
  font-size: 9px; font-weight: 600; color: var(--txt4);
  letter-spacing: 3px; text-transform: uppercase;
  font-family: var(--font-m); margin-bottom: 12px;
}
.sb-stat-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 5px 0; border-bottom: 1px solid rgba(255,255,255,0.05);
}
.sb-stat-row:last-child { border-bottom: none; }
.sb-stat-label { font-size: 12px; color: var(--txt3); }
.sb-stat-val {
  font-family: var(--font-m); font-size: 13px; font-weight: 600;
  background: linear-gradient(135deg, #00d4a8, #f0a882);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}

/* ── SIDEBAR FOOTER ── */
.sb-footer { padding: 14px 12px; border-top: 1px solid rgba(0,212,168,0.10); }
.sb-footer-text { font-size: 10.5px; color: var(--txt4); text-align: center; line-height: 1.7; }
.sb-version-pill {
  display: inline-block;
  background: rgba(0,212,168,0.10); border: 1px solid rgba(0,212,168,0.24);
  color: #7eecd8; font-size: 9px; font-weight: 700;
  letter-spacing: 2.5px; padding: 2px 10px;
  border-radius: var(--rpill); font-family: var(--font-m);
  text-transform: uppercase; margin-bottom: 6px;
}

/* ── HIDE RAW SIDEBAR BUTTONS ── */
section[data-testid="stSidebar"] .stButton > button {
  opacity: 0 !important; height: 0 !important; padding: 0 !important;
  margin: 0 !important; border: none !important; pointer-events: auto !important;
  position: absolute;
}

/* ── PAGE HEADERS ── */
.page-header { margin-bottom: 40px; }
.page-eyebrow {
  font-family: var(--font-m); font-size: 10px; font-weight: 700;
  letter-spacing: 4px; text-transform: uppercase;
  margin-bottom: 14px; display: inline-flex; align-items: center; gap: 9px;
  background: linear-gradient(90deg, #00d4a8 0%, #7eecd8 45%, #f0a882 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.page-eyebrow::before {
  content: ''; width: 16px; height: 1.5px; flex-shrink: 0; display: inline-block;
  background: linear-gradient(90deg, #00d4a8, #f0a882);
  box-shadow: 0 0 8px rgba(0,212,168,0.55);
}
.page-title {
  font-family: var(--font-d); font-size: 46px; font-weight: 800;
  color: var(--txt); line-height: 1.05; margin: 0 0 14px;
  letter-spacing: -1.5px;
  filter: drop-shadow(0 4px 28px rgba(0,212,168,0.12));
}
.page-title .hl-teal {
  background: linear-gradient(125deg, #00d4a8 0%, #7eecd8 30%, #00b88c 55%, #7eecd8 80%, #00d4a8 100%);
  background-size: 250% auto;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  animation: titleShimmer 8s ease-in-out infinite;
}
.page-title .hl-peach {
  background: linear-gradient(125deg, #f0a882 0%, #fcc8a8 30%, #e08060 55%, #fcc8a8 80%, #f0a882 100%);
  background-size: 250% auto;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  animation: titleShimmer 8s ease-in-out infinite;
}
@keyframes titleShimmer {
  0%, 100% { background-position: 0% 50%; }
  50%       { background-position: 100% 50%; }
}
.page-subtitle { font-size: 15px; color: var(--txt2); line-height: 1.65; max-width: 520px; font-weight: 300; }

/* ── BACK BUTTON ── */
.back-btn-wrap { margin-bottom: 28px; }
.back-btn-wrap div.stButton > button {
  background: rgba(0,180,140,0.08) !important;
  border: 1px solid rgba(0,212,168,0.20) !important;
  color: #7eecd8 !important;
  font-size: 12px !important; font-weight: 500 !important;
  padding: 7px 18px !important; border-radius: var(--rpill) !important;
  backdrop-filter: blur(8px) !important; width: auto !important;
  transition: var(--t) !important; opacity: 1 !important;
  height: auto !important; position: relative !important;
}
.back-btn-wrap div.stButton > button:hover {
  background: rgba(0,180,140,0.18) !important;
  transform: translateX(-4px) !important;
}

/* ═══════════════════════════════════════════
   METRIC CARDS — FIXED CONTRAST
═══════════════════════════════════════════ */
.metric-card {
  border-radius: var(--r); padding: 24px 20px;
  backdrop-filter: blur(28px) saturate(1.4);
  -webkit-backdrop-filter: blur(28px) saturate(1.4);
  position: relative; overflow: hidden;
  transition: var(--t); cursor: default;
}
.metric-card:hover { transform: translateY(-6px); }
.metric-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1.5px;
}

/* Teal cards — dark bg, light text */
.mc1 {
  background: rgba(4, 28, 18, 0.78);
  border: 1px solid rgba(0, 180, 140, 0.32);
}
.mc1::before { background: linear-gradient(90deg, #00b88c, #7eecd8); }
.mc1 .metric-val   { color: #7eecd8; }
.mc1 .metric-label { color: rgba(200, 245, 235, 0.90); }
.mc1 .metric-tag   { color: rgba(160, 225, 210, 0.70); }

.mc2 {
  background: rgba(4, 32, 22, 0.75);
  border: 1px solid rgba(0, 196, 154, 0.30);
}
.mc2::before { background: linear-gradient(90deg, #00c49a, #a0f0e0); }
.mc2 .metric-val   { color: #a0f0e0; }
.mc2 .metric-label { color: rgba(200, 245, 235, 0.90); }
.mc2 .metric-tag   { color: rgba(160, 225, 210, 0.70); }

.mc3 {
  background: rgba(0, 40, 28, 0.72);
  border: 1px solid rgba(0, 212, 168, 0.30);
}
.mc3::before { background: linear-gradient(90deg, #00d4a8, #22e5c4); }
.mc3 .metric-val   { color: #22e5c4; }
.mc3 .metric-label { color: rgba(200, 250, 240, 0.92); }
.mc3 .metric-tag   { color: rgba(160, 230, 215, 0.72); }

/* FIXED Peach cards — dark overlay ensures legibility */
.mc4 {
  background: rgba(24, 10, 4, 0.78);
  border: 1px solid rgba(200, 120, 70, 0.35);
}
.mc4::before { background: linear-gradient(90deg, #c88060, #f0a882); }
.mc4 .metric-val   { color: #f5c4a8; }
.mc4 .metric-label { color: rgba(255, 215, 185, 0.92); }  /* FIXED */
.mc4 .metric-tag   { color: rgba(240, 185, 150, 0.72); }

.mc5 {
  background: rgba(28, 12, 4, 0.78);
  border: 1px solid rgba(220, 140, 90, 0.32);
}
.mc5::before { background: linear-gradient(90deg, #d08060, #f5c4a8); }
.mc5 .metric-val   { color: #fde0c8; }
.mc5 .metric-label { color: rgba(255, 220, 192, 0.92); }  /* FIXED */
.mc5 .metric-tag   { color: rgba(245, 195, 162, 0.70); }

.metric-tag {
  font-family: var(--font-m); font-size: 9px; font-weight: 600;
  letter-spacing: 3.5px; text-transform: uppercase; margin-bottom: 14px;
}
.metric-val {
  font-family: var(--font-d); font-size: 52px; font-weight: 800; line-height: 1;
  margin-bottom: 6px;
}
.metric-label { font-size: 12.5px; font-weight: 400; }
.metric-icon { position: absolute; top: 18px; right: 16px; font-size: 22px; opacity: 0.10; }

/* ── METRIC CARD → PAGE NAV LINK (tap "Start creating"/"View" to jump) ── */
.metric-cta-wrap { margin-top: -6px; margin-bottom: 4px; }
.metric-cta-wrap div.stButton > button {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 6px 2px 2px !important;
  margin: 0 !important;
  height: auto !important;
  min-height: 0 !important;
  color: rgba(160, 225, 210, 0.60) !important;
  font-family: var(--font-m) !important;
  font-size: 11.5px !important;
  font-weight: 600 !important;
  letter-spacing: 0.2px !important;
  text-align: left !important;
  justify-content: flex-start !important;
  backdrop-filter: none !important;
  transform: none !important;
  width: 100% !important;
}
.metric-cta-wrap div.stButton > button:hover {
  color: #7eecd8 !important;
  background: transparent !important;
  transform: translateX(4px) !important;
  box-shadow: none !important;
}
.metric-cta-wrap div.stButton > button p { text-align: left !important; }

/* ── SECTION HEADERS ── */
.section-header { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
.section-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: linear-gradient(135deg, #00d4a8, #f0a882);
  box-shadow: 0 0 8px rgba(0,212,168,0.5); flex-shrink: 0;
}
.section-dot-peach {
  width: 6px; height: 6px; border-radius: 50%;
  background: linear-gradient(135deg, #f0a882, #7eecd8);
  box-shadow: 0 0 8px rgba(240,168,130,0.5); flex-shrink: 0;
}
.section-title {
  font-family: var(--font-d); font-size: 16px; font-weight: 700;
  color: var(--txt); letter-spacing: -0.2px;
}
.section-line {
  flex: 1; height: 1px;
  background: linear-gradient(90deg, rgba(0,212,168,0.25), rgba(240,168,130,0.15), transparent);
}

/* ═══════════════════════════════════════════
   ACTION CARDS — FIXED CONTRAST + POLISH
═══════════════════════════════════════════ */
.action-card {
  border-radius: var(--r); padding: 26px 18px; text-align: center;
  cursor: pointer; transition: var(--t); position: relative; overflow: hidden;
  backdrop-filter: blur(22px) saturate(1.3);
  -webkit-backdrop-filter: blur(22px) saturate(1.3);
  height: 100%;
}
.action-card:hover { transform: translateY(-8px) scale(1.01); }

.ac1 {
  background: rgba(4, 26, 16, 0.80);
  border: 1px solid rgba(0, 180, 140, 0.30);
  box-shadow: 0 8px 32px rgba(0,0,0,0.35), inset 0 1px 0 rgba(0,212,168,0.12);
}
.ac1:hover { border-color: rgba(0,212,168,0.55); box-shadow: 0 16px 48px rgba(0,0,0,0.40), 0 0 24px rgba(0,212,168,0.12); }
.ac1 .action-title { color: #7eecd8; }
.ac1 .action-desc  { color: rgba(180, 235, 220, 0.72); }  /* FIXED */

.ac2 {
  background: rgba(0, 32, 22, 0.78);
  border: 1px solid rgba(0, 212, 168, 0.35);
  box-shadow: 0 8px 32px rgba(0,0,0,0.30), inset 0 1px 0 rgba(0,212,168,0.18);
}
.ac2:hover { border-color: rgba(0,212,168,0.60); }
.ac2 .action-title { color: #22e5c4; }
.ac2 .action-desc  { color: rgba(160, 240, 225, 0.72); }  /* FIXED */

.ac3 {
  background: rgba(4, 22, 14, 0.80);
  border: 1px solid rgba(100, 180, 150, 0.28);
  box-shadow: 0 8px 32px rgba(0,0,0,0.32);
}
.ac3:hover { border-color: rgba(150, 210, 185, 0.50); }
.ac3 .action-title { color: #a8e8d8; }
.ac3 .action-desc  { color: rgba(168, 232, 216, 0.70); }  /* FIXED */

.ac4 {
  background: rgba(22, 8, 2, 0.80);
  border: 1px solid rgba(200, 120, 70, 0.32);
  box-shadow: 0 8px 32px rgba(0,0,0,0.32);
}
.ac4:hover { border-color: rgba(240,168,130,0.55); }
.ac4 .action-title { color: #f5c4a8; }
.ac4 .action-desc  { color: rgba(245, 195, 168, 0.72); }  /* FIXED */

.ac5 {
  background: rgba(26, 10, 2, 0.80);
  border: 1px solid rgba(220, 150, 95, 0.28);
  box-shadow: 0 8px 32px rgba(0,0,0,0.30);
}
.ac5:hover { border-color: rgba(245,196,168,0.52); }
.ac5 .action-title { color: #fde0c0; }
.ac5 .action-desc  { color: rgba(252, 220, 190, 0.72); }  /* FIXED */

.action-icon { font-size: 32px; margin-bottom: 12px; display: block; }
.action-title {
  font-family: var(--font-d); font-size: 14px; font-weight: 700;
  margin-bottom: 7px; letter-spacing: -0.1px;
}
.action-desc { font-size: 12px; line-height: 1.6; font-weight: 300; }

/* IMPROVED: Proper badge component */
.ac-badge-new {
  display: inline-flex; align-items: center; gap: 4px;
  margin-top: 10px;
  background: linear-gradient(135deg, rgba(240,140,100,0.22), rgba(240,100,70,0.18));
  border: 1px solid rgba(240,168,130,0.45);
  color: #f5c4a8; font-size: 9px; font-weight: 700;
  padding: 3px 10px; border-radius: var(--rpill);
  font-family: var(--font-m); letter-spacing: 1.5px; text-transform: uppercase;
  box-shadow: 0 2px 10px rgba(240,130,90,0.18);
}

/* ── OPEN BUTTON (inside action cards) ── */
.open-btn-wrap { margin-top: 14px; }

/* ── GLASS CARDS ── */
.glass-card {
  background: rgba(4, 24, 15, 0.65);
  border: 1px solid rgba(0, 212, 168, 0.14);
  border-radius: var(--r); padding: 24px;
  backdrop-filter: blur(28px) saturate(1.3);
  -webkit-backdrop-filter: blur(28px) saturate(1.3);
  position: relative; overflow: hidden; transition: var(--t);
}
.glass-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0,212,168,0.50) 35%, rgba(240,168,130,0.38) 70%, transparent);
}
.glass-card:hover { border-color: rgba(0,212,168,0.24); transform: translateY(-3px); }

.glass-card-peach {
  background: rgba(20, 7, 2, 0.65);
  border: 1px solid rgba(200, 110, 60, 0.22);
  border-radius: var(--r); padding: 24px;
  backdrop-filter: blur(28px) saturate(1.3);
  -webkit-backdrop-filter: blur(28px) saturate(1.3);
  position: relative; overflow: hidden; transition: var(--t);
}
.glass-card-peach::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(240,168,130,0.55) 40%, rgba(0,212,168,0.30) 70%, transparent);
}
.glass-card-peach:hover { border-color: rgba(200,110,60,0.38); transform: translateY(-3px); }

/* ── IMAGE FRAME ── */
.img-frame {
  background: rgba(2, 18, 10, 0.60); border: 1px solid rgba(255,255,255,0.10);
  border-radius: var(--rm); padding: 8px; position: relative; overflow: hidden;
  box-shadow: 0 4px 24px rgba(0,0,0,0.40);
}
.img-frame::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1.5px;
  background: linear-gradient(90deg, #00d4a8, #7eecd8 55%, #f0a882); opacity: 0.7;
}

/* IMPROVED: Empty state placeholders */
.img-placeholder {
  background: rgba(0,180,140,0.04); border: 1.5px dashed rgba(0,212,168,0.22);
  border-radius: var(--rs); padding: 52px 30px; text-align: center;
}
.img-placeholder-icon { font-size: 42px; opacity: 0.14; display: block; margin-bottom: 14px; }
.img-placeholder-text { color: rgba(200,240,230,0.55); font-size: 13.5px; line-height: 1.65; }  /* FIXED */
.img-placeholder-hint {
  margin-top: 10px; font-size: 11.5px; color: rgba(160,220,205,0.40);
  font-family: var(--font-m);
}

.video-placeholder {
  background: rgba(30,10,2,0.35); border: 1.5px dashed rgba(200,100,60,0.25);
  border-radius: var(--rs); padding: 52px 30px; text-align: center;
}
.video-placeholder-icon { font-size: 42px; opacity: 0.14; display: block; margin-bottom: 14px; }
.video-placeholder-text { color: rgba(245,200,170,0.60); font-size: 13.5px; line-height: 1.65; }  /* FIXED */

/* ── GALLERY CARDS ── */
.gallery-card {
  background: rgba(4,24,15,0.65); border: 1px solid rgba(255,255,255,0.10);
  border-radius: var(--rm); overflow: hidden;
  backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
  transition: var(--t);
}
.gallery-card:hover { border-color: rgba(0,212,168,0.30); transform: translateY(-5px); }
.gallery-footer {
  padding: 10px 13px; border-top: 1px solid rgba(255,255,255,0.06);
  display: flex; align-items: center; justify-content: space-between;
  background: rgba(0,212,168,0.04);
}
.gallery-num { font-family: var(--font-m); font-size: 11px; color: var(--txt4); }

/* ── VIDEO HISTORY CARD ── */
.video-history-card {
  background: rgba(20,6,2,0.65); border: 1px solid rgba(200,100,60,0.18);
  border-radius: var(--rm); overflow: hidden;
  backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
  transition: var(--t); padding: 12px;
}
.video-history-card:hover { border-color: rgba(200,100,60,0.35); transform: translateY(-5px); }

/* IMPROVED: Proper badge component */
.video-type-badge {
  display: inline-flex; align-items: center;
  margin-bottom: 10px;
  background: rgba(200,100,60,0.18); border: 1px solid rgba(200,100,60,0.38);
  color: #f5c4a8; font-size: 9px; font-weight: 700;
  padding: 3px 10px; border-radius: var(--rpill);
  font-family: var(--font-m); letter-spacing: 1.5px; text-transform: uppercase;
}

/* ── INFO BOXES ── */
.preset-info {
  background: rgba(0,180,140,0.08); border: 1px solid rgba(0,212,168,0.20);
  border-left: 2.5px solid #00d4a8; border-radius: 0 var(--rs) var(--rs) 0;
  padding: 10px 13px; margin-top: 10px;
  font-size: 12px; color: #7eecd8; line-height: 1.6; font-family: var(--font-m);
}
.preset-info strong { color: var(--txt); font-weight: 600; }
.preset-info-peach {
  background: rgba(180,90,40,0.10); border: 1px solid rgba(200,110,60,0.24);
  border-left: 2.5px solid #f0a882; border-radius: 0 var(--rs) var(--rs) 0;
  padding: 10px 13px; margin-top: 10px;
  font-size: 12px; color: #f5c4a8; line-height: 1.6; font-family: var(--font-m);
}
.preset-info-peach strong { color: var(--txt); font-weight: 600; }

/* ── TECH PILLS ── */
.tech-pill {
  display: inline-flex; align-items: center;
  background: rgba(0,180,140,0.10); border: 1px solid rgba(0,212,168,0.24);
  color: #7eecd8; font-size: 11px; font-family: var(--font-m);
  padding: 3px 11px; border-radius: var(--rpill); margin: 3px;
}
.tech-pill-peach {
  display: inline-flex; align-items: center;
  background: rgba(180,90,40,0.12); border: 1px solid rgba(200,110,60,0.28);
  color: #f5c4a8; font-size: 11px; font-family: var(--font-m);
  padding: 3px 11px; border-radius: var(--rpill); margin: 3px;
}

/* ── DIVIDER ── */
hr {
  border: none !important; height: 1px !important;
  background: linear-gradient(90deg, transparent 0%, rgba(0,212,168,0.22) 25%, rgba(240,168,130,0.16) 65%, transparent 100%) !important;
  margin: 36px 0 !important;
}

/* ── BUTTONS ── */
div.stButton > button {
  background: rgba(0,180,140,0.08) !important;
  color: rgba(220,245,238,0.88) !important;   /* FIXED: was too dim */
  border: 1px solid rgba(0,212,168,0.22) !important;
  border-radius: var(--rs) !important;
  padding: 10px 20px !important;
  font-weight: 500 !important; font-size: 13px !important;
  font-family: var(--font-b) !important;
  transition: var(--t) !important;
  backdrop-filter: blur(10px) !important;
}
div.stButton > button:hover {
  background: rgba(0,180,140,0.16) !important;
  border-color: rgba(0,212,168,0.42) !important;
  color: #fff !important; transform: translateY(-2px) !important;
  box-shadow: 0 4px 18px rgba(0,0,0,0.28) !important;
}
div.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #007d5e 0%, #00c49a 55%, #e09070 100%) !important;
  border: none !important;
  color: rgba(2, 14, 8, 0.96) !important;
  font-weight: 700 !important; font-size: 13.5px !important;
  box-shadow: 0 4px 22px rgba(0,180,140,0.30) !important;
}
div.stButton > button[kind="primary"]:hover {
  background: linear-gradient(135deg, #006a50 0%, #00aa85 55%, #c87858 100%) !important;
  box-shadow: 0 8px 30px rgba(0,180,140,0.38) !important;
  transform: translateY(-3px) !important;
}
.stDownloadButton button {
  background: rgba(160,70,20,0.10) !important;
  border: 1px solid rgba(200,110,60,0.28) !important;
  color: rgba(245, 200, 168, 0.92) !important;   /* FIXED */
  border-radius: var(--rs) !important; font-weight: 500 !important;
  font-family: var(--font-b) !important; transition: var(--t) !important;
}
.stDownloadButton button:hover {
  background: rgba(160,70,20,0.20) !important;
  border-color: rgba(200,110,60,0.48) !important;
  transform: translateY(-2px) !important;
}

/* ── FORM INPUTS ── */
.stTextArea textarea, .stTextInput > div > div > input {
  background: rgba(2,18,10,0.65) !important;
  border: 1px solid rgba(0,212,168,0.18) !important;
  border-radius: var(--rs) !important; color: var(--txt) !important;
  font-family: var(--font-b) !important; font-size: 14px !important;
  caret-color: #00d4a8 !important; backdrop-filter: blur(10px) !important;
  transition: var(--t) !important;
}
.stTextArea textarea:focus, .stTextInput > div > div > input:focus {
  border-color: rgba(0,212,168,0.50) !important;
  box-shadow: 0 0 0 3px rgba(0,212,168,0.10) !important;
}
.stTextArea label, .stTextInput label {
  color: rgba(200,245,235,0.85) !important; font-weight: 600 !important; font-size: 12px !important;
}
.stSelectbox [data-baseweb="select"] > div:first-child {
  background: rgba(2,18,10,0.65) !important;
  border: 1px solid rgba(0,212,168,0.18) !important;
  border-radius: var(--rs) !important; color: var(--txt) !important;
}
.stSelectbox [data-baseweb="select"] > div:first-child:hover { border-color: rgba(0,212,168,0.38) !important; }
.stSelectbox label { color: rgba(200,245,235,0.85) !important; font-size: 12px !important; font-weight: 600 !important; }
[data-baseweb="popover"] [data-baseweb="menu"] {
  background: rgba(2,14,8,0.97) !important;
  backdrop-filter: blur(24px) !important;
  border: 1px solid rgba(0,212,168,0.16) !important;
  border-radius: var(--rs) !important;
  box-shadow: 0 20px 56px rgba(0,0,0,0.60) !important;
}
[data-baseweb="option"] { color: rgba(220,245,238,0.80) !important; }
[data-baseweb="option"]:hover { background: rgba(0,212,168,0.12) !important; color: #fff !important; }
[aria-selected="true"][data-baseweb="option"] { background: rgba(0,212,168,0.16) !important; color: #7eecd8 !important; }
.stSlider [data-testid="stSliderThumb"] {
  background: white !important; border: 2px solid #00d4a8 !important;
  box-shadow: 0 0 10px rgba(0,212,168,0.45) !important;
}
.stSlider [data-testid="stSliderTrackFill"] { background: linear-gradient(90deg, #00d4a8, #f0a882) !important; }
.stSlider label { color: rgba(200,245,235,0.85) !important; font-size: 12px !important; font-weight: 600 !important; }
.stFileUploader > div {
  background: rgba(0,180,140,0.04) !important;
  border: 1.5px dashed rgba(0,212,168,0.22) !important;
  border-radius: var(--rm) !important;
}
.stFileUploader > div:hover { border-color: rgba(0,212,168,0.42) !important; background: rgba(0,180,140,0.08) !important; }
.stFileUploader label { color: rgba(200,245,235,0.85) !important; font-size: 12px !important; font-weight: 600 !important; }
.stProgress > div > div {
  background: linear-gradient(90deg, #00d4a8, #7eecd8 55%, #f0a882) !important;
  border-radius: var(--rpill) !important; box-shadow: 0 2px 10px rgba(0,212,168,0.28) !important;
}
.stProgress > div { background: rgba(0,212,168,0.10) !important; border-radius: var(--rpill) !important; }
.stAlert { background: rgba(0,180,140,0.08) !important; border: 1px solid rgba(0,212,168,0.22) !important; border-radius: var(--rs) !important; }
.stCaption,[data-testid="caption"] { color: rgba(200,235,225,0.48) !important; font-size: 12px !important; }
.stMarkdown p { color: rgba(220,245,238,0.78) !important; font-size: 14px !important; line-height: 1.75 !important; }
h2 { font-family: var(--font-d) !important; color: var(--txt) !important; font-size: 24px !important; font-weight: 700 !important; }
h3 { font-family: var(--font-d) !important; color: var(--txt) !important; font-size: 19px !important; font-weight: 600 !important; }
h4 { font-family: var(--font-d) !important; color: #7eecd8 !important; font-size: 14px !important; font-weight: 700 !important; }
.stSpinner > div { border-top-color: #00d4a8 !important; }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: rgba(2,12,8,0.60); }
::-webkit-scrollbar-thumb { background: linear-gradient(180deg, #00d4a8, #7eecd8); border-radius: 3px; }
.img-comparison-wrap { border: 1px solid rgba(255,255,255,0.10); border-radius: var(--rm); overflow: hidden; }
.stVideo { border-radius: var(--rm) !important; overflow: hidden !important; }
video { border-radius: var(--rm) !important; box-shadow: 0 8px 32px rgba(0,0,0,0.45) !important; border: 1px solid rgba(200,110,60,0.20) !important; }

/* ── TOAST / NOTIFICATION OVERRIDE ── */
[data-testid="stToast"] {
  background: rgba(2,20,12,0.92) !important;
  border: 1px solid rgba(0,212,168,0.25) !important;
  border-radius: var(--rm) !important;
  backdrop-filter: blur(20px) !important;
}

/* ANIMATIONS */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(18px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulseGlow {
  0%, 100% { box-shadow: 0 0 6px rgba(0,212,168,0.4); }
  50%       { box-shadow: 0 0 14px rgba(0,212,168,0.8); }
}
.fade-up   { animation: fadeUp 0.42s cubic-bezier(0.22,1,0.36,1) forwards; }
.fade-up-1 { animation: fadeUp 0.42s 0.06s cubic-bezier(0.22,1,0.36,1) both; }
.fade-up-2 { animation: fadeUp 0.42s 0.12s cubic-bezier(0.22,1,0.36,1) both; }
.fade-up-3 { animation: fadeUp 0.42s 0.19s cubic-bezier(0.22,1,0.36,1) both; }
.fade-up-4 { animation: fadeUp 0.42s 0.27s cubic-bezier(0.22,1,0.36,1) both; }
.pulse-dot { animation: pulseGlow 2.2s ease-in-out infinite; }

/* ═══════════════════════════════════════════════════════════
   RESPONSIVE / MOBILE + TABLET COMPATIBILITY
   (layout & sizing only — no colors/textures/gradients changed)
═══════════════════════════════════════════════════════════ */

/* ── Large tablets / small laptops ── */
@media (max-width: 1100px) {
  .block-container { padding: 2rem 1.5rem 3rem !important; max-width: 100% !important; }
  .page-title { font-size: 38px !important; }
  .metric-val { font-size: 42px !important; }
}

/* ── Tablets (portrait) ── */
@media (max-width: 900px) {
  .block-container { padding: 1.6rem 1.2rem 2.5rem !important; }
  .page-title { font-size: 32px !important; letter-spacing: -0.8px !important; }
  .page-subtitle { max-width: 100% !important; font-size: 14px !important; }
  .metric-card { padding: 18px 16px !important; }
  .metric-val { font-size: 34px !important; }
  .action-card { padding: 20px 14px !important; }
  .action-icon { font-size: 26px !important; }
  .glass-card, .glass-card-peach { padding: 18px !important; }
}

/* ── Phones (landscape / large) ── */
@media (max-width: 640px) {
  .block-container { padding: 1.1rem 0.9rem 2.2rem !important; }
  .page-header { margin-bottom: 26px !important; }
  .page-eyebrow { font-size: 9px !important; letter-spacing: 2.5px !important; }
  .page-title { font-size: 26px !important; letter-spacing: -0.5px !important; line-height: 1.12 !important; }
  .page-subtitle { font-size: 13px !important; line-height: 1.55 !important; }

  .metric-card { padding: 16px 14px !important; border-radius: var(--rm) !important; }
  .metric-val { font-size: 28px !important; margin-bottom: 3px !important; }
  .metric-tag { font-size: 8px !important; letter-spacing: 2px !important; margin-bottom: 8px !important; }
  .metric-label { font-size: 11px !important; }
  .metric-icon { font-size: 17px !important; top: 12px !important; right: 12px !important; }

  .action-card { padding: 18px 12px !important; }
  .action-icon { font-size: 24px !important; margin-bottom: 8px !important; }
  .action-title { font-size: 13px !important; }
  .action-desc { font-size: 11px !important; }

  .section-title { font-size: 13.5px !important; }
  .section-header { margin-bottom: 14px !important; gap: 8px !important; }

  .glass-card, .glass-card-peach { padding: 16px !important; border-radius: var(--rm) !important; }

  .sb-title { font-size: 18px !important; letter-spacing: 1px !important; }
  .sb-logo-icon { width: 38px !important; height: 38px !important; font-size: 17px !important; }
  .sb-tagline { font-size: 11px !important; }

  .img-placeholder, .video-placeholder { padding: 34px 18px !important; }
  .img-placeholder-icon, .video-placeholder-icon { font-size: 32px !important; }
  .img-placeholder-text, .video-placeholder-text { font-size: 12.5px !important; }

  .preset-info, .preset-info-peach { font-size: 11px !important; padding: 8px 11px !important; }
  .tech-pill, .tech-pill-peach { font-size: 10px !important; padding: 3px 9px !important; }

  div.stButton > button { font-size: 12.5px !important; padding: 9px 16px !important; }
  div.stButton > button[kind="primary"] { font-size: 13px !important; }

  h2 { font-size: 20px !important; }
  h3 { font-size: 16px !important; }
  h4 { font-size: 13px !important; }

  hr { margin: 24px 0 !important; }
}

/* ── Small phones ── */
@media (max-width: 400px) {
  .page-title { font-size: 22px !important; }
  .metric-val { font-size: 24px !important; }
  .action-icon { font-size: 20px !important; }
}

/* ── Ensure media never overflows on any screen ── */
img, video, .stVideo, .stImage, .img-frame img {
  max-width: 100% !important;
  height: auto !important;
}

/* ── Sidebar becomes a slide-over drawer on phones (native Streamlit behavior);
     just make sure its contents don't force horizontal scroll ── */
@media (max-width: 640px) {
  section[data-testid="stSidebar"] { width: 86vw !important; min-width: 240px !important; }
}

/* ── Prevent horizontal scrollbars from fixed-width elements ── */
html, body, [data-testid="stAppViewContainer"] { overflow-x: hidden !important; }
</style>
""", unsafe_allow_html=True)

# ═══════ PRESETS ═══════ #
PRESETS = {
    "🎨 No Style":       "",
    "🎬 Cinematic":      "cinematic lighting, ultra realistic, 4k, dramatic, volumetric lighting",
    "🌸 Anime":          "anime style, vibrant colors, cel shaded, studio ghibli inspired",
    "🧙 Fantasy":        "fantasy art, magical, ethereal, trending on artstation, epic composition",
    "🌆 Cyberpunk":      "cyberpunk style, neon lights, synthwave, blade runner aesthetic",
    "📸 Photorealistic": "photorealistic, 8k, sharp focus, professional photography, DSLR",
    "🎨 Oil Painting":   "oil painting, textured, impressionistic, museum quality, artistic",
    "🌊 Watercolor":     "watercolor painting, soft edges, flowing colors, artistic",
    "🤖 Sci-Fi":         "science fiction, futuristic, space opera, concept art, hard sci-fi",
    "✏️ Custom":         "CUSTOM"
}

VIDEO_MOTION_PRESETS = {
    "🌊 Smooth Pan":   "slow cinematic pan, smooth motion, gentle drift",
    "⚡ Dynamic":      "dynamic motion, energetic movement, fast paced",
    "🌸 Gentle Float": "floating gently, soft motion, dreamy movement",
    "🔥 Epic Zoom":    "epic slow zoom, cinematic reveal, dramatic scale",
    "🌀 Swirl":        "swirling motion, circular movement, spiral",
    "🎬 Cinematic":    "cinematic camera movement, film-like motion, professional",
    "✏️ Custom":       "CUSTOM"
}

# ═══════ HELPERS ═══════ #
def back_button(key: str):
    st.markdown('<div class="back-btn-wrap">', unsafe_allow_html=True)
    col_btn, _ = st.columns([1, 6])
    with col_btn:
        if st.button("← Back to Dashboard", key=key):
            st.session_state.selected_menu = "Dashboard"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def check_api_keys():
    """Validate that API keys are configured."""
    stability_ok = bool(STABILITY_API_KEY and len(STABILITY_API_KEY) > 10)
    replicate_ok = bool(REPLICATE_API_TOKEN and len(REPLICATE_API_TOKEN) > 10)
    return stability_ok, replicate_ok


def format_count(n):
    """Format a number for display."""
    return f"{n:,}" if n >= 1000 else str(n)


# ═══════ API FUNCTIONS ═══════ #
@st.cache_data(ttl=3600)
def generate_image(prompt):
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    body = {
        "text_prompts": [{"text": prompt, "weight": 1.0}],
        "cfg_scale": 7, "height": 1024, "width": 1024, "samples": 1, "steps": 30
    }
    try:
        res = requests.post(url, headers=headers, json=body, timeout=90)
        if res.status_code == 401:
            return None, "Invalid Stability AI API key. Check your .env file."
        if res.status_code == 402:
            return None, "Stability AI account has insufficient credits."
        if res.status_code != 200:
            return None, f"API error {res.status_code}: {res.text[:200]}"
        data = res.json()
        if "artifacts" not in data or not data["artifacts"]:
            return None, "No image returned from API."
        return base64.b64decode(data["artifacts"][0]["base64"]), None
    except requests.exceptions.Timeout:
        return None, "Request timed out after 90s. Please try again."
    except requests.exceptions.ConnectionError:
        return None, "Could not connect to Stability AI. Check your internet connection."
    except Exception as e:
        return None, str(e)


def enhance_image(image_path, scale=4):
    try:
        with open(image_path, "rb") as f:
            output = replicate.run(
                "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b",
                input={"image": f, "scale": scale, "face_enhance": False}
            )
        url = output if isinstance(output, str) else (output[0] if isinstance(output, list) else None)
        if not url:
            return None, "Unexpected output from Replicate"
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return resp.content, None
    except replicate.exceptions.ReplicateError as e:
        return None, f"Replicate error: {str(e)}"
    except Exception as e:
        return None, str(e)


def generate_text_to_video(prompt, num_frames=24, fps=8, width=576, height=320):
    try:
        output = replicate.run(
            "anotherjesse/zeroscope-v2-xl:9f747673945c62801b13b84701c783929c0ee784e4748ec062204894dda1a351",
            input={
                "prompt": prompt, "num_frames": num_frames, "fps": fps,
                "width": width, "height": height,
                "num_inference_steps": 50, "guidance_scale": 17.5,
            }
        )
        video_url = output[0] if isinstance(output, list) else output
        resp = requests.get(video_url, timeout=180)
        resp.raise_for_status()
        return resp.content, None
    except replicate.exceptions.ReplicateError as e:
        return None, f"Replicate error: {str(e)}"
    except Exception as e:
        return None, str(e)


def generate_photo_to_video(image_path, motion_bucket_id=127, fps=6, cond_aug=0.02):
    try:
        with open(image_path, "rb") as f:
            output = replicate.run(
                "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
                input={
                    "input_image": f, "motion_bucket_id": motion_bucket_id,
                    "fps_id": fps, "cond_aug": cond_aug, "decoding_t": 14, "frames": 25,
                }
            )
        video_url = output[0] if isinstance(output, list) else output
        resp = requests.get(video_url, timeout=180)
        resp.raise_for_status()
        return resp.content, None
    except replicate.exceptions.ReplicateError as e:
        return None, f"Replicate error: {str(e)}"
    except Exception as e:
        return None, str(e)


# ═══════ SIDEBAR ═══════ #
with st.sidebar:
    st.markdown("""
    <div class="sb-brand">
        <div class="sb-logo-wrap">
            <div class="sb-logo-icon">✦</div>
            <div>
                <div class="sb-title">Imaginer</div>
                <div class="sb-sub">Studio · v3.0</div>
            </div>
        </div>
        <div class="sb-tagline">AI-powered image &amp; video generation platform</div>
    </div>
    """, unsafe_allow_html=True)

    pages = [
        ("Dashboard",      "📊", "Overview & quick actions",           False),
        ("AI Generation",  "🎨", "Text-to-image creation",             False),
        ("Enhance",        "✨", "Upscale & restore images",           False),
        ("Text to Video",  "🎬", "Generate video from text prompt",    True),
        ("Photo to Video", "📷", "Animate a photo into a video",       True),
        ("History",        "🖼️", "Your image gallery",                 False),
    ]

    st.markdown('<div class="sb-nav-section"><div class="sb-nav-label">Navigation</div>', unsafe_allow_html=True)
    for page, icon, tip, is_new in pages:
        active = "active" if st.session_state.selected_menu == page else ""
        badge = ""
        if page == "History" and st.session_state.history:
            badge = f'<span class="sb-nav-badge">{len(st.session_state.history)}</span>'
        elif is_new:
            badge = '<span class="sb-nav-new">NEW</span>'
        st.markdown(
            f'<div class="sb-nav-item {active}">'
            f'<span class="sb-nav-icon">{icon}</span>'
            f'<span class="sb-nav-text">{page}</span>{badge}</div>',
            unsafe_allow_html=True
        )
        if st.button(page, key=f"nav_{page}", use_container_width=True, help=tip):
            st.session_state.selected_menu = page
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Session Stats ──
    st.markdown(f"""
    <div class="sb-stats">
        <div class="sb-stats-title">Session Stats</div>
        <div class="sb-stat-row"><span class="sb-stat-label">Generated</span><span class="sb-stat-val">{format_count(st.session_state.generated_count)}</span></div>
        <div class="sb-stat-row"><span class="sb-stat-label">Enhanced</span><span class="sb-stat-val">{format_count(st.session_state.enhanced_count)}</span></div>
        <div class="sb-stat-row"><span class="sb-stat-label">Videos</span><span class="sb-stat-val">{format_count(st.session_state.video_count)}</span></div>
        <div class="sb-stat-row"><span class="sb-stat-label">Gallery</span><span class="sb-stat-val">{len(st.session_state.history)}</span></div>
        <div class="sb-stat-row"><span class="sb-stat-label">AI Models</span><span class="sb-stat-val">4</span></div>
    </div>
    """, unsafe_allow_html=True)

    # ── API Status (NEW) ──
    stability_ok, replicate_ok = check_api_keys()
    st.markdown(f"""
    <div class="sb-stats" style="margin-top:0;">
        <div class="sb-stats-title">API Status</div>
        <div class="api-status-row">
            <div class="status-dot {'ok' if stability_ok else 'err'} pulse-dot"></div>
            <span class="status-label">Stability AI</span>
            <span class="status-val {'ok' if stability_ok else 'err'}">{'Connected' if stability_ok else 'No Key'}</span>
        </div>
        <div class="api-status-row" style="margin-top:6px;">
            <div class="status-dot {'ok' if replicate_ok else 'err'} pulse-dot"></div>
            <span class="status-label">Replicate</span>
            <span class="status-val {'ok' if replicate_ok else 'err'}">{'Connected' if replicate_ok else 'No Key'}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="sb-footer">
        <div class="sb-footer-text">
            <div class="sb-version-pill">v3.0</div><br>
            Stability AI · Replicate · SVD<br>
            <span style="color:rgba(255,255,255,0.20);">© 2025 Imaginer Studio · Arijit Bera</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

menu = st.session_state.selected_menu

# ══════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════
if menu == "Dashboard":
    st.markdown("""
    <div class="page-header fade-up">
        <div class="page-eyebrow">IMAGINER STUDIO · Made by · Arijit Bera</div>
        <div class="page-title">Creative <span class="hl-teal">Command Center</span></div>
        <div class="page-subtitle">Monitor your session, launch tools, and explore your creations — all from one place.</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Metric Cards ──
    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        ("mc1", st.session_state.generated_count, "Generated",  "Images Created",  "🎨", "AI Generation"),
        ("mc2", st.session_state.enhanced_count,  "Enhanced",   "Images Enhanced", "✨", "Enhance"),
        ("mc3", st.session_state.video_count,      "Videos",     "Videos Created",  "🎬", "Text to Video"),
        ("mc4", len(st.session_state.history),     "Gallery",    "Total Assets",    "🖼️", "History"),
        ("mc5", 4,                                 "Models",     "AI Engines",      "🧠", None),
    ]
    for col, (cls, val, tag, lbl, icon, dest) in zip([c1, c2, c3, c4, c5], metrics):
        with col:
            display_val = format_count(val)
            st.markdown(
                f'<div class="metric-card {cls} fade-up">'
                f'<div class="metric-tag">{tag}</div>'
                f'<div class="metric-val">{display_val}</div>'
                f'<div class="metric-label">{lbl}</div>'
                f'<div class="metric-icon">{icon}</div></div>',
                unsafe_allow_html=True
            )
            # IMPROVED: the hint below the card is now a real, tappable link —
            # jumps straight to the matching tool. Great for mobile where the
            # sidebar nav is tucked away in a drawer.
            if dest:
                cta_label = "Start creating →" if val == 0 else "View →"
                st.markdown('<div class="metric-cta-wrap">', unsafe_allow_html=True)
                if st.button(cta_label, key=f"metric_nav_{cls}", use_container_width=True):
                    st.session_state.selected_menu = dest
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # ── API Key Warning Banner ──
    if not stability_ok or not replicate_ok:
        missing = []
        if not stability_ok: missing.append("STABILITY_API_KEY")
        if not replicate_ok: missing.append("REPLICATE_API_TOKEN")
        st.warning(
            f"⚠️  Missing API keys: **{', '.join(missing)}**. "
            f"Add them to your `.env` file to enable generation features.",
            icon="🔑"
        )

    st.markdown('<hr>', unsafe_allow_html=True)

    # ── Quick Actions ──
    st.markdown(
        '<div class="section-header fade-up-1">'
        '<div class="section-dot"></div>'
        '<div class="section-title">Quick Actions</div>'
        '<div class="section-line"></div></div>',
        unsafe_allow_html=True
    )

    q1, q2, q3, q4, q5 = st.columns(5)
    quick = [
        (q1, "🎨", "AI Generation",     "Generate stunning images from text prompts using SDXL.",           "AI Generation",  "q_gen",  "ac1", False),
        (q2, "✨", "Enhance & Upscale", "Restore & upscale images up to 8× using Real-ESRGAN.",             "Enhance",        "q_enh",  "ac2", False),
        (q3, "🎬", "Text to Video",     "Turn any text prompt into a fluid AI-generated video clip.",       "Text to Video",  "q_t2v",  "ac3", True),
        (q4, "📷", "Photo to Video",    "Animate still photos using Stable Video Diffusion.",               "Photo to Video", "q_p2v",  "ac4", True),
        (q5, "🖼️", "Image Gallery",     "Browse, download & manage all your AI-generated creations.",      "History",        "q_hist", "ac5", False),
    ]
    for col, icon, title, desc, dest, key, card_cls, is_new in quick:
        with col:
            new_badge = '<div class="ac-badge-new">✦ New</div>' if is_new else ""
            st.markdown(
                f'<div class="action-card {card_cls} fade-up-2">'
                f'<span class="action-icon">{icon}</span>'
                f'<div class="action-title">{title}</div>'
                f'<div class="action-desc">{desc}</div>'
                f'{new_badge}</div>',
                unsafe_allow_html=True
            )
            if st.button(f"Open →", key=key, use_container_width=True):
                st.session_state.selected_menu = dest
                st.rerun()

    st.markdown('<hr>', unsafe_allow_html=True)

    # ── About + Tech Stack ──
    left, right = st.columns([1, 1.6])
    with left:
        st.markdown(
            '<div class="section-header fade-up-3">'
            '<div class="section-dot"></div>'
            '<div class="section-title">About This Project</div>'
            '<div class="section-line"></div></div>',
            unsafe_allow_html=True
        )
        st.markdown("""
        <div class="glass-card fade-up-3">
            <p style="color:rgba(215,245,238,0.78);font-size:13.5px;line-height:1.8;margin:0 0 16px;font-weight:300;">
                <strong style="color:rgba(255,255,255,0.95);">Imaginer Studio</strong> is a personal AI creative platform
                combining cutting-edge diffusion models with GAN-based enhancement and
                video generation — built to explore the intersection of machine learning and visual art.
            </p>
            <div>
                <span class="tech-pill">🔬 SDXL 1.0</span>
                <span class="tech-pill">⚡ Real-ESRGAN</span>
                <span class="tech-pill">🐍 Streamlit</span>
                <span class="tech-pill">🔁 Replicate API</span>
                <span class="tech-pill-peach">🎬 ZeroScope v2</span>
                <span class="tech-pill-peach">📷 Stable Video Diffusion</span>
            </div>
        </div>""", unsafe_allow_html=True)

    with right:
        st.markdown(
            '<div class="section-header fade-up-3">'
            '<div class="section-dot"></div>'
            '<div class="section-title">Technology Stack</div>'
            '<div class="section-line"></div></div>',
            unsafe_allow_html=True
        )
        tc1, tc2 = st.columns(2)
        with tc1:
            st.markdown("""
            <div class="glass-card fade-up-3"><h4>🎨 Generation Engine</h4>
            <p style="margin:10px 0 0;color:rgba(200,240,232,0.68);font-size:13px;line-height:1.8;font-weight:300;">
            <strong style="color:#7eecd8;">Stable Diffusion XL 1.0</strong><br>
            Diffusion Architecture · 1024×1024<br>
            10 curated style presets<br>
            <strong style="color:#f5c4a8;">ZeroScope v2 XL</strong><br>
            Text → Video generation</p></div>
            """, unsafe_allow_html=True)
        with tc2:
            st.markdown("""
            <div class="glass-card fade-up-4"><h4>✨ Enhancement & Video</h4>
            <p style="margin:10px 0 0;color:rgba(200,240,232,0.68);font-size:13px;line-height:1.8;font-weight:300;">
            <strong style="color:#f5c4a8;">Real-ESRGAN GAN</strong><br>
            2× · 4× · 8× upscaling<br>
            Texture &amp; noise recovery<br>
            <strong style="color:#f5c4a8;">Stable Video Diffusion</strong><br>
            Photo → Video animation</p></div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# AI GENERATION
# ══════════════════════════════════════════════════
elif menu == "AI Generation":
    back_button("back_gen")

    if not stability_ok:
        st.error("🔑 **Stability AI key missing.** Add `STABILITY_API_KEY` to your `.env` file.", icon="🔑")

    st.markdown("""
    <div class="page-header fade-up">
        <div class="page-eyebrow">Studio · Generate</div>
        <div class="page-title">Text-to-<span class="hl-teal">Image</span></div>
        <div class="page-subtitle">Describe your vision and let Stable Diffusion XL bring it to life.</div>
    </div>
    """, unsafe_allow_html=True)

    left_col, right_col = st.columns([1, 1.15])

    with left_col:
        st.markdown('<div class="glass-card fade-up-1">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-header" style="margin-bottom:18px;">'
            '<div class="section-dot"></div>'
            '<div class="section-title">Compose Your Prompt</div></div>',
            unsafe_allow_html=True
        )
        prompt = st.text_area(
            "Image description", height=130, key="gen_prompt",
            placeholder="A lone astronaut stands on a rust-red Martian plateau, gazing at twin moons rising over jagged cliffs…"
        )
        char_count = len(prompt)
        if char_count > 0:
            st.caption(f"✍️ {char_count} characters")

        st.markdown(
            '<div class="section-header" style="margin:18px 0 14px;">'
            '<div class="section-dot"></div>'
            '<div class="section-title" style="font-size:15px;">Style Preset</div></div>',
            unsafe_allow_html=True
        )
        selected_preset = st.selectbox("Choose a visual style", list(PRESETS.keys()), key="gen_preset")
        custom_style = ""
        if selected_preset == "✏️ Custom":
            custom_style = st.text_input("Custom style descriptor", key="gen_custom",
                                         placeholder="e.g., chalk illustration, risograph print…")
        elif selected_preset != "🎨 No Style":
            st.markdown(
                f'<div class="preset-info"><strong>Active style →</strong> {selected_preset}<br>'
                f'<span style="opacity:0.75;font-size:11.5px;">{PRESETS[selected_preset]}</span></div>',
                unsafe_allow_html=True
            )
        else:
            st.caption("ℹ️  No style modifier — your prompt is used as-is")

        st.markdown('<div style="margin-top:22px;"></div>', unsafe_allow_html=True)
        generate_clicked = st.button(
            "🚀  Generate Image", type="primary", use_container_width=True,
            key="gen_btn", disabled=(not stability_ok)
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="glass-card fade-up-1" style="height:100%;">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-header" style="margin-bottom:18px;">'
            '<div class="section-dot"></div>'
            '<div class="section-title">Generated Result</div></div>',
            unsafe_allow_html=True
        )
        if st.session_state.last_generated is not None:
            st.markdown('<div class="img-frame">', unsafe_allow_html=True)
            st.image(st.session_state.last_generated, use_column_width=True)
            st.markdown('</div><div style="margin-top:14px;"></div>', unsafe_allow_html=True)
            st.download_button(
                "⬇️  Download Image", st.session_state.last_generated,
                "imaginer_generated.png", use_container_width=True, key="dl_gen"
            )
        else:
            st.markdown(
                '<div class="img-placeholder">'
                '<span class="img-placeholder-icon">🎨</span>'
                '<div class="img-placeholder-text">Your generated image will appear here.</div>'
                '<div class="img-placeholder-hint">Enter a prompt and hit Generate →</div>'
                '</div>',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    if generate_clicked:
        if not prompt.strip():
            st.warning("⚠️  Please enter a prompt before generating.")
        else:
            parts = [prompt]
            if selected_preset not in ["🎨 No Style", "✏️ Custom"]:
                parts.append(PRESETS[selected_preset])
            if selected_preset == "✏️ Custom" and custom_style.strip():
                parts.append(custom_style)

            progress_bar = st.progress(0)
            status_text  = st.empty()
            for i in range(100):
                time.sleep(0.02)
                progress_bar.progress(i + 1)
                if i < 30:   status_text.text("🎨  Initialising diffusion pipeline…")
                elif i < 60: status_text.text("🤖  Running SDXL inference…")
                elif i < 90: status_text.text("✨  Refining high-frequency details…")
                else:         status_text.text("🏁  Finalising your masterpiece…")

            img, err = generate_image(", ".join(parts))
            progress_bar.empty(); status_text.empty()
            if err:
                st.error(f"❌  Generation failed: {err}")
            else:
                st.session_state.last_generated = img
                st.session_state.history.append(img)
                st.session_state.generated_count += 1
                st.balloons()
                st.toast("✨  Image generated successfully!", icon="🎉")
                time.sleep(0.8)
                st.rerun()

# ══════════════════════════════════════════════════
# ENHANCE
# ══════════════════════════════════════════════════
elif menu == "Enhance":
    back_button("back_enh")

    if not replicate_ok:
        st.error("🔑 **Replicate token missing.** Add `REPLICATE_API_TOKEN` to your `.env` file.", icon="🔑")

    st.markdown("""
    <div class="page-header fade-up">
        <div class="page-eyebrow">Studio · Enhance</div>
        <div class="page-title">AI <span class="hl-teal">Upscaler</span></div>
        <div class="page-subtitle">Restore detail and upscale resolution up to 8× using Real-ESRGAN GAN inference.</div>
    </div>
    """, unsafe_allow_html=True)

    left_col, right_col = st.columns([1, 1.5])

    with left_col:
        st.markdown('<div class="glass-card fade-up-1">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-header" style="margin-bottom:18px;">'
            '<div class="section-dot"></div>'
            '<div class="section-title">Upload & Configure</div></div>',
            unsafe_allow_html=True
        )
        file = st.file_uploader("Select image", type=["png", "jpg", "jpeg", "webp"], key="enhance_uploader")
        enhance_clicked = False

        if file is not None:
            img_bytes = file.read()
            input_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            st.session_state.enhance_original = input_img
            st.markdown(
                '<div class="section-header" style="margin:20px 0 14px;">'
                '<div class="section-dot"></div>'
                '<div class="section-title" style="font-size:15px;">Upscale Factor</div></div>',
                unsafe_allow_html=True
            )
            scale = st.select_slider("Resolution multiplier", options=[2, 4, 8],
                                     value=st.session_state.enhance_scale, key="scale_slider")
            st.session_state.enhance_scale = scale
            w, h = input_img.size
            file_size_kb = len(img_bytes) / 1024
            st.markdown(
                f'<div class="preset-info"><strong>Input:</strong> {w} × {h} px · {file_size_kb:.0f} KB<br>'
                f'<strong style="color:#f5c4a8;">Output: {w*scale} × {h*scale} px</strong></div>',
                unsafe_allow_html=True
            )
            st.markdown('<div style="margin-top:22px;"></div>', unsafe_allow_html=True)
            enhance_clicked = st.button(
                "✨  Enhance Image", type="primary", use_container_width=True,
                key="enh_btn", disabled=(not replicate_ok)
            )
        else:
            st.markdown(
                '<div class="img-placeholder" style="padding:30px;">'
                '<span class="img-placeholder-icon">📤</span>'
                '<div class="img-placeholder-text">Upload an image to begin enhancement</div>'
                '<div class="img-placeholder-hint">Supports PNG, JPG, JPEG, WEBP</div>'
                '</div>',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="glass-card fade-up-1">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-header" style="margin-bottom:18px;">'
            '<div class="section-dot"></div>'
            '<div class="section-title">Preview & Result</div></div>',
            unsafe_allow_html=True
        )
        if st.session_state.enhance_original is not None:
            if st.session_state.enhance_result is not None:
                st.markdown('<div class="img-frame">', unsafe_allow_html=True)
                st.image(st.session_state.enhance_result, caption="✨ Enhanced", use_column_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                if st.session_state.enhance_result_bytes:
                    st.markdown('<div style="margin-top:14px;"></div>', unsafe_allow_html=True)
                    st.download_button("⬇️  Download Enhanced Image", st.session_state.enhance_result_bytes,
                                       "imaginer_enhanced.png", use_container_width=True, key="dl_enh")
            else:
                st.markdown('<div class="img-frame">', unsafe_allow_html=True)
                st.image(st.session_state.enhance_original, caption="Original — awaiting enhancement", use_column_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="img-placeholder">'
                '<span class="img-placeholder-icon">🖼️</span>'
                '<div class="img-placeholder-text">Preview will appear here after upload</div></div>',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    if file is not None and enhance_clicked:
        input_img = st.session_state.enhance_original
        scale     = st.session_state.enhance_scale
        MAX_SIDE  = {2: 1536, 4: 1024, 8: 512}
        w, h      = input_img.size
        api_img   = input_img
        if max(w, h) > MAX_SIDE.get(scale, 1024):
            r       = MAX_SIDE.get(scale, 1024) / max(w, h)
            api_img = input_img.resize((int(w * r), int(h * r)), Image.LANCZOS)
            st.info(f"📏  Auto-resized to {api_img.size[0]} × {api_img.size[1]} px for API limits")

        pb = st.progress(0); status = st.empty()
        with st.spinner("Running Real-ESRGAN via Replicate…"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                api_img.save(tmp.name); tmp_path = tmp.name
            for i in range(100):
                time.sleep(0.03); pb.progress(i + 1)
                if i < 40:   status.text("🔍  Analysing image structure…")
                elif i < 70: status.text("🧠  Running GAN inference…")
                else:         status.text("✨  Reconstructing fine textures…")
            enhanced_bytes, err = enhance_image(tmp_path, scale=scale)
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            pb.empty(); status.empty()
            if err:
                st.error(f"❌  Enhancement failed: {err}")
            else:
                st.session_state.enhance_result       = Image.open(io.BytesIO(enhanced_bytes))
                st.session_state.enhance_result_bytes = enhanced_bytes
                st.session_state.history.append(enhanced_bytes)
                st.session_state.enhanced_count += 1
                st.balloons(); st.toast("✨  Image enhanced successfully!", icon="🎉")
                time.sleep(0.8); st.rerun()

    if st.session_state.enhance_original is not None and st.session_state.enhance_result is not None:
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-header fade-up">'
            '<div class="section-dot"></div>'
            '<div class="section-title">Side-by-Side Comparison</div>'
            '<div class="section-line"></div></div>',
            unsafe_allow_html=True
        )
        st.markdown('<div class="img-comparison-wrap">', unsafe_allow_html=True)
        image_comparison(img1=st.session_state.enhance_original, img2=st.session_state.enhance_result,
                         label1="Original", label2="Enhanced")
        st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# TEXT TO VIDEO
# ══════════════════════════════════════════════════
elif menu == "Text to Video":
    back_button("back_t2v")

    if not replicate_ok:
        st.error("🔑 **Replicate token missing.** Add `REPLICATE_API_TOKEN` to your `.env` file.", icon="🔑")

    st.markdown("""
    <div class="page-header fade-up">
        <div class="page-eyebrow">Studio · Text to Video · Powered by ZeroScope v2 XL</div>
        <div class="page-title">Text-to-<span class="hl-peach">Video</span></div>
        <div class="page-subtitle">Describe a scene and watch ZeroScope v2 XL render it into a fluid video clip.</div>
    </div>
    """, unsafe_allow_html=True)

    left_col, right_col = st.columns([1, 1.15])

    with left_col:
        st.markdown('<div class="glass-card-peach fade-up-1">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-header" style="margin-bottom:18px;">'
            '<div class="section-dot-peach"></div>'
            '<div class="section-title">Describe Your Scene</div></div>',
            unsafe_allow_html=True
        )
        t2v_prompt = st.text_area("Video description", height=120, key="t2v_prompt",
                                  placeholder="A majestic eagle soaring over misty mountain peaks at golden hour…")

        st.markdown(
            '<div class="section-header" style="margin:18px 0 14px;">'
            '<div class="section-dot-peach"></div>'
            '<div class="section-title" style="font-size:15px;">Motion Style</div></div>',
            unsafe_allow_html=True
        )
        motion_preset = st.selectbox("Motion preset", list(VIDEO_MOTION_PRESETS.keys()), key="t2v_motion")
        custom_motion = ""
        if motion_preset == "✏️ Custom":
            custom_motion = st.text_input("Custom motion descriptor", key="t2v_custom_motion",
                                          placeholder="e.g., timelapse, hyperlapse, slow zoom…")
        else:
            st.markdown(
                f'<div class="preset-info-peach"><strong>Motion →</strong> {motion_preset}<br>'
                f'<span style="opacity:0.80;font-size:11.5px;">{VIDEO_MOTION_PRESETS[motion_preset]}</span></div>',
                unsafe_allow_html=True
            )

        st.markdown(
            '<div class="section-header" style="margin:18px 0 14px;">'
            '<div class="section-dot-peach"></div>'
            '<div class="section-title" style="font-size:15px;">Video Settings</div></div>',
            unsafe_allow_html=True
        )
        vc1, vc2 = st.columns(2)
        with vc1:
            t2v_frames = st.select_slider("Frames", options=[16, 24, 32, 40], value=24, key="t2v_frames")
        with vc2:
            t2v_fps = st.select_slider("FPS", options=[6, 8, 10, 12], value=8, key="t2v_fps")

        t2v_res = st.selectbox("Resolution",
            ["576 × 320  (Fast)", "768 × 432  (Balanced)", "1024 × 576  (High Quality)"],
            index=1, key="t2v_res")
        res_map = {"576 × 320  (Fast)": (576,320), "768 × 432  (Balanced)": (768,432), "1024 × 576  (High Quality)": (1024,576)}
        t2v_w, t2v_h = res_map[t2v_res]
        duration_sec = round(t2v_frames / t2v_fps, 1)
        st.markdown(
            f'<div class="preset-info-peach">'
            f'<strong>Output:</strong> {t2v_w}×{t2v_h} · {t2v_frames} frames @ {t2v_fps} fps · ~{duration_sec}s</div>',
            unsafe_allow_html=True
        )
        st.markdown('<div style="margin-top:22px;"></div>', unsafe_allow_html=True)
        t2v_clicked = st.button(
            "🎬  Generate Video", type="primary", use_container_width=True,
            key="t2v_btn", disabled=(not replicate_ok)
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="glass-card-peach fade-up-1" style="height:100%;">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-header" style="margin-bottom:18px;">'
            '<div class="section-dot-peach"></div>'
            '<div class="section-title">Generated Video</div></div>',
            unsafe_allow_html=True
        )
        if st.session_state.txt2vid_result is not None:
            st.video(st.session_state.txt2vid_result)
            st.markdown('<div style="margin-top:14px;"></div>', unsafe_allow_html=True)
            st.download_button("⬇️  Download Video (.mp4)", st.session_state.txt2vid_result,
                               "imaginer_text2video.mp4", mime="video/mp4", use_container_width=True, key="dl_t2v")
            if st.session_state.txt2vid_prompt:
                st.markdown(
                    f'<div class="preset-info-peach" style="margin-top:12px;">'
                    f'<strong>Prompt used →</strong><br>'
                    f'<span style="opacity:0.80;font-size:11.5px;">{st.session_state.txt2vid_prompt}</span></div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                '<div class="video-placeholder">'
                '<span class="video-placeholder-icon">🎬</span>'
                '<div class="video-placeholder-text">Your generated video will appear here.</div>'
                '<div class="img-placeholder-hint" style="color:rgba(240,185,155,0.45);">Enter a description and hit Generate →</div>'
                '</div>',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    if t2v_clicked:
        if not t2v_prompt.strip():
            st.warning("⚠️  Please enter a scene description before generating.")
        else:
            motion_suffix = (custom_motion if motion_preset == "✏️ Custom"
                             else VIDEO_MOTION_PRESETS.get(motion_preset, ""))
            full_prompt = f"{t2v_prompt}, {motion_suffix}".strip(", ") if motion_suffix else t2v_prompt
            pb = st.progress(0); status = st.empty()
            for i in range(70):
                time.sleep(0.04); pb.progress(i + 1)
                if i < 20:   status.text("🎬  Initialising ZeroScope v2 XL…")
                elif i < 45: status.text("🧠  Running temporal diffusion…")
                elif i < 65: status.text("🎞️  Assembling video frames…")
                else:         status.text("⏳  Finalising — almost there…")
            with st.spinner("Rendering your video via Replicate (60–120s)…"):
                video_bytes, err = generate_text_to_video(full_prompt, num_frames=t2v_frames,
                                                          fps=t2v_fps, width=t2v_w, height=t2v_h)
            pb.progress(100); pb.empty(); status.empty()
            if err:
                st.error(f"❌  Video generation failed: {err}")
            else:
                st.session_state.txt2vid_result = video_bytes
                st.session_state.txt2vid_prompt = full_prompt
                st.session_state.video_count   += 1
                st.session_state.history.append({"type": "text_to_video", "data": video_bytes, "prompt": full_prompt})
                st.balloons(); st.toast("🎬  Video generated successfully!", icon="🎉")
                time.sleep(0.8); st.rerun()

# ══════════════════════════════════════════════════
# PHOTO TO VIDEO
# ══════════════════════════════════════════════════
elif menu == "Photo to Video":
    back_button("back_p2v")

    if not replicate_ok:
        st.error("🔑 **Replicate token missing.** Add `REPLICATE_API_TOKEN` to your `.env` file.", icon="🔑")

    st.markdown("""
    <div class="page-header fade-up">
        <div class="page-eyebrow">Studio · Photo to Video · Powered by Stable Video Diffusion</div>
        <div class="page-title">Photo-to-<span class="hl-peach">Video</span></div>
        <div class="page-subtitle">Upload any photo and Stable Video Diffusion will animate it into a living, breathing video clip.</div>
    </div>
    """, unsafe_allow_html=True)

    left_col, right_col = st.columns([1, 1.5])

    with left_col:
        st.markdown('<div class="glass-card-peach fade-up-1">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-header" style="margin-bottom:18px;">'
            '<div class="section-dot-peach"></div>'
            '<div class="section-title">Upload & Configure</div></div>',
            unsafe_allow_html=True
        )
        p2v_file = st.file_uploader("Upload your photo", type=["png","jpg","jpeg","webp"], key="p2v_uploader")
        p2v_clicked = False
        motion_bucket = 127
        p2v_fps = 6
        cond_aug = 0.02

        if p2v_file is not None:
            p2v_img = Image.open(io.BytesIO(p2v_file.read())).convert("RGB")
            st.session_state.img2vid_original = p2v_img
            st.markdown('<div class="img-frame" style="margin:14px 0;">', unsafe_allow_html=True)
            st.image(p2v_img, caption="Source photo", use_column_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown(
                '<div class="section-header" style="margin:18px 0 14px;">'
                '<div class="section-dot-peach"></div>'
                '<div class="section-title" style="font-size:15px;">Motion Controls</div></div>',
                unsafe_allow_html=True
            )
            motion_bucket = st.slider("Motion Intensity", min_value=1, max_value=255, value=127,
                                      key="p2v_motion_bucket")
            p2v_fps  = st.select_slider("Output FPS", options=[4,6,8,10], value=6, key="p2v_fps")
            cond_aug = st.select_slider("Augmentation Noise", options=[0.0,0.01,0.02,0.05,0.1],
                                        value=0.02, key="p2v_cond_aug")

            if motion_bucket < 60:    intensity_label, ic = "🌿 Subtle",   "#7eecd8"
            elif motion_bucket < 130: intensity_label, ic = "🌊 Balanced", "#a0f0e0"
            elif motion_bucket < 200: intensity_label, ic = "⚡ Dynamic",  "#f5c4a8"
            else:                      intensity_label, ic = "🔥 Dramatic", "#f5c4a8"

            w, h = p2v_img.size
            st.markdown(
                f'<div class="preset-info-peach">'
                f'<strong>Motion:</strong> <span style="color:{ic};">{intensity_label}</span> '
                f'· Bucket {motion_bucket} · {p2v_fps} fps<br>'
                f'<strong>Input:</strong> {w}×{h}px → 1024×576px for SVD</div>',
                unsafe_allow_html=True
            )
            st.markdown('<div style="margin-top:22px;"></div>', unsafe_allow_html=True)
            p2v_clicked = st.button(
                "📷  Animate Photo", type="primary", use_container_width=True,
                key="p2v_btn", disabled=(not replicate_ok)
            )
        else:
            st.markdown(
                '<div class="video-placeholder" style="padding:40px;">'
                '<span class="video-placeholder-icon">📷</span>'
                '<div class="video-placeholder-text">Upload a photo to animate it</div>'
                '<div class="img-placeholder-hint" style="color:rgba(240,185,155,0.45);">PNG, JPG, JPEG, WEBP supported</div>'
                '</div>',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="glass-card-peach fade-up-1" style="height:100%;">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-header" style="margin-bottom:18px;">'
            '<div class="section-dot-peach"></div>'
            '<div class="section-title">Animated Result</div></div>',
            unsafe_allow_html=True
        )
        if st.session_state.img2vid_result is not None:
            st.video(st.session_state.img2vid_result)
            st.markdown('<div style="margin-top:14px;"></div>', unsafe_allow_html=True)
            st.download_button("⬇️  Download Video (.mp4)", st.session_state.img2vid_result,
                               "imaginer_photo2video.mp4", mime="video/mp4",
                               use_container_width=True, key="dl_p2v")
        else:
            st.markdown(
                '<div class="video-placeholder">'
                '<span class="video-placeholder-icon">📽️</span>'
                '<div class="video-placeholder-text">Your animated video will appear here.<br>'
                'Upload a photo and configure motion settings.</div></div>',
                unsafe_allow_html=True
            )
        st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="glass-card-peach" style="padding:20px;">
            <div class="section-header" style="margin-bottom:12px;">
                <div class="section-dot-peach"></div>
                <div class="section-title" style="font-size:14px;">Tips for Best Results</div>
            </div>
            <div style="font-size:12.5px;color:rgba(240,200,170,0.68);line-height:1.9;">
                🌄 <strong style="color:rgba(255,220,190,0.90);">Landscapes & nature</strong> → high motion (150–220)<br>
                🏙️ <strong style="color:rgba(255,220,190,0.90);">Cityscapes</strong> → balanced (80–130)<br>
                🎭 <strong style="color:rgba(255,220,190,0.90);">Portraits</strong> → subtle (30–70)<br>
                🐾 <strong style="color:rgba(255,220,190,0.90);">Animals</strong> → dynamic (130–190)<br>
                📐 <strong style="color:rgba(255,220,190,0.90);">Best format:</strong> 16:9 wide images<br>
                📏 <strong style="color:rgba(255,220,190,0.90);">Auto-resizes</strong> to 1024×576 for SVD
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if p2v_file is not None and p2v_clicked:
        source_img = st.session_state.img2vid_original
        pb = st.progress(0); status = st.empty()
        svd_img = source_img.resize((1024, 576), Image.LANCZOS)
        for i in range(60):
            time.sleep(0.05); pb.progress(i + 1)
            if i < 15:   status.text("📷  Preparing source frame…")
            elif i < 35: status.text("🧠  Running Stable Video Diffusion…")
            elif i < 55: status.text("🎞️  Assembling animated frames…")
            else:         status.text("⏳  Encoding final video…")
        with st.spinner("Animating your photo via Replicate (60–180s)…"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                svd_img.save(tmp.name); tmp_path = tmp.name
            video_bytes, err = generate_photo_to_video(tmp_path, motion_bucket_id=motion_bucket,
                                                       fps=p2v_fps, cond_aug=cond_aug)
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        pb.progress(100); pb.empty(); status.empty()
        if err:
            st.error(f"❌  Animation failed: {err}")
        else:
            st.session_state.img2vid_result = video_bytes
            st.session_state.video_count   += 1
            st.session_state.history.append({
                "type": "photo_to_video", "data": video_bytes,
                "prompt": f"Photo animation · motion={motion_bucket} · fps={p2v_fps}"
            })
            st.balloons(); st.toast("📽️  Photo animated successfully!", icon="🎉")
            time.sleep(0.8); st.rerun()

# ══════════════════════════════════════════════════
# HISTORY / GALLERY
# ══════════════════════════════════════════════════
elif menu == "History":
    back_button("back_hist")
    st.markdown("""
    <div class="page-header fade-up">
        <div class="page-eyebrow">Studio · Gallery</div>
        <div class="page-title">Your <span class="hl-teal">Creative Archive</span></div>
        <div class="page-subtitle">All generated and enhanced images and videos from this session.</div>
    </div>
    """, unsafe_allow_html=True)

    tb1, tb2, tb3 = st.columns([1, 1, 4])
    with tb1:
        if st.button("🗑️  Clear Gallery", use_container_width=True, key="clear_hist"):
            for k in ["history","last_generated","enhance_result","enhance_original",
                      "enhance_result_bytes","txt2vid_result","txt2vid_prompt",
                      "img2vid_result","img2vid_original"]:
                st.session_state[k] = [] if k == "history" else None
            st.toast("Gallery cleared!", icon="🗑️"); time.sleep(0.6); st.rerun()
    with tb2:
        image_items_check = [item for item in st.session_state.history if isinstance(item, bytes)]
        if image_items_check:
            if st.button("📦  Export ZIP", use_container_width=True, key="export_all"):
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for i, img_b in enumerate(image_items_check):
                        zf.writestr(f"imaginer_{i+1:03d}.png", img_b)
                buf.seek(0)
                st.download_button(
                    "⬇️  Download ZIP", buf.getvalue(),
                    "imaginer_gallery.zip", mime="application/zip",
                    use_container_width=True, key="zip_dl"
                )

    st.markdown('<hr>', unsafe_allow_html=True)

    if not st.session_state.history:
        st.markdown(
            '<div class="glass-card fade-up" style="text-align:center;padding:64px 30px;">'
            '<div style="font-size:52px;margin-bottom:20px;opacity:0.12;">🖼️</div>'
            '<div class="section-title" style="margin-bottom:10px;">Your gallery is empty</div>'
            '<p style="color:rgba(200,240,230,0.40);font-size:14px;margin-bottom:20px;">'
            'Generate or enhance images and videos to see them here.</p>'
            '<div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">'
            '<span class="tech-pill">🎨 Try AI Generation</span>'
            '<span class="tech-pill">✨ Try Enhance</span>'
            '<span class="tech-pill-peach">🎬 Try Text to Video</span>'
            '</div></div>',
            unsafe_allow_html=True
        )
    else:
        image_items = [(i, item) for i, item in enumerate(st.session_state.history) if isinstance(item, bytes)]
        video_items = [(i, item) for i, item in enumerate(st.session_state.history) if isinstance(item, dict)]
        n_total = len(st.session_state.history)
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:22px;">'
            f'<span style="font-family:var(--font-m);font-size:12px;color:rgba(200,240,230,0.40);">'
            f'{n_total} asset{"s" if n_total!=1 else ""} · {len(image_items)} image{"s" if len(image_items)!=1 else ""} · {len(video_items)} video{"s" if len(video_items)!=1 else ""}</span>'
            f'<div style="flex:1;height:1px;background:linear-gradient(90deg,rgba(0,212,168,0.22),transparent);"></div></div>',
            unsafe_allow_html=True
        )

        if image_items:
            st.markdown(
                '<div class="section-header fade-up"><div class="section-dot"></div>'
                '<div class="section-title">Images</div><div class="section-line"></div></div>',
                unsafe_allow_html=True
            )
            for row_start in range(0, len(image_items), 3):
                cols = st.columns(3)
                for j in range(3):
                    ii = row_start + j
                    if ii < len(image_items):
                        orig_idx, img_b = image_items[ii]
                        with cols[j]:
                            st.markdown('<div class="gallery-card fade-up">', unsafe_allow_html=True)
                            st.image(img_b, use_column_width=True)
                            st.markdown(
                                f'<div class="gallery-footer"><span class="gallery-num">#{orig_idx+1:03d}</span></div>',
                                unsafe_allow_html=True
                            )
                            st.download_button("⬇️  Download", img_b, f"imaginer_{orig_idx+1:03d}.png",
                                               key=f"dl_hist_{orig_idx}", use_container_width=True)
                            st.markdown('</div>', unsafe_allow_html=True)

        if video_items:
            st.markdown('<div style="margin-top:36px;"></div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="section-header fade-up"><div class="section-dot-peach"></div>'
                '<div class="section-title">Videos</div><div class="section-line"></div></div>',
                unsafe_allow_html=True
            )
            vid_cols_list = st.columns(min(len(video_items), 2))
            for j, (orig_idx, vid_item) in enumerate(video_items):
                col = vid_cols_list[j % 2]
                with col:
                    vtype = vid_item.get("type", "video")
                    badge_label = "TEXT → VIDEO" if vtype == "text_to_video" else "PHOTO → VIDEO"
                    prompt_text = vid_item.get("prompt", "")
                    st.markdown(
                        f'<div class="video-history-card fade-up">'
                        f'<div class="video-type-badge">{badge_label}</div>',
                        unsafe_allow_html=True
                    )
                    st.video(vid_item["data"])
                    if prompt_text:
                        st.markdown(
                            f'<div style="font-size:11.5px;color:rgba(240,200,170,0.55);'
                            f'font-family:var(--font-m);margin:8px 0 4px;line-height:1.6;word-break:break-word;">'
                            f'{prompt_text[:120]}{"…" if len(prompt_text)>120 else ""}</div>',
                            unsafe_allow_html=True
                        )
                    st.download_button("⬇️  Download Video", vid_item["data"],
                                       f"imaginer_video_{orig_idx+1:03d}.mp4", mime="video/mp4",
                                       key=f"dl_vid_{orig_idx}", use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════
st.markdown('<hr>', unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;padding:10px 0 28px;">
    <span style="font-family:'JetBrains Mono',monospace;font-size:11px;
                 color:rgba(255,255,255,0.22);letter-spacing:2.5px;">
        IMAGINER STUDIO · v3.0 · PERSONAL PROJECT
    </span><br>
    <span style="font-size:12px;color:rgba(255,255,255,0.18);">✉️ arijitbera15aug@gmail.com</span>
</div>
""", unsafe_allow_html=True)