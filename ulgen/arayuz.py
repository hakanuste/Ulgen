"""Telefon uyumlu web arayüzü (tek sayfa, ek kütüphane gerektirmez).

Konuşma tanıma ve sesli okuma tarayıcının Web Speech API'si ile yapılır.
Not: Chrome ses tanımayı Google'a, Safari Apple'a gönderir.
"""

import re

_HAM = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Ülgen">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#0b0f14">
<link rel="apple-touch-icon" href="/varlik/simge.png">
<link rel="icon" href="/varlik/simge.png">
<title>Ülgen</title>
<style>
:root { color-scheme: dark; --bg:#0b0f14; --kart:#131a22; --yazi:#e6edf3; --soluk:#7d8a99;
        --vurgu:#3fb4ff; --kullanici:#1d4f7a; --kenar:#1c2630; }
* { box-sizing: border-box; }
html, body { height: 100%; margin: 0; }
body { background: var(--bg); color: var(--yazi); font-family: -apple-system, system-ui, sans-serif;
       display: flex; flex-direction: column; }
header { padding: calc(env(safe-area-inset-top) + 12px) 16px 10px; display: flex;
         align-items: center; justify-content: space-between; border-bottom: 1px solid var(--kenar); }
header h1 { font-size: 17px; margin: 0; letter-spacing: 2px; }
header .dugme { padding: 6px 8px; font-size: 12px; }
.nokta { width: 9px; height: 9px; border-radius: 50%; background: #3c4650; display: inline-block;
         margin-right: 8px; vertical-align: middle; }
.nokta.acik { background: #3fb950; box-shadow: 0 0 8px #3fb950; }
.dugme { background: var(--kart); color: var(--yazi); border: 1px solid #22303d; border-radius: 10px;
         padding: 8px 12px; font-size: 14px; }
.dugme.aktif { background: var(--vurgu); color: #021018; border-color: var(--vurgu); }
#yaklasan { font-size: 13px; color: var(--soluk); padding: 8px 16px; border-bottom: 1px solid var(--kenar); }
#yaklasan div { padding: 2px 0; }
#akis { flex: 1; overflow-y: auto; padding: 14px 14px 6px; }
.balon { max-width: 85%; padding: 10px 13px; border-radius: 16px; margin: 6px 0; line-height: 1.4;
         font-size: 16px; white-space: pre-wrap; word-wrap: break-word; }
.asistan { background: var(--kart); margin-right: auto; border-bottom-left-radius: 4px; }
.kullanici { background: var(--kullanici); margin-left: auto; border-bottom-right-radius: 4px; }
.bildirim { background: #3a2a0f; border: 1px solid #7a5a1f; margin-right: auto; }
#alt { padding: 8px 12px calc(env(safe-area-inset-bottom) + 10px); border-top: 1px solid var(--kenar);
       display: flex; gap: 8px; align-items: flex-end; }
#giris { flex: 1; resize: none; background: var(--kart); color: var(--yazi); border: 1px solid #22303d;
         border-radius: 14px; padding: 10px 12px; font-size: 16px; font-family: inherit; max-height: 120px; }
.yuvarlak { width: 44px; height: 44px; border-radius: 50%; border: 0; background: var(--kart);
            color: var(--yazi); font-size: 18px; flex-shrink: 0; }
.yuvarlak.kayit { background: #c0392b; }
.yuvarlak.gonder { background: var(--vurgu); color: #021018; }
#anahtarKutu { position: fixed; inset: 0; background: rgba(0,0,0,.7); display: none;
               align-items: center; justify-content: center; padding: 20px; }
#anahtarKutu.acik { display: flex; }
#anahtarKutu .kart { background: var(--kart); padding: 18px; border-radius: 14px; width: 100%; max-width: 360px; }
#anahtarKutu input { width: 100%; padding: 10px; border-radius: 10px; border: 1px solid #22303d;
                     background: var(--bg); color: var(--yazi); font-size: 16px; margin: 10px 0; }
#sekmeler { display: flex; gap: 4px; padding: 6px 8px; border-bottom: 1px solid var(--kenar); overflow-x: auto; }
#sekmeler button { flex: 1; white-space: nowrap; background: transparent; color: var(--soluk); border: 0;
                   padding: 8px 6px; font-size: 14px; border-radius: 8px; }
#sekmeler button.aktif { background: var(--kart); color: var(--vurgu); }
.panel { display: none; flex: 1; overflow-y: auto; padding: 12px 14px; }
.panel.acik { display: block; }
.panel h3 { margin: 14px 0 6px; font-size: 14px; color: var(--soluk); font-weight: 600; }
.satir2 { background: var(--kart); border-radius: 10px; padding: 9px 11px; margin: 6px 0; font-size: 14px; line-height: 1.4; }
.satir2 small { color: var(--soluk); display: block; }
.durumNokta { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; background: #3c4650; }
.d-alindi { background: #3fb950; } .d-almadi, .d-yanitsiz { background: #f85149; } .d-bekliyor { background: #d29922; }
.d-ertelendi { background: #3fb4ff; } .d-atlandi { background: #7d8a99; }
#baglanti { display: none; background: #5a1f1f; color: #ffd7d7; font-size: 13px; padding: 6px 16px; text-align: center; }
#baglanti.acik { display: block; }
#kodPanel { position: fixed; inset: 0; background: var(--bg); display: none; flex-direction: column;
            padding: calc(env(safe-area-inset-top) + 8px) 10px calc(env(safe-area-inset-bottom) + 8px); z-index: 5; }
#kodPanel.acik { display: flex; }
#kodPanel .satir { display: flex; gap: 6px; margin: 4px 0; flex-wrap: wrap; align-items: center; }
#kodPanel select, #kodPanel input { background: var(--kart); color: var(--yazi); border: 1px solid #22303d;
            border-radius: 8px; padding: 7px; font-size: 14px; }
#kodYazi { flex: 1; min-height: 160px; resize: none; background: #0d1319; color: #d6e2ee; border: 1px solid #22303d;
           border-radius: 10px; padding: 10px; font: 14px/1.45 ui-monospace, Menlo, monospace; tab-size: 4; }
#kodCikti { height: 28%; overflow: auto; margin: 6px 0 0; background: #05080b; border: 1px solid #22303d;
            border-radius: 10px; padding: 8px; font: 13px/1.4 ui-monospace, Menlo, monospace; white-space: pre-wrap; }

/* ---- ÜLGEN teması: gece mavisi + altın ---- */
:root { --bg:#050b1a; --kart:#0a1530; --kart2:#0e1c40; --yazi:#e9f0ff; --soluk:#8fa0c4; --vurgu:#37a8ff;
        --kullanici:#14437a; --kenar:#1b3166; --altin:#d4af5a; --altin2:#7d6428; --yesil:#3fd07a; --kirmizi:#ff6b5e; }
body { background: radial-gradient(1400px 700px at 75% -15%, #10286a 0%, var(--bg) 62%); }
.dugme { border-color: var(--kenar); }
.dugme.aktif { background: linear-gradient(180deg,#4db6ff,#2a8fe0); }
.satir2 { border: 1px solid var(--kenar); background: var(--kart); }
svg.i { width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; flex: none; }
#kok { display: flex; flex-direction: column; flex: 1; min-height: 0; }
#ana { display: flex; flex-direction: column; flex: 1; min-height: 0; position: relative; }
#yan { display: contents; }
#marka, #kullanici, #afis, #serit, #cipler .genis { display: none; }
#icerik { display: flex; flex: 1; min-height: 0; flex-direction: column; }
#sohbetKolon { display: flex; flex-direction: column; flex: 1; min-height: 0; }
#pano { display: none; }
body[data-s="gorevler"] #sohbetKolon, body[data-s="ilac"] #sohbetKolon, body[data-s="bildirim"] #sohbetKolon,
body[data-s="kasa"] #sohbetKolon, body[data-s="sistem"] #sohbetKolon { display: none; }
#saat { font-variant-numeric: tabular-nums; color: var(--altin); font-size: 13px; }
.sat { display: flex; gap: 10px; align-items: flex-end; margin: 8px 0; }
.sat.sk { flex-direction: row-reverse; }
.av { width: 38px; height: 38px; border-radius: 50%; flex: none; border: 1px solid var(--altin2); overflow: hidden;
      background: #0b1a3d center/cover; display: grid; place-items: center; font-size: 15px; color: var(--altin); }
.av.ul { background-image: url(/varlik/logo.webp); background-size: 190%; background-position: 50% 28%; }
.sat .balon { margin: 0; }
.balon small { display: block; text-align: right; font-size: 11px; color: var(--soluk); margin-top: 4px; }
.balon.asistan, .balon.kullanici { border: 1px solid var(--kenar); }
.balon.kullanici { background: linear-gradient(180deg,#17508f,#123e72); }
#cipler { display: flex; gap: 8px; padding: 6px 12px 0; overflow-x: auto; }
#cipler button { white-space: nowrap; background: rgba(14,28,64,.8); color: var(--altin); border: 1px solid var(--altin2);
                 border-radius: 999px; padding: 7px 14px; font-size: 13px; }
.dalga { display: none; align-items: center; gap: 3px; height: 30px; }
.dalga i { width: 3px; border-radius: 2px; background: var(--vurgu); height: 8px; animation: dalga 1.1s ease-in-out infinite; }
.dalga i:nth-child(2n) { animation-delay: .2s; height: 16px; } .dalga i:nth-child(3n) { animation-delay: .4s; height: 24px; }
@keyframes dalga { 50% { transform: scaleY(1.7); } }
#alt .yuvarlak { background: var(--kart2); border: 1px solid var(--kenar); }
#mikBtn { box-shadow: 0 0 0 1px var(--vurgu), 0 0 16px rgba(55,168,255,.55); background: radial-gradient(circle,#1b6fc2,#0d3a7a); }
.kartK { background: linear-gradient(180deg,var(--kart2),var(--kart)); border: 1px solid var(--kenar);
         border-radius: 16px; padding: 12px 14px; font-size: 13px; color: var(--soluk); position: relative;
         box-shadow: 0 0 18px rgba(30,70,160,.18) inset; }
.kartK .ust { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; color: var(--yazi); }
.kartK .ust b { font-size: 15px; flex: 1; }
.kartK .ust svg { color: var(--altin); }
.kartK.uyari { border-color: #8a3f32; } .kartK.uyari .ust svg { color: var(--kirmizi); }
.cubuk { height: 6px; background: #081027; border-radius: 4px; margin-top: 6px; overflow: hidden; }
.cubuk i { display: block; height: 100%; background: linear-gradient(90deg,#2a8fe0,#4db6ff); }
.rozet { display: inline-grid; place-items: center; width: 22px; height: 22px; border-radius: 6px; font-size: 12px;
         font-weight: 700; color: #fff; margin-right: 8px; vertical-align: middle; }
#pano .s { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 6px 0; font-size: 13px;
           border-top: 1px solid var(--kenar); color: var(--yazi); }
#pano .s span:last-child { color: var(--soluk); white-space: nowrap; }
#pano .ok { color: var(--yesil) !important; } #pano .bekle { color: var(--altin) !important; }
.halka { width: 92px; height: 92px; border-radius: 50%; display: grid; place-items: center; margin: 4px auto;
         background: conic-gradient(var(--yesil) var(--p,0%), #0a1530 0); }
.halka span { width: 74px; height: 74px; border-radius: 50%; background: var(--kart); display: grid; place-items: center;
              color: var(--yazi); font-size: 13px; text-align: center; line-height: 1.2; }
@media (max-width: 899px) {
  #ana { order: 1; } #yan { display: contents; }
  #sekmeler { order: 2; border-top: 1px solid var(--altin2); border-bottom: 0;
              padding: 6px 6px calc(env(safe-area-inset-bottom) + 6px); background: #050b1a; }
  #sekmeler button svg, #sekmeler .genisSadece { display: none; }
  #sekmeler button[data-s="sohbet"] { display: none; }
}
@media (min-width: 900px) {
  #kok { flex-direction: row; }
  #yan { display: flex; flex-direction: column; width: 236px; flex-shrink: 0; padding: 14px 14px 16px;
         border-right: 1px solid var(--altin2); background: linear-gradient(180deg,#071027,#050b1a);
         box-shadow: 0 0 22px rgba(201,162,74,.12); }
  #marka { display: block; text-align: center; padding: 0 0 12px; }
  #marka img { width: 100%; max-width: 190px; height: auto; filter: drop-shadow(0 0 14px rgba(70,140,255,.35)); }
  #sekmeler { flex-direction: column; border: 0; padding: 0; gap: 6px; overflow: visible; }
  #sekmeler button { flex: none; display: flex; align-items: center; gap: 12px; text-align: left; font-size: 15px;
                     padding: 11px 14px; color: var(--yazi); border: 1px solid transparent; border-radius: 12px; }
  #sekmeler button svg { color: var(--altin); }
  #sekmeler button.aktif { background: linear-gradient(90deg,#0f2a5c,#0b1d42); border-color: var(--vurgu);
                           box-shadow: 0 0 14px rgba(55,168,255,.3); }
  #kullanici { display: flex; gap: 10px; align-items: center; margin-top: auto; padding: 12px 4px 0;
               border-top: 1px solid var(--kenar); font-size: 12px; color: var(--soluk); }
  #kullanici b { color: var(--yazi); display: block; font-size: 14px; }
  #afis { display: block; position: relative; height: 132px; flex: none; border-bottom: 1px solid var(--altin2); overflow: hidden; }
  #afis svg.arka { position: absolute; inset: 0; width: 100%; height: 100%; }
  #baslikOrta { position: absolute; left: 0; right: 0; top: 14px; text-align: center; }
  #baslikOrta b { display: block; font-size: 36px; letter-spacing: 10px; color: #f1e3b5; font-weight: 700;
                  text-shadow: 0 0 18px rgba(212,175,90,.5), 0 2px 0 #7d6428; }
  #baslikOrta small { color: var(--yazi); font-size: 14px; letter-spacing: 1px; }
  #sagUst { position: absolute; right: 18px; top: 10px; display: flex; gap: 14px; align-items: center; }
  #sagUst .ik { width: 40px; height: 40px; border-radius: 50%; border: 1px solid var(--kenar); background: rgba(10,21,48,.8);
                display: grid; place-items: center; position: relative; color: var(--yazi); }
  #sagUst .ik em { position: absolute; top: -3px; right: -3px; background: var(--kirmizi); color: #fff; font-style: normal;
                   font-size: 10px; border-radius: 9px; min-width: 16px; text-align: center; padding: 1px 3px; }
  #sagUst .ik i { position: absolute; right: 2px; bottom: 2px; width: 9px; height: 9px; border-radius: 50%; background: #3c4650; }
  #sagUst .ik i.acik { background: var(--yesil); box-shadow: 0 0 6px var(--yesil); }
  #saatKutu { text-align: right; } #saatKutu small { display: block; color: var(--yazi); font-size: 13px; }
  #saatKutu b { font-size: 34px; letter-spacing: 1px; }
  header { position: absolute; left: 12px; top: 10px; z-index: 2; border: 0; padding: 0; gap: 8px; justify-content: flex-start; }
  header h1, header #saat { display: none; }
  #serit { display: grid; grid-template-columns: repeat(5, minmax(150px, 1fr)); gap: 12px; padding: 14px 16px 4px; }
  #icerik { flex-direction: row; gap: 14px; padding: 12px 16px 14px; }
  #sohbetKolon { flex: 1 1 50%; border: 1px solid var(--kenar); border-radius: 18px; background: rgba(10,21,48,.55); overflow: hidden; }
  body[data-s="ana"] #pano { display: flex; gap: 14px; flex: 0 0 min(56%, 700px); overflow-y: auto; }
  body[data-s="ana"] #sohbetKolon, body[data-s="sohbet"] #sohbetKolon { display: flex; }
  #pano > div { flex: 1; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
  .panel { flex: 1; }
  #cipler .genis { display: inline; }
}
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute"><defs>
<symbol id="i-ev" viewBox="0 0 24 24"><path d="M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/></symbol>
<symbol id="i-sohbet" viewBox="0 0 24 24"><path d="M4 5h16v11H9l-5 4z"/><path d="M8 9h8M8 12h5"/></symbol>
<symbol id="i-gorev" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 12l3 3 5-6"/></symbol>
<symbol id="i-kalp" viewBox="0 0 24 24"><path d="M12 20s-8-4.6-8-10.5A4.5 4.5 0 0 1 12 7a4.5 4.5 0 0 1 8 2.5C20 15.4 12 20 12 20z"/></symbol>
<symbol id="i-hap" viewBox="0 0 24 24"><path d="M8.5 15.5l7-7a3.5 3.5 0 0 1 5 5l-7 7a3.5 3.5 0 0 1-5-5z"/><path d="M12 12l3 3"/></symbol>
<symbol id="i-kasa" viewBox="0 0 24 24"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></symbol>
<symbol id="i-zil" viewBox="0 0 24 24"><path d="M6 17v-6a6 6 0 0 1 12 0v6l2 2H4z"/><path d="M10 21h4"/></symbol>
<symbol id="i-ayar" viewBox="0 0 24 24"><path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/></symbol>
<symbol id="i-takvim" viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/></symbol>
<symbol id="i-ekran" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></symbol>
<symbol id="i-tel" viewBox="0 0 24 24"><rect x="7" y="3" width="10" height="18" rx="2"/><path d="M11 18h2"/></symbol>
<symbol id="i-katman" viewBox="0 0 24 24"><path d="M12 3l9 5-9 5-9-5z"/><path d="M3 12l9 5 9-5"/><path d="M3 16l9 5 9-5"/></symbol>
<symbol id="i-sag" viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></symbol>
<symbol id="i-mik" viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></symbol>
<symbol id="i-gonder" viewBox="0 0 24 24"><path d="M4 12l16-8-6 16-3-7z"/></symbol>
</defs></svg>
<div id="kok">
<aside id="yan">
  <div id="marka"><img src="/varlik/logo.webp" alt="Ülgen"></div>
  <nav id="sekmeler">
  <button class="aktif" data-s="ana" onclick="sekme('ana')"><svg class="i"><use href="#i-ev"/></svg>Ana Sayfa</button>
  <button data-s="sohbet" onclick="sekme('sohbet')"><svg class="i"><use href="#i-sohbet"/></svg>Sohbet</button>
  <button data-s="gorevler" onclick="sekme('gorevler')"><svg class="i"><use href="#i-gorev"/></svg>Görevler</button>
  <button data-s="ilac" onclick="sekme('ilac')"><svg class="i"><use href="#i-kalp"/></svg>Sağlık &amp; İlaç</button>
  <button data-s="kasa" onclick="sekme('kasa')"><svg class="i"><use href="#i-kasa"/></svg>Özel Kasa</button>
  <button data-s="bildirim" onclick="sekme('bildirim')"><svg class="i"><use href="#i-zil"/></svg>Bildirim</button>
  <button data-s="sistem" onclick="sekme('sistem')"><svg class="i"><use href="#i-ayar"/></svg>Sistem</button>
  </nav>
  <div id="kullanici"><span class="av ul"></span><div><b>Hakan Üste</b><span id="surumYazi">ÜLGEN</span> <span id="nokta2" class="nokta"></span></div></div>
</aside>
<div id="ana">
<div id="afis">
  <svg class="arka" viewBox="0 0 1200 132" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs><linearGradient id="gk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#071236"/><stop offset="1" stop-color="#14306f"/></linearGradient>
    <radialGradient id="ay" cx=".5" cy=".5" r=".5"><stop offset=".6" stop-color="#e9f3ff"/><stop offset="1" stop-color="#a9c8ff"/></radialGradient>
    <radialGradient id="ayis" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#6ea8ff" stop-opacity=".55"/><stop offset="1" stop-color="#6ea8ff" stop-opacity="0"/></radialGradient></defs>
    <rect width="1200" height="132" fill="url(#gk)"/>
    <g fill="#cfe0ff"><circle cx="120" cy="22" r="1.2"/><circle cx="260" cy="48" r="1"/><circle cx="330" cy="14" r="1.4"/><circle cx="470" cy="38" r="1"/><circle cx="560" cy="18" r="1.2"/><circle cx="700" cy="30" r="1"/><circle cx="790" cy="12" r="1.4"/><circle cx="905" cy="40" r="1"/><circle cx="60" cy="60" r="1"/><circle cx="640" cy="60" r="1"/><circle cx="1010" cy="16" r="1.2"/><circle cx="1130" cy="50" r="1"/><circle cx="410" cy="70" r="1"/></g>
    <circle cx="985" cy="62" r="92" fill="url(#ayis)"/><circle cx="985" cy="62" r="46" fill="url(#ay)"/>
    <g fill="#c4d6f5" opacity=".5"><circle cx="970" cy="50" r="9"/><circle cx="1000" cy="74" r="7"/><circle cx="975" cy="82" r="5"/></g>
    <path d="M0 132V96l60-26 50 22 70-48 60 40 80-32 70 50 90-44 80 40 90-52 70 46 110-30 70 36 120-40 80 30v62z" fill="#0c1d4d"/>
    <path d="M0 132V112l90-30 70 28 110-34 90 36 110-30 100 34 130-40 100 34 110-28 90 24 100-30v62z" fill="#081334"/>
    <path d="M1052 132l12-28 10-6-4-14 8-6 6-12 5 8 8 2 4 10 12 6 6 14 8 8-6 18z" fill="#04091c"/>
    <path d="M1078 74l-2-12 7-8 6-1 4-8 2 7 8 3-3 6 5 5-6 2-3 8-6-2-5 4-4-3z" fill="#04091c"/>
  </svg>
  <div id="baslikOrta"><b>ÜLGEN</b><small>Kişisel Yapay Zekâ Yardımcı</small></div>
  <div id="sagUst">
    <div class="ik" onclick="sekme('bildirim')" style="cursor:pointer"><svg class="i"><use href="#i-zil"/></svg><em id="zilSayi" style="display:none">0</em></div>
    <div class="ik" title="Mac sunucusu"><svg class="i"><use href="#i-ekran"/></svg><i id="macNokta"></i></div>
    <div class="ik" title="iPhone (son 24 saatte bağlandı mı)"><svg class="i"><use href="#i-tel"/></svg><i id="telNokta"></i></div>
    <div id="saatKutu"><small id="tarihYazi"></small><b id="saatYazi"></b></div>
  </div>
</div>
<header>
  <h1><span id="nokta" class="nokta"></span>ÜLGEN</h1>
  <span id="saat"></span>
  <button class="dugme" onclick="kodAcPencere()">&lt;/&gt; Kod</button>
  <button id="sesBtn" class="dugme aktif" onclick="sesDegistir()">Ses: açık</button>
  <button id="surekliBtn" class="dugme" onclick="surekliDegistir()">Sürekli dinle: kapalı</button>
</header>
<div id="kodPanel">
  <div class="satir">
    <b style="flex:1">Kod penceresi</b>
    <button class="dugme" onclick="kodKapat()">Kapat ✕</button>
  </div>
  <div class="satir">
    <select id="kodDosya" onchange="kodAc()"><option value="">Yeni dosya</option></select>
    <input id="kodAd" placeholder="ad.py" style="width:120px" autocapitalize="off" autocorrect="off">
    <select id="kodDil"><option value="python">Python</option><option value="node">Node</option>
      <option value="bash">Bash</option></select>
  </div>
  <textarea id="kodYazi" spellcheck="false" autocapitalize="off" autocorrect="off" autocomplete="off"
    placeholder="Kodunuzu buraya yazın" onkeydown="kodTus(event)"></textarea>
  <div class="satir">
    <button class="dugme aktif" id="kodCalistirBtn" onclick="kodCalistir()">▶ Çalıştır</button>
    <button class="dugme" onclick="kodKaydet()">Kaydet</button>
    <button class="dugme" onclick="kodUlgenSor()">Ülgen'e sor</button>
    <span id="kodDurum" style="font-size:12px;color:var(--soluk)"></span>
  </div>
  <pre id="kodCikti">Çıktı burada görünür. Kod sizin yetkinizle çalışır (kum havuzu değildir).</pre>
</div>
<div id="baglanti">Bağlantı koptu; yeniden deneniyor…</div>
<div id="serit"></div>
<div id="icerik">
<div id="pGorevler" class="panel"></div>
<div id="pIlac" class="panel"></div>
<div id="pBildirim" class="panel"></div>
<div id="pKasa" class="panel"></div>
<div id="pSistem" class="panel"></div>
<section id="sohbetKolon">
<div id="yaklasan"></div>
<div id="beyin" style="font-size:12px;color:var(--soluk);padding:2px 16px"></div>
<div id="akis"></div>
<div id="cipler">
  <button onclick="cipSec('Derinlemesine düşün: ')">Derin Düşün</button>
  <button onclick="cipSec('Araştır: ')">Araştır</button>
  <button onclick="cipSec('Planla: ')">Planla</button>
  <button onclick="cipSec('Hatırlat: ')">Hatırlat</button>
  <button onclick="cipSec('Not al: ')">Not Al</button>
  <button onclick="kodAcPencere()">Kod</button>
</div>
<div id="alt">
    <textarea id="giris" rows="1" placeholder="Yazın ya da konuşun" onkeydown="tusla(event)"></textarea>
  <span class="dalga" id="dalga"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></span>
  <button id="mikBtn" class="yuvarlak" onclick="mikrofon()" title="Konuş"><svg class="i"><use href="#i-mik"/></svg></button>
  <button class="yuvarlak gonder" onclick="gonder()" title="Gönder">➤</button>
</div>
</section>
<aside id="pano"><div id="pano1"></div><div id="pano2"></div></aside>
</div>
</div></div>
<div id="anahtarKutu">
  <div class="kart">
    <b>Cihaz belirteci</b>
    <p style="color:var(--soluk);font-size:14px">Uzaktan bağlanıyorsunuz. Mac'te üretilen cihaz belirtecini girin.</p>
    <input id="anahtarGiris" type="password" placeholder="Belirteç">
    <button class="dugme aktif" style="width:100%" onclick="anahtarKaydet()">Kaydet</button>
  </div>
</div>
<script>
const yerel = ["127.0.0.1", "localhost", "[::1]"].includes(location.hostname);
let anahtar = localStorage.getItem("asistan_anahtar") || "";
let sesli = true;
let taninan = null;

function anahtarIste() {
  if (!yerel && !anahtar) document.getElementById("anahtarKutu").classList.add("acik");
}

function anahtarKaydet() {
  anahtar = document.getElementById("anahtarGiris").value.trim();
  localStorage.setItem("asistan_anahtar", anahtar);
  document.getElementById("anahtarKutu").classList.remove("acik");
  ozetYukle();
}

async function istek(yol, veri) {
  const s = { method: veri ? "POST" : "GET", headers: {} };
  if (anahtar) s.headers["Authorization"] = "Bearer " + anahtar;
  if (veri) { s.headers["Content-Type"] = "application/json"; s.body = JSON.stringify(veri); }
  const c = await fetch(yol, s);
  if (c.status === 401 && yerel) {
    throw new Error("Oturum yok: Launchpad'deki Ülgen simgesiyle açın.");
  }
  if (c.status === 401) {
    localStorage.removeItem("asistan_anahtar");
    anahtar = "";
    anahtarIste();
    throw new Error("Belirteç hatalı, iptal edilmiş ya da eksik.");
  }
  return c.json();
}

function balonEkle(metin, tur) {
  const sat = document.createElement("div");
  sat.className = "sat " + (tur === "kullanici" ? "sk" : "sa");
  const av = document.createElement("span");
  av.className = "av" + (tur === "kullanici" ? "" : " ul");
  if (tur === "kullanici") av.textContent = "H";
  const d = document.createElement("div");
  d.className = "balon " + tur;
  d.appendChild(document.createTextNode(metin));
  const z = document.createElement("small");
  z.textContent = new Date().toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
  d.appendChild(z);
  sat.appendChild(av); sat.appendChild(d);
  const a = document.getElementById("akis");
  a.appendChild(sat);
  a.scrollTop = a.scrollHeight;
}

function cipSec(onek) {
  const g = document.getElementById("giris");
  g.value = onek; g.focus();
}

function konus(metin) {
  if (!sesli || !("speechSynthesis" in window)) return;
  speechSynthesis.cancel();
  // Uzun metinler (sabah raporu) tek parça okununca tarayıcıda kesilir;
  // bu yüzden cümle cümle okunur.
  const parcalar = metin.replace(/\s+/g, " ").match(/[^.!?]+[.!?]*/g) || [metin];
  for (const p of parcalar) {
    if (!p.trim()) continue;
    const u = new SpeechSynthesisUtterance(p.trim());
    u.lang = "tr-TR";
    u.rate = 0.95;
    u.pitch = 0.8;
    speechSynthesis.speak(u);
  }
}

function sesDegistir() {
  sesli = !sesli;
  const b = document.getElementById("sesBtn");
  b.textContent = "Ses: " + (sesli ? "açık" : "kapalı");
  b.classList.toggle("aktif", sesli);
}

async function gonder() {
  const g = document.getElementById("giris");
  const m = g.value.trim();
  g.value = "";
  gonderMetin(m);
}

async function gonderMetin(m) {
  if (!m) return;
  balonEkle(m, "kullanici");
  try {
    const c = await istek("/sohbet", { metin: m });
    balonEkle(c.yanit, "asistan");
    beyinEtiketi(c.beyin);
    konus(c.yanit);
    ozetYukle();
  } catch (e) {
    balonEkle(e.message, "asistan");
  }
}

function beyinEtiketi(ad) {
  document.getElementById("beyin").textContent = ad ? "beyin: " + ad : "";
}

function tusla(e) {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); gonder(); }
}

let surekli = false;

function dinleyiciGorunum(acik) {
  document.getElementById("mikBtn").classList.toggle("kayit", acik);
  const dg = document.getElementById("dalga"); if (dg) dg.style.display = acik ? "flex" : "none";
}

function dinleyiciBaslat() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { balonEkle("Bu tarayıcıda ses tanıma yok.", "asistan"); return; }
  const r = new SR();
  r.lang = "tr-TR";
  r.interimResults = false;
  r.continuous = surekli;
  r.onresult = (e) => {
    const son = e.results[e.results.length - 1];
    if (!son.isFinal) return;
    const metin = son[0].transcript.trim();
    if (!surekli) { gonderMetin(metin); return; }
    const eslesme = metin.match(/^(ülgen|ulgen)[,.\s]*(.*)$/i);
    if (!eslesme) return;
    if (!eslesme[2]) { konus("Efendim?"); return; }
    gonderMetin(eslesme[2]);
  };
  r.onend = () => {
    taninan = null;
    if (surekli) setTimeout(dinleyiciBaslat, 400);
    else dinleyiciGorunum(false);
  };
  r.onerror = () => {
    taninan = null;
    if (!surekli) dinleyiciGorunum(false);
  };
  taninan = r;
  dinleyiciGorunum(true);
  r.start();
}

function mikrofon() {
  if (taninan) { surekli = false; taninan.stop(); return; }
  surekli = false;
  dinleyiciBaslat();
}

function surekliDegistir() {
  const b = document.getElementById("surekliBtn");
  surekli = !surekli;
  b.textContent = "Sürekli dinle: " + (surekli ? "açık" : "kapalı");
  b.classList.toggle("aktif", surekli);
  if (surekli) {
    if (!taninan) dinleyiciBaslat();
  } else if (taninan) {
    taninan.stop();
  }
}

let sonBildirim = 0;

// Her düğme YALNIZCA kendi dozunun kimliğini gönderir (D12 gibi).
function dozDugmeleri(doz) {
  const kap = document.createElement("div");
  kap.className = "balon bildirim";
  [["Aldım", "alindi"], ["Ertele 15 dk", "ertele"], ["Almadım", "almadi"], ["Atla", "atlandi"]].forEach(([ad, yanit]) => {
    const d = document.createElement("button");
    d.className = "dugme";
    d.style.margin = "3px";
    d.textContent = ad;
    d.onclick = async () => {
      kap.querySelectorAll("button").forEach(x => x.disabled = true);
      try {
        const c = await istek("/ilac/yanit", { doz: doz, yanit: yanit, dk: 15 });
        balonEkle(c.yanit, "asistan");
        kap.remove();
      } catch (e) { balonEkle(e.message, "asistan"); }
    };
    kap.appendChild(d);
  });
  const a = document.getElementById("akis");
  a.appendChild(kap);
  a.scrollTop = a.scrollHeight;
}

async function bildirimleriAl() {
  try {
    const liste = await istek("/bildirimler?son=" + sonBildirim);
    for (const b of liste) {
      sonBildirim = Math.max(sonBildirim, b.id);
      balonEkle("⏰ " + b.metin, "bildirim");
      gecmisBildirim.push({ metin: b.metin, saat: new Date().toLocaleTimeString("tr-TR") });
      if (aktifSekme === "bildirim") bildirimCiz();
      if (b.eylem && b.eylem.tur === "doz") dozDugmeleri(b.eylem.doz);
      konus(b.metin);
    }
    if (liste.length && navigator.vibrate) navigator.vibrate([200, 100, 200]);
  } catch (e) { /* sessizce geç */ }
}

async function ozetYukle() {
  try {
    const o = await istek("/ozet");
    const y = document.getElementById("yaklasan");
    y.innerHTML = "";
    if (!o.hatirlaticilar.length) y.textContent = "Bekleyen hatırlatıcı yok.";
    o.hatirlaticilar.forEach(h => {
      const d = document.createElement("div");
      d.textContent = h.zaman.slice(8, 10) + "." + h.zaman.slice(5, 7) + " " + h.zaman.slice(11) + "  " + h.mesaj;
      y.appendChild(d);
    });
    document.getElementById("nokta").classList.add("acik");
    const d = await istek("/durum");
    beyinEtiketi(d.beyin);
  } catch (e) {
    document.getElementById("nokta").classList.remove("acik");
  }
}


// ---- Özel Kasa (Face ID) -------------------------------------------------
const b64u = b => btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const b64coz = t => Uint8Array.from(atob(t.replace(/-/g, "+").replace(/_/g, "/")), c => c.charCodeAt(0));
const PRF_TUZ = new TextEncoder().encode("ulgen-kasa-prf-v1-tuz-32-bayt-uzun!!").slice(0, 32);

async function faceIdAl(kapsam, cred) {
  const g = await istek("/kasa/passkey/giris-baslat", { kapsam });
  if (g.hata) throw new Error(g.hata);
  const a = await navigator.credentials.get({ publicKey: {
    challenge: b64coz(g.challenge), rpId: location.hostname, userVerification: "required",
    allowCredentials: g.izinli.map(i => ({ type: "public-key", id: b64coz(i) })),
    extensions: { prf: { eval: { first: PRF_TUZ } } } } });
  const prf = (a.getClientExtensionResults().prf || {}).results;
  return { yontem: "passkey", kimlik: g.kimlik, prf: prf ? b64u(prf.first) : "",
    veri: { id: b64u(a.rawId), clientDataJSON: b64u(a.response.clientDataJSON),
      authenticatorData: b64u(a.response.authenticatorData), signature: b64u(a.response.signature) } };
}

async function faceIdKaydet(parola) {
  const k = await istek("/kasa/passkey/kayit-baslat", {});
  const c = await navigator.credentials.create({ publicKey: {
    rp: { name: "Ülgen", id: location.hostname },
    user: { id: crypto.getRandomValues(new Uint8Array(16)), name: "ulgen", displayName: "Ülgen" },
    challenge: b64coz(k.challenge), pubKeyCredParams: [{ type: "public-key", alg: -7 }],
    authenticatorSelection: { authenticatorAttachment: "platform", residentKey: "required", userVerification: "required" },
    extensions: { prf: {} } } });
  const r = await istek("/kasa/passkey/kayit-bitir", { kimlik: k.kimlik, veri: {
    clientDataJSON: b64u(c.response.clientDataJSON), attestationObject: b64u(c.response.attestationObject) } });
  if (r.hata) throw new Error(r.hata);
  const a = await faceIdAl("oku:__bagla__");  // PRF çıktısını almak için ikinci Face ID
  if (!a.prf) throw new Error("Bu cihaz/tarayıcı PRF'yi desteklemiyor; Face ID yalnız onay verir.");
  const b = await istek("/kasa/passkey/bagla", { cred: r.cred, prf: a.prf, parola });
  if (b.hata) throw new Error(b.hata);
}

let kasaGoster = null;
async function kasaCiz() {
  const p = document.getElementById("pKasa");
  const d = await istek("/kasa/durum");
  p.replaceChildren();
  baslik(p, "Özel Kasa");
  const not = (m) => ekle(p, m);
  const girdi = (tip, yer) => { const i = document.createElement("input"); i.type = tip; i.placeholder = yer; i.style.cssText = "width:100%;margin:4px 0"; p.appendChild(i); return i; };
  const dugme = (m, f) => { const b = document.createElement("button"); b.className = "dugme"; b.textContent = m; b.style.margin = "4px 4px 4px 0";
    b.onclick = async () => { try { await f(); } catch (e) { alert(e.message || e); } }; p.appendChild(b); return b; };
  if (!d.kurulu) {
    not("Kasa henüz kurulu değil. Parolanız en az 8 karakter olmalı.");
    const pr = girdi("password", "Kasa parolası");
    dugme("Kasayı kur", async () => { const r = await istek("/kasa/kur", { parola: pr.value });
      if (r.hata) throw new Error(r.hata);
      alert("KURTARMA KODUNUZ (bir kez gösterilir, yazıp saklayın):\n\n" + r.kurtarma_kodu +
        "\n\nMac'teki ~/ÜlgenVeri/kurtarma.paket dosyasını da Mac dışında saklayın."); kasaCiz(); });
    return;
  }
  not("Yapay zekâ kasanın içeriğini göremez; yalnız istek açabilir. Açma için Face ID ya da parola gerekir.");
  if (location.hostname.match(/^[0-9.]+$/) && d.passkey >= 0) {
    ekle(p, "Face ID için alan adı gerekir. Şu adresten açın:", "https://" + d.rp_onerisi + ":" + (location.port || 8443));
  }
  ekle(p, "Face ID anahtarı: " + (d.passkey ? d.passkey + " kayıtlı" : "yok"));
  const pw = girdi("password", "Kasa parolası (ekleme/bağlama için)");
  if (!d.passkey) dugme("Face ID'yi bağla", async () => { await faceIdKaydet(pw.value); kasaCiz(); });
  baslik(p, "Bekleyen istekler");
  if (!d.istekler.length) ekle(p, "Yok");
  for (const i of d.istekler) {
    const ad = i.kapsam.replace(/^oku:/, "");
    const e = ekle(p, "#" + i.id + " · " + ad + " isteniyor");
    const b = document.createElement("button"); b.className = "dugme aktif"; b.textContent = "Face ID ile onayla";
    b.onclick = async () => { try { await kasaOku(ad, await faceIdAl("oku:" + ad), i.id); } catch (x) { alert(x.message || x); } };
    e.appendChild(b);
  }
  baslik(p, "Öğeler");
  if (!d.adlar.length) ekle(p, "Kasada öğe yok");
  for (const ad of d.adlar) {
    const e = ekle(p, ad);
    const f = document.createElement("button"); f.className = "dugme"; f.textContent = "Face ID";
    f.onclick = async () => { try { await kasaOku(ad, await faceIdAl("oku:" + ad)); } catch (x) { alert(x.message || x); } };
    const q = document.createElement("button"); q.className = "dugme"; q.textContent = "Parola";
    q.onclick = async () => { try { await kasaOku(ad, { yontem: "parola", parola: pw.value }); } catch (x) { alert(x.message || x); } };
    e.appendChild(f); e.appendChild(q);
  }
  kasaGoster = document.createElement("pre"); kasaGoster.style.whiteSpace = "pre-wrap"; p.appendChild(kasaGoster);
  baslik(p, "Yeni öğe");
  const ad = girdi("text", "Ad (şifresiz saklanır; gizli bilgi yazmayın)");
  const ic = document.createElement("textarea"); ic.placeholder = "İçerik"; ic.rows = 3; ic.style.cssText = "width:100%"; p.appendChild(ic);
  dugme("Kasaya ekle", async () => { const r = await istek("/kasa/ekle", { ad: ad.value, icerik: ic.value, yontem: "parola", parola: pw.value });
    if (r.hata) throw new Error(r.hata); ic.value = ""; pw.value = ""; kasaCiz(); });
  baslik(p, "Parolamı unuttum");
  const yeni = girdi("password", "Yeni parola (en az 8)");
  dugme("Face ID ile parolayı sıfırla", async () => { const a = await faceIdAl("parola-sifirla"); a.yeni = yeni.value;
    const r = await istek("/kasa/parola-sifirla", a); if (r.hata) throw new Error(r.hata); alert(r.yanit); yeni.value = ""; });
  dugme("Face ID ile yeni parolalı yedek al", async () => { const a = await faceIdAl("yedek-al"); a.yeni = yeni.value;
    const r = await istek("/kasa/yedek", a); if (r.hata) throw new Error(r.hata); alert("Yedek: " + r.dosya); });
}

async function kasaOku(ad, acma, istekNo) {
  const r = await istek("/kasa/oku", Object.assign({ ad }, acma, istekNo ? { istek: istekNo } : {}));
  if (r.hata) throw new Error(r.hata);
  kasaGoster.textContent = ad + ":\n" + r.icerik;   // yalnız ekranda; 20 sn sonra silinir
  setTimeout(() => { kasaGoster.textContent = ""; }, 20000);
}

// ---- sekmeler ------------------------------------------------------------
const paneller = { gorevler: "pGorevler", ilac: "pIlac", bildirim: "pBildirim", kasa: "pKasa", sistem: "pSistem" };
const gecmisBildirim = [];
let aktifSekme = "ana";

const sohbetli = ad => ad === "ana" || ad === "sohbet";
function sekme(ad) {
  if (window.innerWidth < 900 && ad === "sohbet") ad = "ana";
  aktifSekme = ad;
  document.body.dataset.s = ad;
  document.querySelectorAll("#sekmeler button").forEach(b => b.classList.toggle("aktif", b.dataset.s === ad));
  for (const [k, id] of Object.entries(paneller)) document.getElementById(id).classList.toggle("acik", k === ad);
  if (sohbetli(ad)) panoYenile(); else panelYenile(ad);
}
document.body.dataset.s = "ana";

// ---- pano (geniş ekran) ------------------------------------------------------
const SAG = '<svg class="i"><use href="#i-sag"/></svg>';
function kartK(ust, baslik, govde, ikon, ek, git) {
  const d = document.createElement("div"); d.className = "kartK" + (ek || "");
  const u = document.createElement("div"); u.className = "ust";
  u.innerHTML = '<svg class="i"><use href="#i-' + ikon + '"/></svg>';
  const b = document.createElement("b"); b.textContent = baslik; u.appendChild(b);
  if (git) { u.insertAdjacentHTML("beforeend", SAG); d.style.cursor = "pointer"; d.onclick = () => sekme(git); }
  d.appendChild(u);
  (Array.isArray(govde) ? govde : [govde]).forEach(g => {
    if (g instanceof Node) d.appendChild(g);
    else if (g) { const p = document.createElement("div"); p.textContent = g; d.appendChild(p); }
  });
  ust.appendChild(d); return d;
}
function cubuk(oran) { const c = document.createElement("div"); c.className = "cubuk";
  const i = document.createElement("i"); i.style.width = Math.max(0, Math.min(100, oran)) + "%"; c.appendChild(i); return c; }
function satirS(kap, a, b, sinif, rozet) { const r = document.createElement("div"); r.className = "s";
  const x = document.createElement("span");
  if (rozet) { const z = document.createElement("span"); z.className = "rozet"; z.style.background = rozet[1]; z.textContent = rozet[0]; x.appendChild(z); }
  x.appendChild(document.createTextNode(a)); const y = document.createElement("span"); y.textContent = b;
  if (sinif) y.className = sinif; r.appendChild(x); r.appendChild(y); kap.appendChild(r); }
const ROZET = { gemini: ["G", "#3b7de0"], nvidia: ["N", "#5aa100"], groq: ["g", "#e0442a"], mistral: ["M", "#f08a1c"],
                openrouter: ["O", "#5a6478"], ollama: ["O", "#7a8499"], "llama.cpp": ["L", "#7a8499"] };
function rozetBul(ad) { const k = ad.toLowerCase(); for (const a in ROZET) if (k.indexOf(a) >= 0) return ROZET[a]; return [ad[0] || "?", "#5a6478"]; }

async function panoYenile() {
  if (window.innerWidth < 900) return;
  try {
    const [g, il, sis] = await Promise.all([istek("/gorevler"), istek("/ilac/bugun"), istek("/sistem")]);
    const serit = document.getElementById("serit"); serit.replaceChildren();
    const alinan = il.filter(x => x.durum === "alindi" || x.durum === "tamamlandi").length;
    const bek = il.filter(x => x.durum === "bekliyor" || x.durum === "ertelendi" || x.durum === "yanitsiz").length;
    const acik = g.gorev.length;
    const yuzde = il.length ? Math.round(100 * alinan / il.length) : 0;
    const k0 = kartK(serit, "Günün Özeti", [acik + " görev · " + il.length + " ilaç · " + g.randevu.length + " randevu"], "takvim", "", "gorevler");
    k0.appendChild(cubuk(yuzde)); const yz = document.createElement("div"); yz.style.cssText = "text-align:right;font-size:12px"; yz.textContent = "%" + yuzde + " ilaç alındı"; k0.appendChild(yz);
    kartK(serit, "İlaçlar", bek ? bek + " bekleyen doz" : "Bekleyen doz yok", "hap", bek ? " uyari" : "", "ilac");
    kartK(serit, "Görevler", acik ? acik + " tamamlanmamış" : "Açık görev yok", "gorev", acik ? " uyari" : "", "gorevler");
    kartK(serit, "Sağlık", ["Adım, nabız, uyku:", "iPhone Sağlık köprüsü (Aşama 7)"], "kalp", "", "ilac");
    kartK(serit, "Sistem", ["ÜLGEN " + sis.surum + " • " + (sis.butunluk.saglam ? "Çalışıyor" : "SORUNLU"),
      "Veritabanı: " + (sis.veritabani_sifreli ? "şifreli" : "ŞİFRESİZ")], "katman", sis.veritabani_sifreli ? "" : " uyari", "sistem");
    document.getElementById("surumYazi").textContent = "ÜLGEN " + sis.surum;
    document.getElementById("macNokta").classList.add("acik");
    const gun = Date.now() / 1000 - 86400;
    const tel = sis.cihazlar.some(c => !c.iptal && c.ad !== "Mac tarayıcı" && c.son_kullanim && Date.parse(c.son_kullanim.replace(" ", "T")) / 1000 > gun);
    document.getElementById("telNokta").classList.toggle("acik", tel);
    const p1 = document.getElementById("pano1"), p2 = document.getElementById("pano2");
    p1.replaceChildren(); p2.replaceChildren();
    const k1 = kartK(p1, "İlaç Takvimi", [], "hap", "", "ilac");
    if (!il.length) satirS(k1, "Bugün doz yok", "");
    il.forEach(x => satirS(k1, "D" + x.id + " – " + x.ilac_ad, x.planli.slice(11, 16) + " " + durumYazi[x.durum].split(" ")[0],
      x.durum === "alindi" ? "ok" : (x.durum === "bekliyor" ? "bekle" : "")));
    const k2 = kartK(p1, "Görevler", [], "gorev", "", "gorevler");
    if (!g.gorev.length) satirS(k2, "Açık görev yok", "");
    g.gorev.slice(0, 6).forEach(x => satirS(k2, x.baslik, x.zaman ? x.zaman.slice(5, 16) : "Zamansız"));
    const k5 = kartK(p1, "Sağlık Durumu", [], "kalp");
    const h = document.createElement("div"); h.className = "halka"; h.style.setProperty("--p", "0%");
    h.innerHTML = "<span>Adım<br>—</span>"; k5.appendChild(h);
    const n = document.createElement("div"); n.style.cssText = "text-align:center;font-size:12px"; n.textContent = "iPhone Sağlık köprüsü kurulunca dolar"; k5.appendChild(n);
    const k3 = kartK(p2, "Yapay Zekâ Modelleri", [], "katman");
    sis.kota.forEach(t => satirS(k3, t.ad, t.engelli ? "Engelli" : "Hazır", t.engelli ? "" : "ok", rozetBul(t.ad)));
    const k4 = kartK(p2, "Sistem Durumu", [], "ayar");
    const d = sis.donanim || {};
    if (d.cpu !== undefined) { satirS(k4, "CPU", Math.round(d.cpu) + "%"); k4.appendChild(cubuk(d.cpu)); }
    if (d.ram_toplam) { satirS(k4, "RAM", d.ram_kullanilan + " / " + d.ram_toplam + " GB"); k4.appendChild(cubuk(100 * d.ram_kullanilan / d.ram_toplam)); }
    if (d.disk_toplam) { satirS(k4, "Disk", d.disk_kullanilan + " / " + d.disk_toplam + " GB"); k4.appendChild(cubuk(100 * d.disk_kullanilan / d.disk_toplam)); }
    const ok = document.createElement("div"); ok.style.cssText = "margin-top:8px;color:var(--yesil);font-size:13px";
    ok.textContent = sis.butunluk.saglam ? "✓ Tüm sistemler normal çalışıyor." : "! Veritabanı bütünlüğü sorunlu"; k4.appendChild(ok);
  } catch (e) { /* oturum yoksa istek() zaten bildirir */ }
}
function saatYaz() {
  const d = new Date();
  const t = d.toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric", weekday: "long" });
  const sy = d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
  document.getElementById("saat").textContent = t + "  " + sy;
  document.getElementById("tarihYazi").textContent = t;
  document.getElementById("saatYazi").textContent = sy;
  const z = document.getElementById("zilSayi");
  z.textContent = gecmisBildirim.length; z.style.display = gecmisBildirim.length ? "" : "none";
}
saatYaz(); setInterval(saatYaz, 15000); setInterval(() => { if (sohbetli(aktifSekme)) panoYenile(); }, 30000);
setTimeout(panoYenile, 400);

function ekle(kap, metin, kucuk) {
  const d = document.createElement("div");
  d.className = "satir2";
  d.textContent = metin;
  if (kucuk) { const k = document.createElement("small"); k.textContent = kucuk; d.appendChild(k); }
  kap.appendChild(d);
  return d;
}

function baslik(kap, m) { const h = document.createElement("h3"); h.textContent = m; kap.appendChild(h); }

async function panelYenile(ad) {
  try {
    if (ad === "kasa") await kasaCiz();
    if (ad === "gorevler") await gorevlerCiz();
    else if (ad === "ilac") await ilacCiz();
    else if (ad === "bildirim") bildirimCiz();
    else if (ad === "sistem") await sistemCiz();
  } catch (e) { /* bağlantı uyarısı zaten gösteriliyor */ }
}

async function gorevlerCiz() {
  const g = await istek("/gorevler");
  const k = document.getElementById("pGorevler");
  k.innerHTML = "";
  baslik(k, "Görevler");
  if (!g.gorev.length) ekle(k, "Açık görev yok.");
  g.gorev.forEach(x => {
    const d = ekle(k, "#" + x.id + " " + x.baslik, x.zaman || "zamansız");
    const b = document.createElement("button");
    b.className = "dugme"; b.style.marginTop = "6px"; b.textContent = "Tamamlandı";
    b.onclick = async () => { b.disabled = true; await istek("/gorev/bitir", { id: x.id }); gorevlerCiz(); };
    d.appendChild(b);
  });
  baslik(k, "Randevular");
  if (!g.randevu.length) ekle(k, "Randevu yok.");
  g.randevu.forEach(x => ekle(k, "#" + x.id + " " + x.baslik, x.zaman));
  baslik(k, "Rutinler");
  if (!g.rutin.length) ekle(k, "Rutin yok.");
  g.rutin.forEach(x => ekle(k, "#" + x.id + " " + x.baslik, x.zaman + "  (günler: " + x.tekrar + ")"));
  const o = await istek("/ozet");
  baslik(k, "Hatırlatıcılar");
  if (!o.hatirlaticilar.length) ekle(k, "Bekleyen hatırlatıcı yok.");
  o.hatirlaticilar.forEach(h => ekle(k, h.mesaj, h.zaman));
}

const durumYazi = { alindi: "alındı", almadi: "almadı", atlandi: "atlandı", tamamlandi: "tamamlandı",
                    bekliyor: "bekliyor", ertelendi: "ertelendi", yanitsiz: "YANITSIZ (bilinmiyor)" };

async function ilacCiz() {
  const l = await istek("/ilac/bugun");
  const k = document.getElementById("pIlac");
  k.innerHTML = "";
  baslik(k, "Bugünkü dozlar");
  if (!l.length) ekle(k, "Bugün için doz kaydı yok. İlaç eklemek için sohbete yazın: ilaç ekle: Ad 08:00 20:00");
  l.forEach(x => {
    const d = ekle(k, "", "");
    const n = document.createElement("span"); n.className = "durumNokta d-" + x.durum; d.appendChild(n);
    d.appendChild(document.createTextNode("D" + x.id + "  " + x.planli.slice(11) + "  " + x.ilac_ad +
      (x.doz_notu ? " (" + x.doz_notu + ")" : "") + " — " + durumYazi[x.durum]));
    if (x.durum === "yanitsiz") {
      const du = document.createElement("div");
      d.appendChild(du);
      [["Aldım (kaydı düzelt)", "alindi"], ["Almadım", "almadi"]].forEach(([a, y]) => {
        const b = document.createElement("button");
        b.className = "dugme"; b.style.margin = "6px 4px 0 0"; b.textContent = a;
        b.onclick = async () => { b.disabled = true; await istek("/ilac/duzelt", { doz: x.id, yanit: y }); ilacCiz(); };
        du.appendChild(b);
      });
    }
    if (x.durum === "bekliyor" || x.durum === "ertelendi") {
      const dugmeler = document.createElement("div");
      d.appendChild(dugmeler);
      [["Aldım", "alindi"], ["Ertele 15", "ertele"], ["Almadım", "almadi"], ["Atla", "atlandi"]].forEach(([a, y]) => {
        const b = document.createElement("button");
        b.className = "dugme"; b.style.margin = "6px 4px 0 0"; b.textContent = a;
        b.onclick = async () => {
          d.querySelectorAll("button").forEach(z => z.disabled = true);
          await istek("/ilac/yanit", { doz: x.id, yanit: y, dk: 15 });
          ilacCiz();
        };
        dugmeler.appendChild(b);
      });
    }
  });
  const n = document.createElement("div");
  n.style.cssText = "color:var(--soluk);font-size:12px;margin-top:12px";
  n.textContent = "Her düğme yalnızca kendi dozunu değiştirir. Ülgen dozu değiştirmez ve tıbbi öneri vermez.";
  k.appendChild(n);
  baslik(k, "Mac kapalıyken de çalsın");
  const t = ekle(k, "İlaç, randevu ve rutin alarmlarını iPhone takvimine aktarın; Mac uykudayken ya da kapalıyken de çalar.",
    "Alarm yalnızca çalar; 'aldım' yanıtı Ülgen'e ulaşabildiğinizde verilir. Plan değişince yeniden aktarın.");
  const tb = document.createElement("button");
  tb.className = "dugme aktif"; tb.style.marginTop = "8px"; tb.textContent = "iPhone takvimine aktar";
  tb.onclick = async () => {
    const c = await istek("/takvim/baglanti", {});
    location.href = c.adres;
  };
  t.appendChild(tb);
}

function bildirimCiz() {
  const k = document.getElementById("pBildirim");
  k.innerHTML = "";
  baslik(k, "Son bildirimler");
  if (!gecmisBildirim.length) ekle(k, "Bu oturumda bildirim yok.");
  gecmisBildirim.slice().reverse().forEach(b => ekle(k, b.metin, b.saat));
}

function tarihYazi(sn) { return sn ? new Date(sn * 1000).toLocaleString("tr-TR") : "yok"; }

async function sistemCiz() {
  const s = await istek("/sistem");
  const k = document.getElementById("pSistem");
  k.innerHTML = "";
  baslik(k, "Durum");
  ekle(k, "Ülgen " + s.surum + "  ·  veritabanı sürümü " + s.veritabani_surumu,
       "Bütünlük: " + (s.butunluk.saglam ? "sağlam" : "SORUNLU: " + s.butunluk.ayrinti));
  ekle(k, "Beyin: " + (s.beyin.beyin || "yok"), "Kuyrukta bekleyen istek: " + s.kuyruk);
  ekle(k, "Son otomatik yedek: " + tarihYazi(s.son_yedek));
  baslik(k, "Kota (ücretsiz katmanlar, maliyet 0)");
  s.kota.forEach(t => {
    const e = t.tahmini;
    const d = ekle(k, t.ad + " — " + (t.engelli ? "ENGELLİ: " + t.neden : "kullanılabilir"),
      "Tahmini (kendi sayacım): bugün " + e.istek_gun + " istek, ~" + e.token_gun + " token; gecikme " + e.gecikme_ms +
      " ms; hata %" + Math.round(t.hata_orani * 100));
    if (t.gercek) {
      const g = document.createElement("small");
      g.textContent = "GERÇEK (sağlayıcı bildirdi): " + Object.entries(t.gercek).map(([a, b]) => a + "=" + b).join(", ");
      d.appendChild(g);
    } else if (!t.yerel) {
      const g = document.createElement("small"); g.textContent = "Gerçek kalan kota: sağlayıcı bildirmedi."; d.appendChild(g);
    }
  });
  baslik(k, "Cihazlar (iptal için Mac'te: --cihaz-iptal NUMARA)");
  s.cihazlar.forEach(c => ekle(k, "#" + c.id + " " + c.ad + (c.iptal ? " (iptal)" : ""), "Son kullanım: " + (c.son_kullanim || "yok")));
  if (!s.cihazlar.length) ekle(k, "Kayıtlı cihaz yok.");
  baslik(k, "Son günlük kayıtları");
  s.gunluk.forEach(g => ekle(k, g.seviye + " · " + g.kaynak + ": " + g.metin, g.zaman));
}

// ---- bağlantı izleme ------------------------------------------------------
let kopuk = false;
let denemeAraligi = 5000;

function baglantiDurumu(iyi) {
  document.getElementById("baglanti").classList.toggle("acik", !iyi);
  document.getElementById("nokta").classList.toggle("acik", iyi);
  if (iyi && kopuk) { kopuk = false; denemeAraligi = 5000; ozetYukle(); if (!sohbetli(aktifSekme)) panelYenile(aktifSekme); }
  if (!iyi) kopuk = true;
}

async function nabiz() {
  try {
    const c = await fetch("/saglik", { cache: "no-store" });
    baglantiDurumu(c.ok);
    if (c.ok) denemeAraligi = 5000;
  } catch (e) {
    baglantiDurumu(false);
    denemeAraligi = Math.min(denemeAraligi * 2, 60000);   // artan bekleme
  }
  setTimeout(nabiz, denemeAraligi);
}

document.addEventListener("visibilitychange", () => {
  if (!document.hidden) { bildirimleriAl(); if (!sohbetli(aktifSekme)) panelYenile(aktifSekme); }
});

const kodDil = { py: "python", js: "node", sh: "bash" };

async function kodListele(sec) {
  try {
    const l = await istek("/kod/liste");
    const k = document.getElementById("kodDosya");
    k.innerHTML = '<option value="">Yeni dosya</option>';
    l.forEach(a => { const o = document.createElement("option"); o.value = a; o.textContent = a; k.appendChild(o); });
    if (sec) k.value = sec;
  } catch (e) { /* sessizce geç */ }
}

function kodAcPencere() { document.getElementById("kodPanel").classList.add("acik"); kodListele(); }
function kodKapat() { document.getElementById("kodPanel").classList.remove("acik"); }

async function kodAc() {
  const ad = document.getElementById("kodDosya").value;
  if (!ad) { document.getElementById("kodAd").value = ""; return; }
  const c = await istek("/kod/oku?ad=" + encodeURIComponent(ad));
  if (c.hata) { kodDurum(c.hata); return; }
  document.getElementById("kodYazi").value = c.icerik;
  document.getElementById("kodAd").value = ad;
  const dil = kodDil[ad.split(".").pop()];
  if (dil) document.getElementById("kodDil").value = dil;
}

function kodDurum(m) { document.getElementById("kodDurum").textContent = m; }

function kodTus(e) {
  if (e.key === "Tab") {
    e.preventDefault();
    const t = e.target, b = t.selectionStart;
    t.value = t.value.slice(0, b) + "    " + t.value.slice(t.selectionEnd);
    t.selectionStart = t.selectionEnd = b + 4;
  }
}

async function kodKaydet() {
  const ad = document.getElementById("kodAd").value.trim();
  const c = await istek("/kod/kaydet", { ad: ad, icerik: document.getElementById("kodYazi").value });
  if (c.hata) { kodDurum(c.hata); return; }
  kodDurum("Kaydedildi: " + c.ad);
  kodListele(c.ad);
}

async function kodCalistir() {
  const b = document.getElementById("kodCalistirBtn");
  const cikti = document.getElementById("kodCikti");
  b.disabled = true;
  cikti.textContent = "Çalışıyor...";
  try {
    const c = await istek("/kod/calistir", { icerik: document.getElementById("kodYazi").value,
                                              dil: document.getElementById("kodDil").value });
    cikti.textContent = c.hata ? c.hata : (c.cikti || "(çıktı yok)") +
      "\n\n[çıkış kodu " + c.cikis + ", " + c.sure_sn + " sn]";
  } catch (e) { cikti.textContent = e.message; }
  b.disabled = false;
}

function kodUlgenSor() {
  const kod = document.getElementById("kodYazi").value;
  const cikti = document.getElementById("kodCikti").textContent;
  document.getElementById("giris").value =
    "Şu kodu incele ve düzelt:\n" + kod + "\n\nÇıktısı:\n" + cikti;
  kodKapat();
}

anahtarIste();
istek("/durum").then(d => { sonBildirim = d.son_bildirim || 0; }).catch(() => {});
ozetYukle();
setInterval(ozetYukle, 60000);
setInterval(bildirimleriAl, 20000);
setTimeout(nabiz, 5000);
balonEkle("Merhaba, hoş geldiniz. Size nasıl yardımcı olabilirim?", "asistan");
</script>
</body>
</html>
"""


# --- Sıkı CSP için: betik ayrı dosyadan (/varlik/uygulama.js), gömülü olay
# yöneticisi (onclick=...) yok; data-onclick="ad(arg)" özniteliği tek bir
# dinleyiciyle çalıştırılır (eval yok).
_OLAYLAR = r"""
(function () {
  for (const ol of ["click", "keydown", "change"]) {
    document.addEventListener(ol, e => {
      const el = e.target.closest ? e.target.closest("[data-on" + ol + "]") : null;
      if (!el) return;
      const m = /^(\w+)\((.*)\)$/.exec(el.getAttribute("data-on" + ol));
      const f = m && window[m[1]];
      if (typeof f !== "function") return;
      const args = m[2].trim() ? m[2].split(/,(?=(?:[^']*'[^']*')*[^']*$)/).map(a => {
        a = a.trim();
        if (a === "event") return e;
        return a[0] === "'" ? a.slice(1, -1) : JSON.parse(a);
      }) : [];
      f.apply(el, args);
    });
  }
})();
"""

_ESLESME = re.search(r"<script>(.*)</script>", _HAM, re.S)
BETIK = _OLAYLAR + _ESLESME.group(1)
SAYFA = _HAM.replace(_ESLESME.group(0),
                     '<script src="/varlik/uygulama.js"></script>')
SAYFA = re.sub(r' on(click|keydown|change)="', r' data-on\1="', SAYFA)
