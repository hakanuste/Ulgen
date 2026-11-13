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
<meta name="theme-color" content="var(--ulgen-bg)">
<link rel="apple-touch-icon" href="/varlik/simge.png">
<link rel="icon" href="/varlik/simge.png">
<title>Ülgen</title>
<style>
:root { color-scheme: dark;
  /* ÜLGEN resmî tema (tek merkez) */
  --ulgen-bg:#030914; --ulgen-navy:#061A32; --ulgen-ocean:#082B4C; --ulgen-panel:#0D243B;
  --ulgen-blue:#00BFFF; --ulgen-ice:#78DFFF;
  --ulgen-gold:#D9A441; --ulgen-gold-bright:#FFC857; --ulgen-champagne:#F5DFA5;
  --ulgen-text:#F2F5FA; --ulgen-muted:#AAB8C8;
  --ulgen-success:#32D875; --ulgen-warning:#FFBF47; --ulgen-danger:#FF5364;
  --ulgen-info:#36BFFF; --ulgen-offline:#68788A;
  /* eski adlar → resmî değişkenler */
  --bg:var(--ulgen-bg); --kart:var(--ulgen-panel); --kart2:var(--ulgen-ocean); --yazi:var(--ulgen-text);
  --soluk:var(--ulgen-muted); --vurgu:var(--ulgen-blue); --kullanici:var(--ulgen-ocean);
  --kenar:var(--ulgen-ocean); --altin:var(--ulgen-gold); --altin2:var(--ulgen-gold);
  --yesil:var(--ulgen-success); --kirmizi:var(--ulgen-danger); }
* { box-sizing: border-box; }
html, body { height: 100%; margin: 0; }
body { background: var(--bg); color: var(--yazi); font-family: -apple-system, system-ui, sans-serif;
       display: flex; flex-direction: column; }
header { padding: calc(env(safe-area-inset-top) + 12px) 16px 10px; display: flex;
         align-items: center; justify-content: space-between; border-bottom: 1px solid var(--kenar); }
header h1 { font-size: 17px; margin: 0; letter-spacing: 2px; }
header .dugme { padding: 6px 8px; font-size: 12px; }
.nokta { width: 9px; height: 9px; border-radius: 50%; background: var(--ulgen-offline); display: inline-block;
         margin-right: 8px; vertical-align: middle; }
.nokta.acik { background: var(--ulgen-success); box-shadow: 0 0 8px var(--ulgen-success); }
.dugme { background: var(--kart); color: var(--yazi); border: 1px solid var(--ulgen-ocean); border-radius: 10px;
         padding: 8px 12px; font-size: 14px; }
.dugme.aktif { background: var(--vurgu); color: var(--ulgen-bg); border-color: var(--vurgu); }
#yaklasan { font-size: 13px; color: var(--soluk); padding: 8px 16px; border-bottom: 1px solid var(--kenar); }
#yaklasan div { padding: 2px 0; }
#akis { flex: 1; overflow-y: auto; padding: 14px 14px 6px; }
.balon { max-width: 85%; padding: 10px 13px; border-radius: 16px; margin: 6px 0; line-height: 1.4;
         font-size: 16px; white-space: pre-wrap; word-wrap: break-word; overflow-wrap: anywhere;
         min-width: 0; overflow-x: auto; }
.balon.asistan { white-space: normal; }
.mdBaslik { font-weight: 700; color: var(--ulgen-gold, #e9c46a); margin: 4px 0 2px; }
.mdB1 { font-size: 1.15em; } .mdB2 { font-size: 1.05em; } .mdB3 { font-size: 1em; }
.mdMadde { padding-left: 1.1em; text-indent: -0.8em; }
.mdMadde::before { content: "• "; }
.mdNot { border-left: 3px solid var(--kenar); padding-left: 8px; color: var(--soluk); font-style: italic; }
.mdBos { height: 0.6em; }
.mdKod { white-space: pre-wrap; background: rgba(0,0,0,.25); padding: 6px 8px; border-radius: 8px; font-size: 13px; }
.balon code { background: rgba(0,0,0,.25); padding: 0 4px; border-radius: 4px; }
/* Uzun yanıt sayfayı yana genişletmesin: esnek kutular içeriğe göre büyümez */
#ana, #icerik, #sohbetKolon, #akis, .sat, #pano { min-width: 0; max-width: 100%; }
#akis { overflow-x: hidden; }
.balon pre, .balon table { max-width: 100%; overflow-x: auto; }
.asistan { background: var(--kart); margin-right: auto; border-bottom-left-radius: 4px; }
.kullanici { background: var(--kullanici); margin-left: auto; border-bottom-right-radius: 4px; }
.bildirim { background: color-mix(in srgb, var(--ulgen-warning) 18%, var(--ulgen-bg)); border: 1px solid color-mix(in srgb, var(--ulgen-warning) 50%, var(--ulgen-bg)); margin-right: auto; }
#alt { padding: 8px 12px calc(env(safe-area-inset-bottom) + 10px); border-top: 1px solid var(--kenar);
       display: flex; gap: 8px; align-items: flex-end; }
#giris { flex: 1; resize: none; background: var(--kart); color: var(--yazi); border: 1px solid var(--ulgen-ocean);
         border-radius: 14px; padding: 10px 12px; font-size: 16px; font-family: inherit; max-height: 120px; }
.yuvarlak { width: 44px; height: 44px; border-radius: 50%; border: 0; background: var(--kart);
            color: var(--yazi); font-size: 18px; flex-shrink: 0; }
.yuvarlak.kayit { background: var(--ulgen-danger); }
.yuvarlak.gonder { background: var(--vurgu); color: var(--ulgen-bg); }
#anahtarKutu { position: fixed; inset: 0; background: rgba(0,0,0,.7); display: none;
               align-items: center; justify-content: center; padding: 20px; }
#anahtarKutu.acik { display: flex; }
#anahtarKutu .kart { background: var(--kart); padding: 18px; border-radius: 14px; width: 100%; max-width: 360px; }
#anahtarKutu input { width: 100%; padding: 10px; border-radius: 10px; border: 1px solid var(--ulgen-ocean);
                     background: var(--bg); color: var(--yazi); font-size: 16px; margin: 10px 0; }
#sekmeler { display: flex; gap: 4px; padding: 6px 8px; border-bottom: 1px solid var(--kenar); overflow-x: auto; }
#sekmeler button { flex: 1; white-space: nowrap; background: transparent; color: var(--soluk); border: 0;
                   padding: 8px 6px; font-size: 14px; border-radius: 8px; }
#sekmeler button.aktif { background: var(--kart); color: var(--vurgu); }
#geriBtn { display: none; }
.panel { display: none; flex: 1; overflow-y: auto; padding: 12px 14px; }
.panel.acik { display: block; }
.panel h3 { margin: 14px 0 6px; font-size: 14px; color: var(--soluk); font-weight: 600; }
.satir2 { background: var(--kart); border-radius: 10px; padding: 9px 11px; margin: 6px 0; font-size: 14px; line-height: 1.4; }
.satir2 small { color: var(--soluk); display: block; }
.durumNokta { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; background: var(--ulgen-offline); }
.d-alindi { background: var(--ulgen-success); } .d-almadi, .d-yanitsiz { background: var(--ulgen-danger); } .d-bekliyor { background: var(--ulgen-warning); }
.d-ertelendi { background: var(--ulgen-blue); } .d-atlandi { background: var(--ulgen-muted); }
#baglanti { display: none; background: color-mix(in srgb, var(--ulgen-danger) 25%, var(--ulgen-bg)); color: #ffd7d7; font-size: 13px; padding: 6px 16px; text-align: center; }
#baglanti.acik { display: block; }
#kodPanel, #ajanPanel { position: fixed; inset: 0; background: var(--bg); display: none; flex-direction: column;
            padding: calc(env(safe-area-inset-top) + 8px) 10px calc(env(safe-area-inset-bottom) + 8px); z-index: 5; }
#kodPanel.acik, #ajanPanel.acik { display: flex; }
#kodPanel .satir, #ajanPanel .satir { display: flex; gap: 6px; margin: 4px 0; flex-wrap: wrap; align-items: center; }
#kodPanel select, #kodPanel input, #ajanPanel select, #ajanPanel textarea { background: var(--kart); color: var(--yazi); border: 1px solid var(--ulgen-ocean);
            border-radius: 8px; padding: 7px; font-size: 14px; }
#kodYazi { flex: 1; min-height: 160px; resize: none; background: var(--ulgen-bg); color: var(--ulgen-text); border: 1px solid var(--ulgen-ocean);
           border-radius: 10px; padding: 10px; font: 14px/1.45 ui-monospace, Menlo, monospace; tab-size: 4; }
#kodCikti { height: 28%; overflow: auto; margin: 6px 0 0; background: var(--ulgen-bg); border: 1px solid var(--ulgen-ocean);
            border-radius: 10px; padding: 8px; font: 13px/1.4 ui-monospace, Menlo, monospace; white-space: pre-wrap; }

#ana { background: linear-gradient(rgba(3,9,20,.86), rgba(3,9,20,.92)), url(/varlik/zemin.webp) center / cover; }
#akis { background: linear-gradient(rgba(3,9,20,.80), rgba(3,9,20,.9)), url(/varlik/sahne.webp) center / cover; }
img.sus { display: block; width: 100%; height: 92px; object-fit: cover; border-radius: 12px; margin: 2px 0 8px;
          border: 1px solid var(--kenar); }
img.pus { display: block; width: 84px; height: 84px; margin: 4px auto 8px; border-radius: 50%; object-fit: cover;
          box-shadow: 0 0 18px rgba(217,164,65,.35); }
#runlar { position: absolute; left: 270px; top: 22px; color: var(--altin); font-size: 22px; letter-spacing: 8px;
          font-family: "Apple Symbols", "Noto Sans Old Turkic", "Segoe UI Historic", serif; text-shadow: 0 0 8px rgba(217,164,65,.5); }
#baslikOrta { top: 6px; } #baslikOrta .egri { position: absolute; left: 50%; top: 60px; width: 640px; margin-left: -320px; height: 70px; opacity: .85; pointer-events: none; }
#baslikOrta .yd { color: var(--altin); display: inline-block; vertical-align: middle; filter: drop-shadow(0 0 8px rgba(217,164,65,.8)); margin: 0 10px; }
#baslikOrta .yd svg { width: 30px; height: 30px; }
#baslikOrta b { display: inline-block !important; vertical-align: middle; }
#havaYazi { display: flex; gap: 8px; align-items: center; justify-content: flex-end; margin-top: 6px; font-size: 13px; }
#havaYazi svg { color: var(--altin); width: 26px; height: 26px; } #havaYazi b { font-size: 15px !important; letter-spacing: 0 !important; display: block; }
#dagKutu { display: none; }
.sag3 { display: grid; grid-template-columns: 1.3fr 1fr 1fr; justify-items: center; align-items: center; margin-top: 6px; text-align: center; font-size: 13px; color: var(--yazi); }
.sag3 .oge svg { width: 30px; height: 30px; display: block; margin: 0 auto 2px; } .sag3 b { display: block; font-size: 18px; }
.nokta2 { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; background: var(--ulgen-offline); }
.nokta2.y { background: var(--yesil); box-shadow: 0 0 6px var(--yesil); } .nokta2.k { background: var(--kirmizi); }
.ozetCubuk { display: flex; align-items: center; gap: 10px; margin-top: 8px; } .ozetCubuk .cubuk { flex: 1; margin: 0; }
.ozetCubuk span { color: var(--yazi); font-size: 13px; }
#pano .s .sol { display: flex; align-items: center; gap: 8px; }
.cubuk.mor i { background: linear-gradient(90deg,var(--ulgen-blue),var(--ulgen-ice)); } .cubuk.yes i { background: linear-gradient(90deg,var(--ulgen-success),var(--ulgen-success)); }
/* ---- ÜLGEN teması: gece mavisi + altın ---- */
:root { --bg:var(--ulgen-bg); --kart:var(--ulgen-panel); --kart2:var(--ulgen-ocean); --yazi:var(--ulgen-text); --soluk:var(--ulgen-muted); --vurgu:var(--ulgen-blue);
        --kullanici:var(--ulgen-ocean); --kenar:var(--ulgen-ocean); --altin:var(--ulgen-gold); --altin2:var(--ulgen-gold); --yesil:var(--ulgen-success); --kirmizi:var(--ulgen-danger); }
body { background: radial-gradient(1400px 700px at 75% -15%, var(--ulgen-ocean) 0%, var(--bg) 62%); }
.dugme { border-color: var(--kenar); }
.dugme.aktif { background: linear-gradient(180deg,var(--ulgen-ice),var(--ulgen-blue)); }
.satir2 { border: 1px solid var(--kenar); background: var(--kart); }
svg.i { width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; flex: none; }
#kok { display: flex; flex-direction: column; flex: 1; min-height: 0; }
#ana { display: flex; flex-direction: column; flex: 1; min-height: 0; position: relative; }
#yan { display: contents; }
#marka, #kullanici, #afis, #serit, #cipler .genis { display: none; }
#marka .mk, #kapatBtn, #perde, #hamBtn, #mobilLogo, #mobilAlt, #mobilAna, .rz { display: none; }
.rz { background: var(--kirmizi); color: #fff; font-style: normal; font-size: 12px; min-width: 20px; height: 20px; border-radius: 10px; place-items: center; padding: 0 6px; margin-left: auto; }
.rz.var { display: inline-grid; }
#icerik { display: flex; flex: 1; min-height: 0; flex-direction: column; }
#sohbetKolon { display: flex; flex-direction: column; flex: 1; min-height: 0; }
#pano { display: none; }
body[data-s="gorevler"] #sohbetKolon, body[data-s="ilac"] #sohbetKolon, body[data-s="bildirim"] #sohbetKolon,
body[data-s="kasa"] #sohbetKolon, body[data-s="sistem"] #sohbetKolon, body[data-s="saglik"] #sohbetKolon, body[data-s="projeler"] #sohbetKolon,
body[data-s="bilgi"] #sohbetKolon, body[data-s="yz"] #sohbetKolon, body[data-s="ajanlar"] #sohbetKolon, body[data-s="ayarlar"] #sohbetKolon { display: none; }
#saat { font-variant-numeric: tabular-nums; color: var(--altin); font-size: 13px; }
.sat { display: flex; gap: 10px; align-items: flex-end; margin: 8px 0; }
.sat.sk { flex-direction: row-reverse; }
.av { width: 38px; height: 38px; border-radius: 50%; flex: none; border: 1px solid var(--altin2); overflow: hidden;
      background: var(--ulgen-navy) center/cover; display: grid; place-items: center; font-size: 15px; color: var(--altin); }
.av.ul { background-image: url(/varlik/logo.webp); background-size: 190%; background-position: 50% 28%; }
.sat .balon { margin: 0; }
.balon small { display: block; text-align: right; font-size: 11px; color: var(--soluk); margin-top: 4px; }
.balon.asistan, .balon.kullanici { border: 1px solid var(--kenar); }
.balon.kullanici { background: linear-gradient(180deg,var(--ulgen-ocean),var(--ulgen-ocean)); }
#cipler { display: flex; gap: 8px; padding: 6px 12px 0; overflow-x: auto; }
#cipler button { white-space: nowrap; background: rgba(13,36,59,.8); color: var(--altin); border: 1px solid var(--altin2);
                 border-radius: 999px; padding: 7px 14px; font-size: 13px; }
.dalga { display: none; align-items: center; gap: 3px; height: 30px; }
.dalga i { width: 3px; border-radius: 2px; background: var(--vurgu); height: 8px; animation: dalga 1.1s ease-in-out infinite; }
.dalga i:nth-child(2n) { animation-delay: .2s; height: 16px; } .dalga i:nth-child(3n) { animation-delay: .4s; height: 24px; }
@keyframes dalga { 50% { transform: scaleY(1.7); } }
#alt .yuvarlak { background: var(--kart2); border: 1px solid var(--kenar); }
#mikBtn { box-shadow: 0 0 0 1px var(--vurgu), 0 0 16px rgba(0,191,255,.55); background: radial-gradient(circle,var(--ulgen-ocean),var(--ulgen-ocean)); }
.kartK { background: linear-gradient(180deg,var(--kart2),var(--kart)); border: 1px solid var(--kenar);
         border-radius: 16px; padding: 12px 14px; font-size: 13px; color: var(--soluk); position: relative;
         box-shadow: 0 0 18px rgba(8,43,76,.18) inset; }
.kartK .ust { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; color: var(--yazi); }
.kartK .ust b { font-size: 15px; flex: 1; }
.kartK .ust svg { color: var(--altin); }
.kartK.uyari { border-color: color-mix(in srgb, var(--ulgen-danger) 55%, var(--ulgen-bg)); } .kartK.uyari .ust svg { color: var(--kirmizi); }
.cubuk { height: 6px; background: var(--ulgen-navy); border-radius: 4px; margin-top: 6px; overflow: hidden; }
.cubuk i { display: block; height: 100%; background: linear-gradient(90deg,var(--ulgen-blue),var(--ulgen-ice)); }
.rozet { display: inline-grid; place-items: center; width: 22px; height: 22px; border-radius: 6px; font-size: 12px;
         font-weight: 700; color: #fff; margin-right: 8px; vertical-align: middle; }
#pano .s { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 6px 0; font-size: 13px;
           border-top: 1px solid var(--kenar); color: var(--yazi); }
#pano .s span:last-child { color: var(--soluk); white-space: nowrap; }
#pano .ok { color: var(--yesil) !important; } #pano .bekle { color: var(--altin) !important; }
.halka { width: 92px; height: 92px; border-radius: 50%; display: grid; place-items: center; margin: 4px auto;
         background: conic-gradient(var(--yesil) var(--p,0%), var(--ulgen-panel) 0); }
.halka span { width: 74px; height: 74px; border-radius: 50%; background: var(--kart); display: grid; place-items: center;
              color: var(--yazi); font-size: 13px; text-align: center; line-height: 1.2; }
@media (max-width: 1239px) {
  #yan { display: flex; flex-direction: column; position: fixed; top: 0; left: 0; bottom: 0; width: 84%; max-width: 340px; z-index: 30;
         transform: translateX(-105%); transition: transform .25s; padding: calc(env(safe-area-inset-top) + 14px) 14px calc(env(safe-area-inset-bottom) + 14px);
         background: linear-gradient(180deg,var(--ulgen-navy),var(--ulgen-bg)); border-right: 1px solid var(--altin2); overflow-y: auto; }
  body.menuAcik #yan { transform: none; }
  #perde { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.55); z-index: 25; }
  body.menuAcik #perde { display: block; }
  #marka { display: flex; align-items: center; gap: 10px; padding: 0 0 12px; }
  #marka img { width: 66px; height: auto; }
  #marka .mk b { color: var(--altin); font-size: 24px; letter-spacing: 2px; margin-right: 8px; }
  #surumRozet { border: 1px solid var(--altin2); border-radius: 12px; padding: 2px 8px; font-size: 12px; color: var(--yazi); }
  #kapatBtn { margin-left: auto; width: 40px; height: 40px; border-radius: 50%; border: 1px solid var(--kenar); background: transparent;
              color: var(--yazi); display: grid; place-items: center; }
  #sekmeler { flex-direction: column; border: 0; padding: 0; gap: 2px; overflow: visible; background: none; }
  #sekmeler button { display: flex; align-items: center; gap: 14px; flex: none; text-align: left; font-size: 16px; padding: 10px 12px; color: var(--yazi);
                     border: 1px solid transparent; border-radius: 14px; }
  #sekmeler button svg { color: var(--altin); width: 24px; height: 24px; }
  #sekmeler button.aktif { background: linear-gradient(90deg,var(--ulgen-ocean),var(--ulgen-ocean)); border-color: var(--vurgu); box-shadow: 0 0 14px rgba(0,191,255,.3); }
  .rz { margin-left: auto; background: var(--kirmizi); color: #fff; font-style: normal; font-size: 12px; min-width: 20px; height: 20px; border-radius: 10px;
        display: none; place-items: center; padding: 0 6px; } .rz.var { display: grid; }
  #dagKutu { display: block; height: 90px; margin: auto -14px 8px; background: url(/varlik/afis.webp) 60% 100% / cover; opacity: .85;
             mask-image: linear-gradient(transparent, #000 45%); -webkit-mask-image: linear-gradient(transparent, #000 45%); flex: none; }
  #kullanici { display: flex; gap: 12px; align-items: center; padding: 10px 12px; border: 1px solid var(--altin2); border-radius: 16px; font-size: 13px; color: var(--soluk); }
  #kullanici b { color: var(--yazi); display: block; font-size: 16px; }
  #ana { order: 1; }
  #serit, #pano, #runlar, #baslikOrta .egri { display: none; }
  #afis { display: block; position: relative; height: calc(58px + env(safe-area-inset-top)); flex: none; overflow: hidden; border-bottom: 1px solid var(--altin2); }
  body[data-s="ana"] #afis { height: calc(250px + env(safe-area-inset-top)); }
  #afis .arka { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(3,9,20,.25), rgba(3,9,20,.1) 60%, var(--ulgen-bg) 100%), url(/varlik/afis.webp) center 35% / cover; }
  #mobilLogo { display: none; position: absolute; left: 50%; top: calc(env(safe-area-inset-top) + 8px); width: 170px; margin-left: -85px; filter: drop-shadow(0 0 14px rgba(120,223,255,.5)); }
  #mobilAlt { display: none; position: absolute; left: 0; right: 0; bottom: 12px; text-align: center; color: #fff; font-size: 15px; text-shadow: 0 1px 4px #000; }
  body[data-s="ana"] #mobilLogo, body[data-s="ana"] #mobilAlt { display: block; }
  #baslikOrta { top: calc(env(safe-area-inset-top) + 12px); } #baslikOrta small, #baslikOrta .yd { display: none; }
  #baslikOrta b { font-size: 22px !important; letter-spacing: 6px !important; }
  body[data-s="ana"] #baslikOrta { display: none; }
  #hamBtn, #sagUst .ik { width: 44px; height: 44px; border-radius: 50%; border: 1px solid var(--altin2); background: rgba(13,36,59,.7); color: var(--altin); display: grid; place-items: center; }
  #hamBtn { position: absolute; left: 14px; top: calc(env(safe-area-inset-top) + 8px); z-index: 3; cursor: pointer; }
  #geriBtn { display: none; position: absolute; left: 68px; top: calc(env(safe-area-inset-top) + 8px); z-index: 3; height: 44px; padding: 0 16px;
             border-radius: 22px; border: 1px solid var(--altin2); background: rgba(13,36,59,.85); color: var(--altin); font-size: 16px; }
  body:not([data-s="ana"]) #geriBtn { display: block; }
  #sagUst { position: absolute; right: 14px; top: calc(env(safe-area-inset-top) + 8px); z-index: 3; gap: 8px; display: flex; }
  #sagUst .ik:not(:first-child) { display: none; }
  #sagUst .ik { position: relative; } #sagUst .ik em { position: absolute; top: -3px; right: -3px; background: var(--kirmizi); color: #fff; font-style: normal; font-size: 10px; border-radius: 9px; min-width: 16px; text-align: center; padding: 1px 3px; }
  #saatKutu { display: none; }
  body[data-s="ana"] #saatKutu { display: flex; align-items: center; margin: 4px 14px 0; padding: 12px 14px; border: 1px solid var(--altin2); border-radius: 18px;
        background: linear-gradient(180deg,var(--kart2),var(--kart)); box-shadow: 0 0 16px rgba(217,164,65,.15); }
  #saatKutu .tk { display: flex; align-items: center; gap: 12px; flex: 1; border-right: 1px solid var(--altin2); }
  #saatKutu .tk svg { width: 30px; height: 30px; color: var(--altin); } #saatKutu small { display: block; font-size: 13px; } #saatKutu b { font-size: 30px; }
  #havaYazi { flex: 1; justify-content: center; margin: 0; }
  header { display: none; }
  body[data-s="sohbet"] header { display: flex; position: static; padding: 6px 12px; gap: 6px; flex-wrap: wrap; }
  body[data-s="sohbet"] header h1, body[data-s="sohbet"] header #saat { display: none; }
  #mobilAna { display: none; }
  body[data-s="ana"] #mobilAna { display: block; flex: 1; overflow-y: auto; }
  #kareler { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; padding: 12px 14px 4px; }
  .kare { position: relative; aspect-ratio: 1 / .95; border-radius: 18px; border: 1px solid var(--kenar); color: var(--yazi); font-size: 13px;
          background: linear-gradient(180deg,var(--kart2),var(--kart)); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; }
  .kare svg { width: 32px; height: 32px; color: var(--altin); }
  .kare:first-child { border-color: var(--vurgu); box-shadow: 0 0 14px rgba(0,191,255,.35); }
  .kare .rz { position: absolute; top: -6px; right: -4px; margin: 0; }
  #mobilOzet { padding: 8px 14px 14px; display: flex; flex-direction: column; gap: 12px; }
  body[data-s="ana"] #sohbetKolon { flex: none; }
  body[data-s="ana"] #akis, body[data-s="ana"] #cipler, body[data-s="ana"] #yaklasan, body[data-s="ana"] #beyin { display: none; }
  #alt { flex-direction: column; align-items: stretch; gap: 8px; background: linear-gradient(180deg, rgba(3,9,20,0), var(--ulgen-bg) 30%); }
  #mikSatir { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
  #klavyeBtn { width: 52px; height: 52px; border-radius: 16px; }
  #mikBtn { width: 76px; height: 76px; }
  #mikBtn svg { width: 34px; height: 34px; }
  #mikSatir .dalga { display: flex; flex: 1; justify-content: center; opacity: .8; }
  #mikSatir .dalga i { animation: none; } body.dinliyor #mikSatir .dalga i { animation: dalga 1.1s ease-in-out infinite; }
  #yazSatir { display: flex; gap: 8px; align-items: flex-end; }
  #yazSatir #giris { flex: 1; border-radius: 22px; border: 1px solid var(--altin2); }
  #dalgaS { transform: scaleX(-1); }
}
@media (min-width: 1240px) {
  #kok { flex-direction: row; }
  #yan { display: flex; flex-direction: column; width: 236px; flex-shrink: 0; padding: 14px 14px 16px;
         border-right: 1px solid var(--altin2); background: linear-gradient(180deg,var(--ulgen-navy),var(--ulgen-bg));
         box-shadow: 0 0 22px rgba(217,164,65,.12); }
  #marka { display: block; text-align: center; padding: 0 0 12px; }
  #marka img { width: 100%; max-width: 190px; height: auto; filter: drop-shadow(0 0 14px rgba(120,223,255,.35)); }
  #sekmeler { flex-direction: column; border: 0; padding: 0; gap: 4px; overflow: visible; }
  #dagKutu { display: block; height: 96px; margin: auto -14px 8px; background: linear-gradient(var(--ulgen-navy), rgba(3,9,20,0) 40%), url(/varlik/afis.webp) 60% 100% / cover; opacity: .9; mask-image: linear-gradient(transparent, #000 40%); -webkit-mask-image: linear-gradient(transparent, #000 40%); }
  #kullanici { margin-top: 0 !important; }
  #sekmeler button { flex: none; display: flex; align-items: center; gap: 12px; text-align: left; font-size: 15px;
                     padding: 11px 14px; color: var(--yazi); border: 1px solid transparent; border-radius: 12px; }
  #sekmeler button svg { color: var(--altin); }
  #sekmeler button.aktif { background: linear-gradient(90deg,var(--ulgen-ocean),var(--ulgen-ocean)); border-color: var(--vurgu);
                           box-shadow: 0 0 14px rgba(0,191,255,.3); }
  #kullanici { display: flex; gap: 10px; align-items: center; margin-top: auto; padding: 12px 4px 0;
               border-top: 1px solid var(--kenar); font-size: 12px; color: var(--soluk); }
  #kullanici b { color: var(--yazi); display: block; font-size: 14px; }
  #afis { display: block; position: relative; height: 132px; flex: none; border-bottom: 1px solid var(--altin2); overflow: hidden; }
  #afis .arka { position: absolute; inset: 0; background:
      linear-gradient(90deg, rgba(3,9,20,.88) 0%, rgba(3,9,20,.2) 30%, rgba(3,9,20,.1) 70%, rgba(3,9,20,.7) 100%),
      url(/varlik/afis.webp) center 40% / cover; }
  #baslikOrta { position: absolute; left: 0; right: 0; top: 14px; text-align: center; }
  #baslikOrta b { display: block; font-size: 36px; letter-spacing: 10px; color: var(--ulgen-champagne); font-weight: 700;
                  text-shadow: 0 0 18px rgba(217,164,65,.5), 0 2px 0 var(--ulgen-gold); }
  #baslikOrta small { color: #fff; font-size: 14px; letter-spacing: 1px; text-shadow: 0 0 6px #000, 0 1px 3px #000; }
  #sagUst { position: absolute; right: 230px; top: 14px; display: flex; gap: 12px; align-items: center; z-index: 3; }
  #saatKutu { position: absolute; right: 18px; top: 8px; text-align: right; z-index: 3; }
  #saatKutu .tk svg { display: none; } #saatKutu .tk { display: block; }
  #hamBtn, #mobilLogo, #mobilAlt, #mobilAna { display: none; }
  #mikSatir, #yazSatir { display: contents; } #klavyeBtn, #dalgaS { display: none; } #giris { order: 1; } #dalga { order: 2; } #mikBtn { order: 3; } .gonder { order: 4; }
  body.dinliyor .dalga { display: flex; }
  #sagUst .ik { width: 40px; height: 40px; border-radius: 50%; border: 1px solid var(--kenar); background: rgba(13,36,59,.8);
                display: grid; place-items: center; position: relative; color: var(--yazi); }
  #sagUst .ik em { position: absolute; top: -3px; right: -3px; background: var(--kirmizi); color: #fff; font-style: normal;
                   font-size: 10px; border-radius: 9px; min-width: 16px; text-align: center; padding: 1px 3px; }
  #sagUst .ik i { position: absolute; right: 2px; bottom: 2px; width: 9px; height: 9px; border-radius: 50%; background: var(--ulgen-offline); }
  #sagUst .ik i.acik { background: var(--yesil); box-shadow: 0 0 6px var(--yesil); }
  #saatKutu small { display: block; color: var(--yazi); font-size: 13px; }
  #saatKutu b { font-size: 34px; letter-spacing: 1px; }
  header { position: absolute; left: 12px; top: 98px; z-index: 4; border: 0; padding: 0; gap: 6px; justify-content: flex-start; }
  header .dugme { font-size: 11px; padding: 4px 8px; }
  header h1, header #saat { display: none; }
  #serit { display: grid; grid-template-columns: repeat(5, minmax(150px, 1fr)); gap: 12px; padding: 14px 16px 4px; }
  #icerik { flex-direction: row; gap: 14px; padding: 12px 16px 14px; }
  #sohbetKolon { flex: 1 1 50%; border: 1px solid var(--kenar); border-radius: 18px; background: rgba(13,36,59,.55); overflow: hidden; }
  body[data-s="ana"] #pano { display: flex; gap: 14px; flex: 0 0 min(56%, 700px); overflow-y: auto; }
  body[data-s="ana"] #sohbetKolon, body[data-s="sohbet"] #sohbetKolon { display: flex; }
  #pano > div { flex: 1; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
  .panel { flex: 1; }
  #cipler .genis { display: inline; }
}
@media (min-width: 1240px) and (max-width: 1599px) { #baslikOrta small { display: none; } }
/* Sohbet sekmesi bütün ekranı kullanır: özet kartları ve hatırlatıcı satırı gizli */
body[data-s="sohbet"] #serit, body[data-s="sohbet"] #yaklasan { display: none !important; }
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
<symbol id="i-gunes" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/></symbol>
<symbol id="i-ay" viewBox="0 0 24 24"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></symbol>
<symbol id="i-veri" viewBox="0 0 24 24"><ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/></symbol>
<symbol id="i-cip" viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/></symbol>
<symbol id="i-klasor" viewBox="0 0 24 24"><path d="M3 6h7l2 2h9v11H3z"/></symbol>
<symbol id="i-beyin" viewBox="0 0 24 24"><path d="M12 4a3.5 3.5 0 0 0-3.5 3.5A3 3 0 0 0 6 10.5a3 3 0 0 0 1 2.3A3 3 0 0 0 9 18a3 3 0 0 0 3 2 3 3 0 0 0 3-2 3 3 0 0 0 2-5.2 3 3 0 0 0 1-2.3 3 3 0 0 0-2.5-3A3.5 3.5 0 0 0 12 4zM12 4v16"/></symbol>
<symbol id="i-dis" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1"/></symbol>
<symbol id="i-yildiz" viewBox="0 0 24 24"><path d="M12 1l2.2 8.8L23 12l-8.8 2.2L12 23l-2.2-8.8L1 12l8.8-2.2z" fill="currentColor" stroke="none"/></symbol>
<symbol id="i-menu" viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16"/></symbol>
<symbol id="i-kapat" viewBox="0 0 24 24"><path d="M5 5l14 14M19 5L5 19"/></symbol>
<symbol id="i-klavye" viewBox="0 0 24 24"><rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/></symbol>
<symbol id="i-nabiz" viewBox="0 0 24 24"><path d="M3 12h4l2-6 4 12 2-6h6"/></symbol>
</defs></svg>
<div id="perde" onclick="menuKapat()"></div>
<div id="kok">
<aside id="yan">
  <div id="marka"><img src="/varlik/logo.webp" alt="Ülgen"><div class="mk"><b>ÜLGEN</b><span id="surumRozet">v</span></div><button id="kapatBtn" class="ik" onclick="menuKapat()" aria-label="Kapat"><svg class="i"><use href="#i-kapat"/></svg></button></div>
  <nav id="sekmeler">
  <button class="aktif" data-s="ana" onclick="sekme('ana')"><svg class="i"><use href="#i-ev"/></svg>Ana Sayfa</button>
  <button data-s="sohbet" onclick="sekme('sohbet')"><svg class="i"><use href="#i-sohbet"/></svg>Sohbet</button>
  <button data-s="gorevler" onclick="sekme('gorevler')"><svg class="i"><use href="#i-gorev"/></svg>Görevler<em class="rz" id="rzGorev"></em></button>
  <button data-s="ilac" onclick="sekme('ilac')"><svg class="i"><use href="#i-hap"/></svg>İlaçlar</button>
  <button data-s="saglik" onclick="sekme('saglik')"><svg class="i"><use href="#i-kalp"/></svg>Sağlık &amp; Ölçümler</button>
  <button data-s="projeler" onclick="sekme('projeler')"><svg class="i"><use href="#i-katman"/></svg>Projeler</button>
  <button data-s="ajanlar" onclick="sekme('ajanlar')"><svg class="i"><use href="#i-cip"/></svg>Ajanlar</button>
  <button data-s="bilgi" onclick="sekme('bilgi')"><svg class="i"><use href="#i-veri"/></svg>Hafıza &amp; Bilgi</button>
  <button data-s="yz" onclick="sekme('yz')"><svg class="i"><use href="#i-cip"/></svg>Yapay Zekâ Modelleri</button>
  <button data-s="kasa" onclick="sekme('kasa')"><svg class="i"><use href="#i-kasa"/></svg>Özel Kasa</button>
  <button data-s="bildirim" onclick="sekme('bildirim')"><svg class="i"><use href="#i-zil"/></svg>Bildirimler<em class="rz" id="rzBildirim"></em></button>
  <button data-s="sistem" onclick="sekme('sistem')"><svg class="i"><use href="#i-nabiz"/></svg>Sistem Durumu</button>
  <button data-s="ayarlar" onclick="sekme('ayarlar')"><svg class="i"><use href="#i-ayar"/></svg>Ayarlar</button>
  </nav>
  <div id="dagKutu"></div>
  <div id="kullanici"><span class="av ul"></span><div><b>Hakan Üste</b><span id="surumYazi">ÜLGEN</span> <span id="nokta2" class="nokta"></span></div></div>
</aside>
<div id="ana">
<div id="afis">
  <div class="arka"></div>
  <button id="hamBtn" class="ik" onclick="menuAc()" aria-label="Menü"><svg class="i"><use href="#i-menu"/></svg></button>
  <button id="geriBtn" onclick="sekme('ana')" aria-label="Ana Sayfa">&#8249; Ana Sayfa</button>
  <img id="mobilLogo" src="/varlik/logo.webp" alt="Ülgen"><div id="mobilAlt">Kişisel Yapay Zekâ Yardımcı</div>
  <div id="runlar">𐰜𐰇𐰞𐰏𐰤</div>
  <div id="baslikOrta">
    <svg class="egri" viewBox="0 0 640 70" aria-hidden="true"><path d="M8 8Q40 62 130 62H510Q600 62 632 8" fill="none" stroke="var(--ulgen-gold)" stroke-width="1.6"/></svg>
    <span class="yd"><svg class="i"><use href="#i-yildiz"/></svg></span><b>ÜLGEN</b><span class="yd"><svg class="i"><use href="#i-yildiz"/></svg></span>
    <small>Kişisel Yapay Zekâ Yardımcı</small></div>
  <div id="sagUst">
    <div class="ik" onclick="sekme('bildirim')" style="cursor:pointer"><svg class="i"><use href="#i-zil"/></svg><em id="zilSayi" style="display:none">0</em></div>
    <div class="ik" title="Mac sunucusu"><svg class="i"><use href="#i-ekran"/></svg><i id="macNokta"></i></div>
    <div class="ik" title="iPhone (son 24 saatte bağlandı mı)"><svg class="i"><use href="#i-tel"/></svg><i id="telNokta"></i></div>
      </div>
</div>
<div id="saatKutu"><div class="tk"><svg class="i"><use href="#i-takvim"/></svg><div><small id="tarihYazi"></small><b id="saatYazi"></b></div></div><div id="havaYazi"></div></div>
<header>
  <h1><span id="nokta" class="nokta"></span>ÜLGEN</h1>
  <span id="saat"></span>
  <button class="dugme" onclick="kodAcPencere()">&lt;/&gt; Kod</button>
  <button id="sesBtn" class="dugme aktif" onclick="sesDegistir()">Ses: açık</button>
  <button id="susBtn" class="dugme" onclick="hepsiniDurdur()">Sus</button>
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
<div id="ajanPanel">
  <div class="satir">
    <b style="flex:1">Ajan görevi</b>
    <button class="dugme" onclick="ajanKapat()">Kapat ✕</button>
  </div>
  <div class="satir">
    <select id="ajanSec"></select>
    <span style="font-size:12px;color:var(--soluk)" id="ajanAlan"></span>
  </div>
  <textarea id="ajanGorev" rows="10" maxlength="60000" spellcheck="false"
    placeholder="Görevi yazın. Ajan araştırıp bitirince sonucu sohbet sayfasında yayınlar."
    style="flex:1;padding:10px;border-radius:10px;font:inherit"></textarea>
  <div class="satir">
    <button class="dugme aktif" onclick="ajanGonder()">Görevi gönder</button>
    <span id="ajanDurum" style="font-size:12px;color:var(--soluk)"></span>
  </div>
</div>
<div id="baglanti">Bağlantı koptu; yeniden deneniyor…</div>
<div id="serit"></div>
<div id="icerik">
<div id="pGorevler" class="panel"></div>
<div id="pIlac" class="panel"></div>
<div id="pBildirim" class="panel"></div>
<div id="pKasa" class="panel"></div>
<div id="pSaglik" class="panel"></div>
<div id="pProjeler" class="panel"></div>
<div id="pAjanlar" class="panel"></div>
<div id="pBilgi" class="panel"></div>
<div id="pYz" class="panel"></div>
<div id="pAyarlar" class="panel"></div>
<div id="pSistem" class="panel"></div>
<section id="mobilAna">
  <div id="kareler">
    <button class="kare" onclick="sekme('sohbet')"><svg class="i"><use href="#i-sohbet"/></svg>Sohbet</button>
    <button class="kare" onclick="sekme('gorevler')"><svg class="i"><use href="#i-gorev"/></svg>Görevler<em class="rz" id="kGorev"></em></button>
    <button class="kare" onclick="sekme('ilac')"><svg class="i"><use href="#i-hap"/></svg>İlaçlar</button>
    <button class="kare" onclick="sekme('projeler')"><svg class="i"><use href="#i-katman"/></svg>Projeler</button>
    <button class="kare" onclick="sekme('ajanlar')"><svg class="i"><use href="#i-cip"/></svg>Ajanlar</button>
    <button class="kare" onclick="sekme('bilgi')"><svg class="i"><use href="#i-veri"/></svg>Hafıza</button>
    <button class="kare" onclick="sekme('yz')"><svg class="i"><use href="#i-cip"/></svg>Yapay Zekâ</button>
    <button class="kare" onclick="sekme('sistem')"><svg class="i"><use href="#i-ayar"/></svg>Sistem</button>
  </div>
  <div id="mobilOzet"></div>
</section>
<section id="sohbetKolon">
<div id="yaklasan"></div>
<div id="beyin" style="font-size:12px;color:var(--soluk);padding:2px 16px"></div>
<div id="akis"></div>
<div id="cipler">
  <button onclick="cipSec('Derinlemesine düşün: ')">Derin Düşün</button>
  <button onclick="cipSec('Araştır: ')">Araştır</button>
  <button onclick="cipSec('Planla: ')">Planla</button>
  <button onclick="cipSec('Proje: ')">Proje</button>
  <button onclick="cipSec('Hatırlat: ')">Hatırlat</button>
  <button onclick="cipSec('Not al: ')">Not Al</button>
  <button onclick="kodAcPencere()">Kod</button>
  <button onclick="ajanAc()">Ajan Görevi</button>
</div>
<div id="alt">
  <div id="mikSatir">
    <button id="klavyeBtn" class="yuvarlak" onclick="giriseOdak()" title="Yaz"><svg class="i"><use href="#i-klavye"/></svg></button>
    <span class="dalga" id="dalgaS"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></span>
    <button id="mikBtn" class="yuvarlak" onclick="mikrofon()" title="Konuş"><svg class="i"><use href="#i-mik"/></svg></button>
    <span class="dalga" id="dalga"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></span>
  </div>
  <div id="ekSatir" style="display:none;flex-wrap:wrap;gap:6px;padding:4px 8px"></div>
  <div id="yazSatir">
    <button id="ekBtn" class="yuvarlak" onclick="ekSec()" title="Dosya ya da resim ekle" style="font-size:18px">📎</button>
    <input id="ekDosya" type="file" multiple hidden
      accept="image/*,.pdf,.docx,.txt,.md,.csv,.json,.html,.htm,.log">
    <textarea id="giris" rows="1" placeholder="ÜLGEN'e yazın veya konuşun" onkeydown="tusla(event)"></textarea>
    <button class="yuvarlak gonder" onclick="gonder()" title="Gönder">➤</button>
  </div>
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

// Asistan yanıtındaki Markdown işaretlerini (#, **, -, >, `) biçime çevirir.
// innerHTML kullanılmaz: her parça metin düğümü olarak eklenir (güvenli).
function mdSatirIci(kap, satir) {
  const parca = satir.split(/(\*\*[^*]+\*\*|`[^`]+`)/);
  parca.forEach(p => {
    if (!p) return;
    if (/^\*\*[^*]+\*\*$/.test(p)) { const b = document.createElement("b"); b.textContent = p.slice(2, -2); kap.appendChild(b); }
    else if (/^`[^`]+`$/.test(p)) { const c = document.createElement("code"); c.textContent = p.slice(1, -1); kap.appendChild(c); }
    else kap.appendChild(document.createTextNode(p));
  });
}
function mdYaz(d, metin) {
  const satirlar = metin.split("\n");
  let kod = null;
  satirlar.forEach(s => {
    if (/^\s*```/.test(s)) {
      if (kod) { d.appendChild(kod); kod = null; }
      else { kod = document.createElement("pre"); kod.className = "mdKod"; }
      return;
    }
    if (kod) { kod.textContent += s + "\n"; return; }
    const e = document.createElement("div");
    let m;
    if ((m = s.match(/^\s*(#{1,6})\s+(.*)$/))) {
      e.className = "mdBaslik mdB" + Math.min(m[1].length, 3); mdSatirIci(e, m[2]);
    } else if ((m = s.match(/^\s*[-*•]\s+(.*)$/))) {
      e.className = "mdMadde"; mdSatirIci(e, m[1]);
    } else if ((m = s.match(/^\s*>\s?(.*)$/))) {
      e.className = "mdNot"; mdSatirIci(e, m[1]);
    } else if (!s.trim()) {
      e.className = "mdBos";
    } else mdSatirIci(e, s);
    d.appendChild(e);
  });
  if (kod) d.appendChild(kod);
}

function balonEkle(metin, tur) {
  const sat = document.createElement("div");
  sat.className = "sat " + (tur === "kullanici" ? "sk" : "sa");
  const av = document.createElement("span");
  av.className = "av" + (tur === "kullanici" ? "" : " ul");
  if (tur === "kullanici") av.textContent = "H";
  const d = document.createElement("div");
  d.className = "balon " + tur;
  if (tur === "kullanici") d.appendChild(document.createTextNode(metin));
  else mdYaz(d, String(metin || ""));
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

let konusmaNo = 0;

const DUR_DESENI = /^(ülgen[,.\s]+)?(dur|sus|kes|yeter|sessiz|sessiz ol|konuşma|tamam dur|dur artık|sus artık|dur ülgen|sus ülgen)[\s.!?]*$/i;

// Konuşmayı keser VE sunucuda süren sohbet/araştırma işini durdurur.
function hepsiniDurdur() {
  sesiDurdur();
  istek("/sohbet/iptal", {}).catch(() => {});
}

// Her şeyi susturur: yerel ses, bulut sesi, sıradaki parçalar.
function sesiDurdur() {
  konusmaNo++;
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  if (klipSes) { try { klipSes.pause(); } catch (e) {} }
}

// Uzun metni cümle sınırlarında ≤ 700 karakterlik parçalara böler (bulut sesi sınırı).
function parcalaMetin(metin) {
  const cumleler = metin.replace(/\s+/g, " ").trim().match(/[^.!?]+[.!?]*/g) || [metin];
  const sonuc = []; let o = "";
  for (let c of cumleler) {
    c = c.trim(); if (!c) continue;
    while (c.length > 700) { if (o) { sonuc.push(o); o = ""; } sonuc.push(c.slice(0, 700)); c = c.slice(700); }
    if ((o + " " + c).trim().length > 700) { sonuc.push(o); o = c; } else o = (o + " " + c).trim();
  }
  if (o) sonuc.push(o);
  return sonuc;
}

// Her yerde aynı ses: sabit cümle -> kendi klibi; bulut sesi açıksa tüm yanıt (parça parça) aynı sesle.
// Sayıyı Türkçe sözcüklere çevirir: 11842 -> "on bir bin sekiz yüz kırk iki".
// Ses motoru "100 11.842"yi "yüz on birinci" gibi yanlış birleştirmesin diye.
function sayiYazi(n) {
  const b = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"];
  const o = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"];
  const uc = x => { const y = Math.floor(x / 100), r = x % 100;
    return [y ? (y > 1 ? b[y] + " " : "") + "yüz" : "", o[Math.floor(r / 10)], b[r % 10]].filter(Boolean).join(" "); };
  const s = String(n).replace(/^0+(?=\d)/, "");
  if (s.length > 15) return s.split("").map(d => d === "0" ? "sıfır" : b[+d]).join(" ");
  let x = Number(s);
  if (x === 0) return "sıfır";
  const adlar = ["", "bin", "milyon", "milyar", "trilyon"];
  const parca = [];
  for (let i = 0; x > 0; i++, x = Math.floor(x / 1000)) {
    const g = x % 1000;
    if (!g) continue;
    parca.unshift(i === 1 && g === 1 ? "bin" : (uc(g) + (adlar[i] ? " " + adlar[i] : "")).trim());
  }
  return parca.join(" ");
}

// Seslendirmeden önce: kod, HTML etiketi, bağlantı ve Markdown işaretleri
// atılır; yoksa ses bunları harf harf okur.
function sesliMetin(m) {
  m = String(m || "");
  // Uzun raporlar (## bölümlü): yalnızca baştaki sade özet okunur; ayrıntı ekranda.
  const b = m.indexOf("\n## ");
  if (b > 40) m = m.slice(0, b) + "\nAyrıntılar ekranda.";
  // Yüzdeler Türkçe okunsun: "13.3%" / "%13,3" -> "yüzde 13 virgül 3"
  const yuzde = (isaret, tam, kesir) => " yüzde " + (isaret === "-" || isaret === "−" ? "eksi " : isaret === "+" ? "artı " : "") +
    tam.replace(/\./g, "") + (kesir ? " virgül " + kesir : "") + " ";
  // Binlik noktalı sayı: "11.842,82" -> "11842 virgül 82" (yoksa "11." sıra sayısı
  // gibi "on birinci" diye okunur). Ondalık virgül açıkça "virgül" okunur.
  m = m.replace(/(\d{1,3}(?:\.\d{3})+)(?:,(\d+))?(?!\d)/g, (_, t, k) => t.replace(/\./g, "") + (k ? " virgül " + k : ""))
       .replace(/(\d),(\d)/g, "$1 virgül $2");
  m = m.replace(/%\s?([+\-−]?)(\d{1,3}(?:\.\d{3})*|\d+)(?:,(\d+))?/g, (_, i, t, k) => yuzde(i, t, k))
       .replace(/([+\-−]?)(\d+)(?:[.,](\d+))?\s?%/g, (_, i, t, k) => yuzde(i, t, k));
  // Kalan bütün rakamlar sözcüğe: "BIST 100, 11842" -> "BIST yüz, on bir bin..."
  m = m.replace(/virgül (0+)(?=\d*)/g, (_, z) => "virgül " + "sıfır ".repeat(z.length))
       .replace(/\d+/g, d => " " + sayiYazi(d) + " ");
  return m.replace(/\s+([,.;:!?])/g, "$1").replace(/\s+/g, " ").trim()
    .replace(/```[\s\S]*?```/g, " (kod bölümü) ")
    .replace(/<[^>]+>/g, " ")
    .replace(/https?:\/\/\S+|www\.\S+/g, " (bağlantı) ")
    .replace(/&[a-zA-Z]+;|&#\d+;/g, " ")
    .replace(/^\s*[-•]\s+/gm, "")
    .replace(/[\u2500-\u257f\u2022\u25aa\u25cf]+/g, " ")   // kutu çizgileri ╔═║, madde imleri •
    .replace(/[#*_`|>~\[\]{}\\$]/g, " ")
    .replace(/\s+/g, " ").trim();
}

async function konus(metin) {
  if (!sesli) return;
  sesiDurdur();
  const no = konusmaNo;
  const ad = klipler[metin.replace(/\s+/g, " ").trim().toLowerCase()];
  if (ad) { if (!(await klipCal(ad))) yedekKonus(sesliMetin(metin)); return; }
  metin = sesliMetin(metin);
  if (!metin) return;
  if (!bulutSes) { yerelKonus(metin); return; }
  const parcalar = parcalaMetin(metin);
  for (let i = 0; i < parcalar.length; i++) {
    if (no !== konusmaNo) return;                       // araya "dur" girdi
    if (!(await bulutOku(parcalar[i], true))) {         // kota/ağ/hassas içerik: kalanı yerel sesle
      if (no === konusmaNo) { if (!/hassas/.test(sonBulutNeden)) bulutHataBildir(); yedekKonus(parcalar.slice(i).join(" "), true); }
      return;
    }
  }
}

// "Yalnız benim sesim": bulut sesi (kendi sesiniz) okuyamazsa kadın sistem sesine DÖNME, sessiz kal (yazı görünür).
function yalnizBenimSes() {
  try { return localStorage.getItem("ulgen_yalniz_ben") === "1"; } catch (e) { return false; }
}
function yedekKonus(metin, sirada) {
  if (yalnizBenimSes()) return;
  yerelKonus(metin, sirada);
}

function sesTercihi() {
  try { return JSON.parse(localStorage.getItem("ulgen_ses") || "{}"); } catch (e) { return {}; }
}

function yerelKonus(metin, sirada) {
  if (!("speechSynthesis" in window)) return;
  if (!sirada) speechSynthesis.cancel();
  const t = sesTercihi();
  const secili = t.ad ? speechSynthesis.getVoices().find(v => v.name === t.ad) : null;
  // Uzun metinler (sabah raporu) tek parça okununca tarayıcıda kesilir;
  // bu yüzden cümle cümle okunur.
  const parcalar = metin.replace(/\s+/g, " ").match(/[^.!?]+[.!?]*/g) || [metin];
  for (const p of parcalar) {
    if (!p.trim()) continue;
    const u = new SpeechSynthesisUtterance(p.trim());
    u.lang = "tr-TR";
    if (secili) u.voice = secili;
    u.rate = t.hiz || 0.95;
    u.pitch = t.perde || 0.8;
    speechSynthesis.speak(u);
  }
}

function sesDegistir() {
  sesli = !sesli;
  if (!sesli) sesiDurdur();
  const b = document.getElementById("sesBtn");
  b.textContent = "Ses: " + (sesli ? "açık" : "kapalı");
  b.classList.toggle("aktif", sesli);
}

// ---- sohbete dosya/resim ekleme
let bekleyenEkler = [];
function ekSec() { document.getElementById("ekDosya").click(); }
function ekleriCiz() {
  const k = document.getElementById("ekSatir");
  k.textContent = "";
  k.style.display = bekleyenEkler.length ? "flex" : "none";
  bekleyenEkler.forEach((e, i) => {
    const c = document.createElement("span");
    c.style.cssText = "background:var(--kart);border:1px solid var(--ulgen-ocean);border-radius:12px;padding:3px 8px;font-size:13px";
    c.textContent = "📎 " + e.ad + (e.karakter ? " (" + e.karakter + " karakter)" : "") + (e.not ? " – " + e.not : "") + " ";
    const x = document.createElement("button");
    x.textContent = "✕"; x.title = "Eki kaldır";
    x.style.cssText = "background:none;border:0;color:inherit;cursor:pointer";
    x.addEventListener("click", () => { bekleyenEkler.splice(i, 1); ekleriCiz(); });
    c.appendChild(x); k.appendChild(c);
  });
}
async function ekYukle() {
  const d = document.getElementById("ekDosya");
  const btn = document.getElementById("ekBtn");
  btn.disabled = true; btn.textContent = "⏳";
  for (const f of d.files) {
    try {
      const h = { "Content-Type": "application/octet-stream" };
      if (anahtar) h["Authorization"] = "Bearer " + anahtar;
      const r = await fetch("/ek/yukle?ad=" + encodeURIComponent(f.name), { method: "POST", headers: h, body: f });
      const y = await r.json();
      if (!r.ok) { balonEkle("Ek yüklenemedi (" + f.name + "): " + (y.hata || r.status), "asistan"); continue; }
      bekleyenEkler.push(y);
    } catch (e) { balonEkle("Ek yüklenemedi (" + f.name + "): " + e, "asistan"); }
  }
  d.value = ""; btn.disabled = false; btn.textContent = "📎";
  ekleriCiz();
  if (aktifSekme === "ana") sekme("sohbet");
  document.getElementById("giris").focus();
}
document.addEventListener("change", e => { if (e.target && e.target.id === "ekDosya") ekYukle(); });

async function gonder() {
  const g = document.getElementById("giris");
  const m = g.value.trim();
  g.value = "";
  const ekler = bekleyenEkler; bekleyenEkler = []; ekleriCiz();
  gonderMetin(m, ekler);
}

function menuAc() { document.body.classList.add("menuAcik"); }
function menuKapat() { document.body.classList.remove("menuAcik"); }
function giriseOdak() { sekme("sohbet"); document.getElementById("giris").focus(); }

async function gonderMetin(m, ekler) {
  ekler = ekler || [];
  if (window.innerWidth < 900 && aktifSekme === "ana") sekme("sohbet");
  if (!m && !ekler.length) return;
  balonEkle((m || "") + (ekler.length ? (m ? "\n" : "") + ekler.map(e => "📎 " + e.ad).join("\n") : ""), "kullanici");
  if (DUR_DESENI.test(m)) {
    hepsiniDurdur(); balonEkle("Sustum; süren iş varsa durduruyorum.", "asistan"); return;
  }
  try {
    const c = await istek("/sohbet", ekler.length ? { metin: m, ekler: ekler.map(e => e.kimlik) } : { metin: m });
    balonEkle((c.ajan ? "🤖 " + c.ajan + "\n\n" : "") + c.yanit, "asistan");
    beyinEtiketi(c.beyin);
    if (!/^İptal ettim/.test(c.yanit)) konus(c.yanit);
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
  document.body.classList.toggle("dinliyor", acik);
}

function dinleyiciBaslat() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { balonEkle("Bu tarayıcıda ses tanıma yok.", "asistan"); return; }
  const r = new SR();
  r.lang = "tr-TR";
  r.interimResults = true;                  // "dur" bitmeden, anında yakalansın
  r.continuous = surekli;
  let durYakalandi = -1;
  r.onresult = (e) => {
    const sira = e.results.length - 1;
    const son = e.results[sira];
    const ham = son[0].transcript.trim();
    // "dur" demek, ağırlıklı olarak konuşma sürerken: çağrı sözcüğü gerekmez
    if (DUR_DESENI.test(ham) && durYakalandi !== sira) {
      durYakalandi = sira; hepsiniDurdur();
      if (son.isFinal) balonEkle("Sustum; süren iş varsa durduruyorum.", "asistan");
      return;
    }
    if (!son.isFinal) return;
    const metin = ham;
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

// Çevrimdışı ses: Mac'te faster-whisper kuruluysa kayıt yerel olarak metne çevrilir
// (ses internete çıkmaz). Kurulu değilse tarayıcının kendi tanıması kullanılır.
let cevrimdisiSes = false, kayitci = null;
async function sesDurumuYukle() {
  try { cevrimdisiSes = !!(await istek("/ses/durum")).cevrimdisi; } catch (e) { cevrimdisiSes = false; }
  try { klipler = await istek("/ses/klipler"); } catch (e) { klipler = {}; }
  try { bulutSes = !!(await istek("/ses/durum")).bulut; } catch (e) { bulutSes = false; }
}
let bulutSes = false;
// Tek, yeniden kullanılan ses öğesi: Safari/Chrome ilk kullanıcı dokunuşunda "kilidi açılan" öğeyi sonradan,
// dokunuş olmadan da çalmaya izin verir. Her seferinde yeni Audio() oluşturmak engelleniyordu ve kadın sesine düşülüyordu.
const sesKap = new Audio();
let sesKilidiAcik = false, sonBulutNeden = "", sonBulutBildirim = 0;
function sessizWav() {
  const n = 800, b = new ArrayBuffer(44 + n * 2), v = new DataView(b);
  const y = (o, t) => { for (let i = 0; i < t.length; i++) v.setUint8(o + i, t.charCodeAt(i)); };
  y(0, "RIFF"); v.setUint32(4, 36 + n * 2, true); y(8, "WAVEfmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, 8000, true); v.setUint32(28, 16000, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); y(36, "data"); v.setUint32(40, n * 2, true);
  return URL.createObjectURL(new Blob([b], { type: "audio/wav" }));
}
function sesKilidiniAc() {
  if (sesKilidiAcik) return;
  try {
    sesKap.src = sessizWav();
    const p = sesKap.play();
    if (p && p.then) p.then(() => { sesKilidiAcik = true; }).catch(() => {});
  } catch (e) {}
}
["pointerdown", "keydown", "touchstart"].forEach(o => document.addEventListener(o, sesKilidiniAc, { passive: true }));

function sesCal(url, bitenKadar) {
  return new Promise(async (coz) => {
    klipSes = sesKap;
    const son = () => { try { URL.revokeObjectURL(url); } catch (e) {} };
    sesKap.onended = () => { son(); coz(true); };
    sesKap.onpause = () => { coz(true); };
    sesKap.onerror = () => { sonBulutNeden = "ses dosyası çalınamadı"; son(); coz(false); };
    try { sesKap.src = url; await sesKap.play(); if (!bitenKadar) coz(true); }
    catch (e) { sonBulutNeden = "tarayıcı sesi çalmayı engelledi (" + (e && e.name ? e.name : "hata") + ")"; son(); coz(false); }
  });
}

// Kendi sesiniz çalınamayınca nedenini (en çok 10 dakikada bir) sohbette gösterir: sessizce kadın sesine düşülmez.
function bulutHataBildir() {
  if (Date.now() - sonBulutBildirim < 600000) return;
  sonBulutBildirim = Date.now();
  balonEkle("Kendi sesiniz çalınamadı: " + (sonBulutNeden || "bilinmeyen neden") + (yalnizBenimSes() ? ". Yanıt yazı olarak kaldı." : ". Bu yanıt sistem sesiyle okunuyor."), "asistan");
}

// Bulut sesi açıksa (ElevenLabs, kendi sesiniz) yanıt metni oraya gider; olmazsa yerel ses okur.
async function bulutOku(metin, bitenKadar) {
  sonBulutNeden = "";
  try {
    const h = { "Content-Type": "application/json" }; if (anahtar) h["Authorization"] = "Bearer " + anahtar;
    const c = await fetch("/ses/oku", { method: "POST", headers: h, body: JSON.stringify({ metin: metin }) });
    if (!c.ok) {
      let m = ""; try { m = (await c.json()).hata || ""; } catch (e) {}
      sonBulutNeden = m || ("sunucu yanıtı " + c.status); return false;
    }
    return await sesCal(URL.createObjectURL(await c.blob()), bitenKadar);
  } catch (e) { sonBulutNeden = "ağ hatası"; return false; }
}
// Kendi sesiniz (ElevenLabs'ten bir kez üretilmiş, yerelde saklı) sabit cümleler için çalınır.
let klipler = {}, klipSes = null;
async function klipCal(ad) {
  try {
    const h = anahtar ? { "Authorization": "Bearer " + anahtar } : {};
    const c = await fetch("/ses/klip/" + ad, { headers: h });
    if (!c.ok) return false;
    return await sesCal(URL.createObjectURL(await c.blob()), false);
  } catch (e) { return false; }
}
async function cevrimdisiKayit() {
  if (kayitci) { kayitci.stop(); return; }
  let akim;
  try { akim = await navigator.mediaDevices.getUserMedia({ audio: true }); }
  catch (e) { balonEkle("Mikrofon izni verilmedi.", "asistan"); return; }
  const parca = [];
  kayitci = new MediaRecorder(akim);
  kayitci.ondataavailable = (e) => parca.push(e.data);
  kayitci.onstop = async () => {
    akim.getTracks().forEach(t => t.stop());
    const k = kayitci; kayitci = null; dinleyiciGorunum(false);
    const blob = new Blob(parca, { type: k.mimeType || "audio/mp4" });
    try {
      const h = { "Content-Type": blob.type || "audio/mp4" };
      if (anahtar) h["Authorization"] = "Bearer " + anahtar;
      const c = await fetch("/ses/yaz", { method: "POST", headers: h, body: blob });
      const v = await c.json();
      if (!c.ok) { balonEkle(v.hata || "Ses çözülemedi.", "asistan"); return; }
      if (v.metin) gonderMetin(v.metin);
      else balonEkle("Bir şey duyamadım.", "asistan");
    } catch (e) { balonEkle("Ses gönderilemedi.", "asistan"); }
  };
  dinleyiciGorunum(true);
  kayitci.start();
  setTimeout(() => { if (kayitci && kayitci.state === "recording") kayitci.stop(); }, 20000);
}

function mikrofon() {
  if (cevrimdisiSes) { cevrimdisiKayit(); return; }
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
      if (b.eylem && b.eylem.tur === "ajan_sonuc") {
        balonEkle(b.metin, "asistan");
        continue;
      }
      balonEkle("⏰ " + b.metin, "bildirim");
      gecmisBildirim.push({ metin: b.metin, saat: new Date().toLocaleTimeString("tr-TR") });
      if (aktifSekme === "bildirim") bildirimCiz();
      if (b.eylem && b.eylem.tur === "doz") dozDugmeleri(b.eylem.doz);
      const yerel = ["127.0.0.1", "localhost"].includes(location.hostname);
      if (!(yerel && b.eylem && b.eylem.sunucu_sesi)) konus(b.metin);
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
  resimEkle(p, "pusula", "pus");
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
const paneller = { gorevler: "pGorevler", ilac: "pIlac", bildirim: "pBildirim", kasa: "pKasa", saglik: "pSaglik", projeler: "pProjeler", ajanlar: "pAjanlar", bilgi: "pBilgi", yz: "pYz", ayarlar: "pAyarlar", sistem: "pSistem" };
const gecmisBildirim = [];
let aktifSekme = "ana";

const sohbetli = ad => ad === "ana" || ad === "sohbet";
function sekme(ad, geriden) {
  menuKapat();
  if (!geriden && ad !== aktifSekme) { try { history.pushState({ s: ad }, ""); } catch (e) {} }
  aktifSekme = ad;
  document.body.dataset.s = ad;
  document.querySelectorAll("#sekmeler button").forEach(b => b.classList.toggle("aktif", b.dataset.s === ad));
  for (const [k, id] of Object.entries(paneller)) document.getElementById(id).classList.toggle("acik", k === ad);
  if (sohbetli(ad)) panoYenile(); else panelYenile(ad);
}
document.body.dataset.s = "ana";
window.addEventListener("popstate", e => sekme((e.state && e.state.s) || "ana", true));

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
function resimEkle(kap, ad, sinif) {
  const i = document.createElement("img"); i.src = "/varlik/" + ad + ".webp"; i.alt = ""; i.className = sinif; kap.appendChild(i); return i;
}
function uykuYazi(dk) { return dk === null || dk === undefined ? "—" : Math.floor(dk / 60) + "s " + (dk % 60) + "dk"; }
function cubuk(oran, renk) { const c = document.createElement("div"); c.className = "cubuk" + (renk ? " " + renk : "");
  const i = document.createElement("i"); i.style.width = Math.max(0, Math.min(100, oran)) + "%"; c.appendChild(i); return c; }
function satirS(kap, a, b, sinif, rozet) { const r = document.createElement("div"); r.className = "s";
  const x = document.createElement("span");
  if (rozet) { const z = document.createElement("span"); z.className = "rozet"; z.style.background = rozet[1]; z.textContent = rozet[0]; x.appendChild(z); }
  x.appendChild(document.createTextNode(a)); const y = document.createElement("span"); y.textContent = b;
  if (sinif) y.className = sinif; r.appendChild(x); r.appendChild(y); kap.appendChild(r); }
const ROZET = { gemini: ["G", "#3b7de0"], nvidia: ["N", "#5aa100"], groq: ["g", "#e0442a"], mistral: ["M", "#f08a1c"],
                openrouter: ["O", "var(--ulgen-muted)"], ollama: ["O", "var(--ulgen-muted)"], "llama.cpp": ["L", "var(--ulgen-muted)"] };
function rozetBul(ad) { const k = ad.toLowerCase(); for (const a in ROZET) if (k.indexOf(a) >= 0) return ROZET[a]; return [ad[0] || "?", "#5a6478"]; }

function rozetYaz(g, il) {
  const acik = g.gorev.length;
  for (const id of ["rzGorev", "kGorev"]) { const e = document.getElementById(id); if (e) { e.textContent = acik; e.classList.toggle("var", acik > 0); } }
}
function ozetKarti(kap, g, il, ek) {
  const alinan = il.filter(x => x.durum === "alindi" || x.durum === "tamamlandi").length;
  const yuzde = il.length ? Math.round(100 * alinan / il.length) : 0;
  const k0 = kartK(kap, "Günün Özeti", [g.gorev.length + " görev • " + il.length + " ilaç • " + g.randevu.length + " randevu"], "takvim", ek || "", "gorevler");
  const oc = document.createElement("div"); oc.className = "ozetCubuk"; oc.appendChild(cubuk(yuzde));
  const yz = document.createElement("span"); yz.textContent = "%" + yuzde; oc.appendChild(yz); k0.appendChild(oc);
}
function ilacKarti(kap, il) {
  const k1 = kartK(kap, "İlaç Takvimi (Bugün)", [], "hap", "", "ilac");
  if (!il.length) satirS(k1, "Bugün doz yok", "");
  il.forEach(x => satirS(k1, "D" + x.id + " – " + x.ilac_ad, x.planli.slice(11, 16) + " " + durumYazi[x.durum].split(" ")[0],
    x.durum === "alindi" ? "ok" : (x.durum === "bekliyor" ? "bekle" : "")));
}

async function panoYenile() {
  try {
    if (window.innerWidth < 900) {
      const [g, il, sis] = await Promise.all([panoIstek("/gorevler"), panoIstek("/ilac/bugun"), panoIstek("/sistem")]);
      rozetYaz(g, il);
      document.getElementById("surumRozet").textContent = "v" + sis.surum;
      const m = document.getElementById("mobilOzet"); m.replaceChildren();
      ozetKarti(m, g, il); ilacKarti(m, il);
      return;
    }
    const [g, il, sis] = await Promise.all([panoIstek("/gorevler"), panoIstek("/ilac/bugun"), panoIstek("/sistem")]);
    rozetYaz(g, il);
    document.getElementById("surumRozet").textContent = "v" + sis.surum;
    const serit = document.getElementById("serit"); serit.replaceChildren();
    const alinan = il.filter(x => x.durum === "alindi" || x.durum === "tamamlandi").length;
    const bek = il.filter(x => x.durum === "bekliyor" || x.durum === "ertelendi" || x.durum === "yanitsiz").length;
    const acik = g.gorev.length;
    const yuzde = il.length ? Math.round(100 * alinan / il.length) : 0;
    const k0 = kartK(serit, "Günün Özeti", [acik + " görev · " + il.length + " ilaç · " + g.randevu.length + " randevu"], "takvim", "", "gorevler");
    const oc = document.createElement("div"); oc.className = "ozetCubuk"; oc.appendChild(cubuk(yuzde));
    const yz = document.createElement("span"); yz.textContent = "%" + yuzde; oc.appendChild(yz); k0.appendChild(oc);
    kartK(serit, "İlaçlar", bek ? bek + " bekleyen doz" : "Bekleyen doz yok", "hap", bek ? " uyari" : "", "ilac");
    kartK(serit, "Görevler", acik ? acik + " tamamlanmamış" : "Açık görev yok", "gorev", acik ? " uyari" : "", "gorevler");
    // Sağlık kartı yerine Ajanlar: kaç ajan var, hangisi çalışıyor, son iş
    const aj = await panoIstek("/ajanlar");
    const uzm = aj.filter(a => a.tur === "uzman").length;
    const calisan = aj.filter(a => a.durum === "calisiyor").map(a => a.ad.split(" – ")[0]);
    const sonlar = aj.filter(a => a.son_calisma).sort((a, b) => String(b.son_calisma).localeCompare(String(a.son_calisma)));
    kartK(serit, "Ajanlar", [(aj.length - uzm) + " genel • " + uzm + " uzman",
      calisan.length ? "Çalışıyor: " + calisan.join(", ") :
        (sonlar.length ? "Son: " + sonlar[0].ad.split(" – ")[0] + " " + String(sonlar[0].son_calisma).slice(11, 16) : "Şu an boşta")],
      "cip", calisan.length ? " uyari" : "", "ajanlar");
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
    const k5 = kartK(p1, "Ajanlar ve Uzmanlar", [], "cip", "", "ajanlar");
    try {
      const uz = await panoIstek("/uzmanlar");
      uz.genel.forEach(x => satirS(k5, x.ad + " – " + x.is, x.yer));
      uz.uzmanlar.forEach(x => satirS(k5, x.ad, x.alan));
    } catch (e) { satirS(k5, "Liste alınamadı", ""); }
    const k3 = kartK(p2, "Yapay Zekâ Modelleri", [], "katman");
    const aktif = ((sis.beyin && sis.beyin.beyin) || "").toLowerCase();
    sis.kota.forEach(t => {
      const durum = (t.yerel && t.ulasilir === false) ? "Kapalı" : t.engelli ? (t.yerel ? "Çevrimdışı" : "Engelli") : (aktif && aktif.indexOf(t.ad.toLowerCase().split(" ")[0]) >= 0 ? "Aktif" : "Hazır");
      satirS(k3, t.ad, durum, durum === "Hazır" || durum === "Aktif" ? "ok" : "", rozetBul(t.ad));
    });
    const k4 = kartK(p2, "Sistem Durumu", [], "ayar");
    const d = sis.donanim || {};
    if (d.cpu !== undefined) { satirS(k4, "CPU", Math.round(d.cpu) + "%"); k4.appendChild(cubuk(d.cpu, "yes")); }
    if (d.ram_toplam) { satirS(k4, "RAM", d.ram_kullanilan + " / " + d.ram_toplam + " GB (%" + Math.round(100 * d.ram_kullanilan / d.ram_toplam) + ")"); k4.appendChild(cubuk(100 * d.ram_kullanilan / d.ram_toplam)); }
    if (d.disk_toplam) { satirS(k4, "Disk", d.disk_kullanilan + " / " + d.disk_toplam + " GB (%" + Math.round(100 * d.disk_kullanilan / d.disk_toplam) + ")"); k4.appendChild(cubuk(100 * d.disk_kullanilan / d.disk_toplam, "mor")); }
    const ok = document.createElement("div"); ok.style.cssText = "margin-top:8px;color:var(--yesil);font-size:13px";
    ok.textContent = sis.butunluk.saglam ? "✓ Tüm sistemler normal çalışıyor." : "! Veritabanı bütünlüğü sorunlu"; k4.appendChild(ok);
  } catch (e) {
    console.error("panoYenile", e);
    const kutu = document.getElementById("serit") || document.getElementById("mobilOzet");
    if (kutu) { kutu.replaceChildren(); const d = document.createElement("div"); d.className = "kart";
      d.style.cssText = "padding:14px;color:var(--ulgen-danger)";
      d.textContent = "Pano yüklenemedi: " + (e && e.message ? e.message : e) + " — Launchpad'deki Ülgen simgesiyle yeniden açın."; kutu.appendChild(d); }
  }
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
  const rb = document.getElementById("rzBildirim"); rb.textContent = gecmisBildirim.length; rb.classList.toggle("var", gecmisBildirim.length > 0);
}
async function havaYukle() {
  try {
    // Cihazın konumu (izin verilirse); olmazsa ayardaki varsayılan yer kullanılır.
    const konum = await new Promise(coz => {
      if (!navigator.geolocation) { coz(null); return; }
      navigator.geolocation.getCurrentPosition(p => coz(p.coords), () => coz(null),
        { timeout: 8000, maximumAge: 1800000, enableHighAccuracy: false });
    });
    const h = await istek(konum ? "/hava?enlem=" + konum.latitude.toFixed(2) + "&boylam=" + konum.longitude.toFixed(2) : "/hava");
    const k = document.getElementById("havaYazi");
    if (!h || h.sicaklik === undefined) { k.textContent = ""; return; }
    k.innerHTML = '<svg class="i"><use href="#i-gunes"/></svg><div><b></b><span></span></div>';
    k.querySelector("b").textContent = h.ad + " • " + h.sicaklik + "°C"; k.querySelector("span").textContent = h.durum;
  } catch (e) { /* hava isteğe bağlıdır */ }
}
setTimeout(sesDurumuYukle, 1200); setTimeout(havaYukle, 800); setInterval(havaYukle, 1800000);
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
    else if (ad === "saglik") await saglikCiz();
    else if (ad === "projeler") await projelerCiz();
    else if (ad === "ajanlar") await ajanlarCiz();
    else if (ad === "bilgi") await bilgiCiz();
    else if (ad === "yz") await yzCiz();
    else if (ad === "ayarlar") await ayarCiz();
  } catch (e) { /* bağlantı uyarısı zaten gösteriliyor */ }
}

async function saglikCiz() {
  const k = document.getElementById("pSaglik"); k.innerHTML = "";
  const [b, h] = await Promise.all([istek("/saglik/bugun"), istek("/saglik/gecmis")]);
  baslik(k, "Bugün");
  if (!b.veri_var) ekle(k, "Henüz veri yok.", "iPhone Kestirmesi kurulunca adım, nabız ve uyku buraya gelir (SAGLIK_KESTIRME.md).");
  else {
    ekle(k, "Adım: " + (b.adim === null ? "—" : b.adim.toLocaleString("tr-TR")));
    ekle(k, "Son nabız: " + (b.nabiz === null ? "—" : b.nabiz + " atım/dk"), b.nabiz_zaman || "");
    ekle(k, "Uyku: " + uykuYazi(b.uyku_dk));
  }
  baslik(k, "Son 7 gün");
  if (!h.length) ekle(k, "Kayıt yok.");
  h.forEach(g => ekle(k, g.gun + "  ·  adım " + (g.adim === null ? "—" : Math.round(g.adim)) + "  ·  ort. nabız " + (g.nabiz === null ? "—" : Math.round(g.nabiz)) +
    "  ·  uyku " + uykuYazi(g.uyku === null ? null : Math.round(g.uyku))));
  ekle(k, "Bu veriler yalnızca Mac'inizde durur, buluta gönderilmez. Ülgen tıbbi öneri vermez.");
}

// Pano istekleri: sunucu hata gövdesi dönerse (ör. 429, 403) hangi istekte olduğunu açıkça söyler.
async function panoIstek(yol) {
  const j = await istek(yol);
  if (j && !Array.isArray(j) && typeof j === "object" && j.hata) throw new Error(yol + " → " + j.hata);
  return j;
}
let ajanZamani = null;
async function ajanlarCiz() {
  const k = document.getElementById("pAjanlar");
  const liste = await istek("/ajanlar");
  k.replaceChildren();
  baslik(k, "Ajanlar");
  const not = document.createElement("div"); not.style.cssText = "font-size:12px;color:var(--soluk);margin-bottom:8px";
  not.textContent = "Ajanlar sohbetten de çalışır; her çalıştırma burada görünür. Araştırma ajanı, bir uzmanın alanına giren görevi o uzmana devreder. Sağlık ajanı tıbbi öneri vermez.";
  k.appendChild(not);
  let uzmanBaslik = false;
  const durumYazi = { bosta: "Boşta", calisiyor: "Çalışıyor…", hata: "Hata" };
  let calisan = false;
  liste.forEach(a => {
    if (a.durum === "calisiyor") calisan = true;
    if (a.tur === "uzman" && !uzmanBaslik) {
      uzmanBaslik = true;
      const h = document.createElement("h3"); h.textContent = "Alan uzmanları"; h.style.cssText = "margin:16px 0 8px";
      k.appendChild(h);
    }
    const kart = document.createElement("div"); kart.className = "kartK"; kart.style.marginBottom = "10px";
    const ust = document.createElement("div"); ust.className = "ust";
    ust.innerHTML = '<svg class="i"><use href="#i-cip"/></svg>';
    const b = document.createElement("b"); b.textContent = a.ad; ust.appendChild(b);
    const d = document.createElement("span"); d.style.cssText = "margin-left:auto;font-size:12px;color:" + (a.durum === "hata" ? "var(--ulgen-danger)" : "var(--soluk)");
    d.textContent = durumYazi[a.durum] || a.durum; ust.appendChild(d);
    kart.appendChild(ust);
    const ne = document.createElement("div"); ne.textContent = a.ne; kart.appendChild(ne);
    const son = document.createElement("div"); son.style.cssText = "font-size:12px;color:var(--soluk);margin-top:4px";
    son.textContent = a.son_calisma ? ("Son çalışma: " + a.son_calisma + " · " + a.sure_sn + " sn · " + a.sayac + " kez") : "Henüz çalışmadı.";
    kart.appendChild(son);
    if (a.hata) { const h = document.createElement("div"); h.style.cssText = "color:var(--ulgen-danger);font-size:13px;margin-top:4px"; h.textContent = "Hata: " + a.hata; kart.appendChild(h); }
    if (a.ozet) { const o = document.createElement("div"); o.style.cssText = "font-size:13px;margin-top:6px;white-space:pre-wrap"; o.textContent = a.ozet; kart.appendChild(o); }
    const satir = document.createElement("div"); satir.style.cssText = "display:flex;gap:8px;margin-top:8px;flex-wrap:wrap";
    let girdi = null;
    if (a.girdi) {
      const uzun = a.id === "arastirma";
      girdi = document.createElement(uzun ? "textarea" : "input"); girdi.placeholder = a.girdi;
      if (uzun) { girdi.rows = 4; girdi.maxLength = 60000; } else { girdi.maxLength = 300; }
      girdi.style.cssText = "flex:1;min-width:160px;padding:8px;border-radius:10px;border:1px solid var(--kenar);background:var(--kart);color:var(--yazi);font:inherit";
      satir.appendChild(girdi); }
    const dg = document.createElement("button"); dg.className = "dugme aktif"; dg.textContent = "Şimdi çalıştır";
    dg.disabled = a.durum === "calisiyor";
    dg.onclick = async () => {
      if ((a.id === "arastirma" || a.tur === "uzman") && !(girdi && girdi.value.trim())) { girdi.focus(); return; }
      dg.disabled = true;
      try { const y = await istek("/ajanlar/calistir", { id: a.id, girdi: girdi ? girdi.value : "" });
        if (y && y.hata) alert("Ajan başlatılamadı: " + y.hata);
        else if (a.tur === "uzman") balonEkle("Görev " + a.ad + " uzmanına verildi. Bitince sonucu sohbette yayınlayacak.", "asistan"); }
      catch (e) { alert("Ajan başlatılamadı: " + (e.message || e)); }
      ajanlarCiz();
    };
    satir.appendChild(dg);
    if (a.id === "kitap") {
      const yb = document.createElement("button"); yb.className = "dugme"; yb.textContent = "PDF / resim yükle";
      const dsy = document.createElement("input"); dsy.type = "file"; dsy.multiple = true;
      dsy.accept = ".pdf,.png,.jpg,.jpeg,.tif,.tiff,.bmp"; dsy.style.display = "none";
      yb.onclick = () => dsy.click();
      dsy.onchange = async () => {
        yb.disabled = true; let tamam = 0;
        for (const f of dsy.files) {
          yb.textContent = "Yükleniyor: " + f.name;
          try {
            const h = { "Content-Type": "application/octet-stream" };
            if (anahtar) h["Authorization"] = "Bearer " + anahtar;
            const r = await fetch("/kitap/yukle?ad=" + encodeURIComponent(f.name), { method: "POST", headers: h, body: f });
            const j = await r.json();
            if (j.hata) { alert(f.name + ": " + j.hata); } else { tamam++; }
          } catch (e) { alert(f.name + " yüklenemedi: " + (e.message || e)); }
        }
        yb.disabled = false; yb.textContent = "PDF / resim yükle";
        if (tamam) { alert(tamam + " dosya yüklendi. Okumaya başlamak için 'Şimdi çalıştır'a basın (girdi boş)."); }
      };
      satir.appendChild(yb); satir.appendChild(dsy);
    }
    kart.appendChild(satir); k.appendChild(kart);
  });
  clearTimeout(ajanZamani);
  if (calisan && aktifSekme === "ajanlar") ajanZamani = setTimeout(() => { if (aktifSekme === "ajanlar") ajanlarCiz().catch(() => {}); }, 3000);
}

async function projelerCiz() {
  const k = document.getElementById("pProjeler"); k.innerHTML = "";
  const p = await istek("/projeler");
  baslik(k, "Hafıza projeleri");
  if (!p.hafiza.length) ekle(k, "Proje yok. Sohbete yazın: proje ekle: Ad");
  p.hafiza.forEach(a => ekle(k, a));
  baslik(k, "Kod dosyaları");
  if (!p.kod.length) ekle(k, "Kayıtlı kod dosyası yok.");
  p.kod.forEach(a => { const d = ekle(k, typeof a === "string" ? a : (a.ad || JSON.stringify(a)));
    const b = document.createElement("button"); b.className = "dugme"; b.style.marginLeft = "8px"; b.textContent = "Kod penceresinde aç";
    const ad = typeof a === "string" ? a : a.ad;
    b.onclick = () => { kodAcPencere(); setTimeout(() => { document.getElementById("kodDosya").value = ad; kodAc(); }, 400); };
    d.appendChild(b); });
  const y = document.createElement("button"); y.className = "dugme aktif"; y.style.marginTop = "10px"; y.textContent = "Yeni kod dosyası";
  y.onclick = kodAcPencere; k.appendChild(y);
}

async function bilgiCiz() {
  const k = document.getElementById("pBilgi"); k.innerHTML = "";
  baslik(k, "Hafıza ve Obsidian notlarında ara");
  const g = document.createElement("input"); g.placeholder = "Ne arıyorsunuz?"; g.style.cssText = "width:100%;padding:10px;border-radius:10px;border:1px solid var(--kenar);background:var(--kart);color:var(--yazi)";
  k.appendChild(g);
  const sonuc = document.createElement("div"); k.appendChild(sonuc);
  const ara = async () => {
    const r = await istek("/bilgi/ara?q=" + encodeURIComponent(g.value));
    sonuc.innerHTML = "";
    baslik(sonuc, "Notlar (Obsidian)");
    if (!r.dizin.hazir) ekle(sonuc, "Not dizini hazır değil.");
    else if (!r.dizin.erisim) ekle(sonuc, "Obsidian kasasına ulaşılamıyor", r.dizin.ileti);
    else if (!g.value) ekle(sonuc, "Aramak için yazın. Kasa: " + r.dizin.kasa, r.dizin.dosya + " not dosyası, " + r.dizin.dizinli + " tanesi dizinlendi.");
    else if (!r.notlar.length) ekle(sonuc, "Eşleşen not yok.");
    r.notlar.forEach(n => ekle(sonuc, n.baslik, n.alinti));
    baslik(sonuc, "Hafıza");
    if (!r.hafiza.length) ekle(sonuc, "Kayıt yok.");
    r.hafiza.forEach(h => ekle(sonuc, h.metin, h.kategori));
  };
  g.addEventListener("input", () => { clearTimeout(g._z); g._z = setTimeout(ara, 300); });
  await ara();
}

async function yzCiz() {
  const s = await istek("/sistem"); const k = document.getElementById("pYz"); k.innerHTML = "";
  resimEkle(k, "kure", "sus");
  baslik(k, "Yapay zekâ modelleri (ücretsiz katmanlar, maliyet 0)");
  ekle(k, "Şu an kullanılan: " + (s.beyin.beyin || "yok"), "Kuyrukta bekleyen istek: " + s.kuyruk);
  s.kota.forEach(t => { const e = t.tahmini;
    ekle(k, t.ad + " — " + (t.engelli ? "ENGELLİ: " + t.neden : "kullanılabilir"),
      "bugün " + e.istek_gun + " istek, ~" + e.token_gun + " token; gecikme " + e.gecikme_ms + " ms; hata %" + Math.round(t.hata_orani * 100)); });
  if (!yerel) { ekle(k, "Anahtar eklemek güvenlik için yalnızca Mac'in kendi tarayıcısından yapılır."); return; }
  await beyinKipi(k);
  await beyinAcKapat(k);
  await anahtarlarim(k);
  await ozelSaglayicilar(k);
}

// Listede olmayan bir yapay zekâ servisi eklemek (OpenAI uyumlu her servis)
async function ozelSaglayicilar(k) {
  baslik(k, "Yeni sağlayıcı ekle");
  let d = { liste: [], ornekler: [] };
  try { d = await istek("/yz/ozel", { islem: "liste" }); } catch (e) { ekle(k, "Özel sağlayıcılar okunamadı."); return; }
  d.liste.forEach(t => {
    const satir = ekle(k, t.baslik + " — " + (t.yerel ? "yerel (bu Mac)" : "bulut") + " · " + t.model,
      t.taban + "  ·  " + (t.anahtar_var ? "anahtar VAR …" + t.son4 : (t.yerel ? "anahtarsız" : "anahtar YOK")) +
      "  ·  " + (t.yerel || t.ucretsiz ? (t.acik ? "kullanılıyor" : "kapalı") : "ÜCRETLİ: Ülgen kendiliğinden kullanmaz"));
    satir.style.borderLeft = "3px solid " + ((t.yerel || t.ucretsiz) && t.acik ? "var(--ulgen-success)" : "var(--ulgen-offline)");
    const dugme = (yazi, tehlike) => { const b = document.createElement("button"); b.className = "dugme"; b.textContent = yazi;
      b.style.cssText = "margin:6px 6px 0 0" + (tehlike ? ";border-color:var(--ulgen-danger);color:var(--ulgen-danger)" : ""); satir.appendChild(b); return b; };
    const de = dugme("Bağlantıyı dene");
    de.onclick = async () => { de.disabled = true; balonEkle("Deneniyor: " + t.baslik + "…", "asistan");
      try { const c = await istek("/yz/ozel", { islem: "dene", ad: t.ad }); balonEkle((c.calisti ? "✔ " : "✘ ") + (c.cikti || c.hata || "Yanıt yok."), "asistan"); }
      finally { de.disabled = false; } };
    const ak = dugme(t.acik ? "Kapat" : "Aç");
    ak.onclick = async () => { const c = await istek("/yz/saglayici", { saglayici: t.ad, acik: !t.acik }); if (c.hata) balonEkle(c.hata, "asistan"); yzCiz(); };
    const si = dugme("Sil", true);
    si.onclick = async () => { if (!confirm(t.baslik + " ve anahtarı bu Mac'ten silinecek. Emin misiniz?")) return;
      const c = await istek("/yz/ozel", { islem: "sil", ad: t.ad, onay: true }); balonEkle(c.hata || t.baslik + " silindi.", "asistan"); yzCiz(); };
  });
  const kap = ekle(k, "Listede olmayan bir servis ekleyin",
    "OpenAI uyumlu her servis olur. Anahtar Mac'in Anahtar Zinciri'ne yazılır. 'Ücretsiz' işaretlemezseniz Ülgen bu servise kendiliğinden geçmez.");
  const st = "width:100%;margin:4px 0;padding:9px;border-radius:10px;border:1px solid var(--kenar);background:var(--ulgen-navy);color:var(--yazi)";
  const alan = (ph, tur) => { const e = document.createElement("input"); e.type = tur || "text"; e.autocomplete = "off"; e.placeholder = ph; e.style.cssText = st; kap.appendChild(e); return e; };
  const sec = document.createElement("select"); sec.className = "dugme"; sec.style.cssText = "max-width:100%;margin-top:6px";
  const bos = document.createElement("option"); bos.value = ""; bos.textContent = "Hazır örnekten doldur…"; sec.appendChild(bos);
  d.ornekler.forEach((o, i) => { const e = document.createElement("option"); e.value = i; e.textContent = o.baslik; sec.appendChild(e); });
  kap.appendChild(sec);
  const ad = alan("Ad (örn. DeepSeek)"), taban = alan("Adres (örn. https://api.deepseek.com/v1)"),
    model = alan("Model (örn. deepseek-chat)"), anahtar = alan("API anahtarı (bu Mac'teki LM Studio için boş bırakılabilir)", "password");
  sec.onchange = () => { const o = d.ornekler[sec.value]; if (!o) return; ad.value = o.baslik; taban.value = o.taban; model.value = o.model; };
  const et = document.createElement("label"); et.style.cssText = "display:block;margin:6px 0;font-size:14px";
  const ucr = document.createElement("input"); ucr.type = "checkbox"; et.appendChild(ucr);
  et.appendChild(document.createTextNode(" Bu servis ücretsiz (Ülgen sırası gelince kendiliğinden kullanabilir)"));
  kap.appendChild(et);
  const so = document.createElement("div"); so.style.cssText = "font-size:12px;color:var(--soluk)";
  const kay = document.createElement("button"); kay.className = "dugme aktif"; kay.textContent = "Ekle";
  kay.onclick = async () => {
    kay.disabled = true;
    const c = await istek("/yz/ozel", { islem: "ekle", baslik: ad.value, taban: taban.value, model: model.value, anahtar: anahtar.value, ucretsiz: ucr.checked });
    anahtar.value = "";
    if (c.tamam) { balonEkle(ad.value + " eklendi. 'Bağlantıyı dene' ile sınayın.", "asistan"); yzCiz(); }
    else { so.textContent = c.hata || "Eklenemedi."; kay.disabled = false; }
  };
  kap.appendChild(kay); kap.appendChild(so);
}

const BEYIN_AD = { llamacpp: "Yerel (llama.cpp)", ollama: "Yerel (Ollama)", gemini: "Gemini (bulut)", nvidia: "NVIDIA (bulut)",
  groq: "Groq (bulut)", mistral: "Mistral (bulut)", openrouter: "OpenRouter (bulut)" };
// Her beyin ayrı ayrı açılıp kapatılabilir; kapalı beyin hiç denenmez.
async function beyinAcKapat(k) {
  baslik(k, "Beyinleri aç / kapat");
  let d = {};
  try { d = await istek("/yz/saglayicilar"); } catch (e) { ekle(k, "Beyin listesi okunamadı."); return; }
  Object.keys(BEYIN_AD).forEach(ad => {
    const acik = !(d[ad] && d[ad].acik === false);
    const satir = ekle(k, BEYIN_AD[ad], acik ? "Açık: sırası gelince denenir." : "Kapalı: hiç kullanılmaz.");
    satir.style.borderLeft = "3px solid " + (acik ? "var(--ulgen-success)" : "var(--ulgen-offline)");
    const b = document.createElement("button"); b.className = "dugme" + (acik ? " aktif" : ""); b.textContent = acik ? "Kapat" : "Aç";
    b.style.marginTop = "6px";
    b.onclick = async () => {
      b.disabled = true;
      const c = await istek("/yz/saglayici", { saglayici: ad, acik: !acik });
      if (c.hata) balonEkle(c.hata, "asistan");
      yzCiz();
    };
    satir.appendChild(b);
  });
}

const SAGLAYICI_AD = { gemini: "Gemini", nvidia: "NVIDIA", groq: "Groq", mistral: "Mistral", openrouter: "OpenRouter", elevenlabs: "ElevenLabs (ses)", github: "GitHub (İSTEĞE BAĞLI: yalnız depo özel olursa gerekir; şimdilik boş bırakın)" };

// Hangi sağlayıcıya anahtar girilmiş: görünür, eklenir, değiştirilir, silinir.
async function anahtarlarim(k) {
  baslik(k, "API anahtarlarım (Mac'in Anahtar Zinciri'nde saklanır)");
  let durum = {};
  try { durum = await istek("/yz/anahtarlar"); } catch (e) { ekle(k, "Anahtar durumu okunamadı."); return; }
  Object.keys(SAGLAYICI_AD).forEach(ad => {
    const d = durum[ad] || { var: false };
    const satir = ekle(k, SAGLAYICI_AD[ad] + " — " + (d.var ? "✔ anahtar VAR" : "✘ anahtar YOK"),
      d.var ? "Saklandığı yer: " + d.yer + "  ·  son 4 hane: …" + d.son4 : "Eklemek için «Ekle»ye basın.");
    satir.style.borderLeft = "3px solid " + (d.var ? "var(--ulgen-success)" : "var(--ulgen-offline)");
    const dugme = (yazi, tehlike) => { const b = document.createElement("button"); b.className = "dugme"; b.textContent = yazi;
      b.style.cssText = "margin:6px 6px 0 0" + (tehlike ? ";border-color:var(--ulgen-danger);color:var(--ulgen-danger)" : ""); satir.appendChild(b); return b; };
    const ek = dugme(d.var ? "Değiştir" : "Ekle");
    ek.onclick = () => {
      if (satir.querySelector(".duzeltForm")) return;
      const f = document.createElement("div"); f.className = "duzeltForm"; f.style.marginTop = "8px";
      const st = "width:100%;margin:4px 0;padding:9px;border-radius:10px;border:1px solid var(--kenar);background:var(--ulgen-navy);color:var(--yazi)";
      const gir = document.createElement("input"); gir.type = "password"; gir.autocomplete = "off"; gir.placeholder = "API anahtarı"; gir.style.cssText = st;
      let kim = null;
      if (ad === "elevenlabs") { kim = document.createElement("input"); kim.placeholder = "Ses kimliği (isteğe bağlı)"; kim.autocomplete = "off"; kim.style.cssText = st; }
      const so = document.createElement("div"); so.style.cssText = "font-size:12px;color:var(--soluk)";
      const kay = document.createElement("button"); kay.className = "dugme aktif"; kay.textContent = "Kaydet";
      const va = document.createElement("button"); va.className = "dugme"; va.textContent = "Vazgeç"; va.style.marginLeft = "8px"; va.onclick = () => f.remove();
      kay.onclick = async () => {
        kay.disabled = true;
        const c = await istek("/yz/anahtar", { saglayici: ad, anahtar: gir.value, ses_kimligi: kim ? kim.value : "" });
        gir.value = "";
        if (c.tamam) { balonEkle(SAGLAYICI_AD[ad] + " anahtarı kaydedildi (" + c.yer + ").", "asistan"); yzCiz(); }
        else { so.textContent = c.hata || "Kaydedilemedi."; kay.disabled = false; }
      };
      f.appendChild(gir); if (kim) f.appendChild(kim); f.appendChild(kay); f.appendChild(va); f.appendChild(so); satir.appendChild(f);
    };
    if (d.var) {
      const de = dugme("Bağlantıyı dene");
      de.onclick = async () => { de.disabled = true; balonEkle("Deneniyor: " + SAGLAYICI_AD[ad] + "…", "asistan");
        try { const c = await istek("/yz/dene", { saglayici: ad }); balonEkle((c.calisti ? "✔ " : "✘ ") + (c.cikti || c.hata || "Yanıt yok."), "asistan"); }
        finally { de.disabled = false; } };
      const si = dugme("Sil", true);
      si.onclick = async () => {
        if (!confirm(SAGLAYICI_AD[ad] + " anahtarı bu Mac'ten silinecek. Emin misiniz?")) return;
        si.disabled = true;
        const c = await istek("/yz/anahtar-sil", { saglayici: ad, onay: true });
        balonEkle(c.hata ? c.hata : SAGLAYICI_AD[ad] + " anahtarı silindi.", "asistan"); yzCiz();
      };
    }
  });
}

async function beyinKipi(k) {
  baslik(k, "Yapay zekâ kipi");
  const a = await istek("/ayar/ozet");
  const kap = ekle(k, "Şu an: " + ({ yerel: "yalnız yerel (sabit)", otomatik: "önce yerel, olmazsa bulut", hizli: "hızlı: önce bulut; özel sorular yalnız yerelde", bulut: "yalnız bulut" }[a.beyin] || a.beyin),
    "Yerel kipte hiçbir soru Mac'ten dışarı çıkmaz. Bulut kipleri sorularınızı ücretsiz bulut sağlayıcılarına gönderir.");
  [["yerel", "Yalnız yerel"], ["hizli", "Hızlı (özel sorular yerelde)"], ["otomatik", "Önce yerel, sonra bulut"], ["bulut", "Yalnız bulut"]].forEach(([m, ad]) => {
    const b = document.createElement("button"); b.className = "dugme" + (a.beyin === m ? " aktif" : ""); b.textContent = ad; b.style.cssText = "margin:6px 6px 0 0";
    b.onclick = async () => {
      if (m !== "yerel" && !confirm("Bu kipte sorularınız bulut sağlayıcılarına gidebilir. Onaylıyor musunuz?")) return;
      const c = await istek("/yz/mod", { mod: m, onay: m !== "yerel" }); balonEkle(c.mod ? "Yapay zekâ kipi: " + ad : (c.hata || "Değişmedi."), "asistan"); ayarCiz();
    };
    kap.appendChild(b);
  });
}

function anahtarKutusu(k) {
  baslik(k, "Bulut anahtarı ekle (Mac'in Anahtar Zinciri'ne yazılır)");
  const kap = document.createElement("div"); kap.className = "satir2";
  const sec = document.createElement("select"); sec.className = "dugme";
  ["gemini", "nvidia", "groq", "mistral", "openrouter", "elevenlabs"].forEach(a => { const o = document.createElement("option"); o.value = a; o.textContent = a; sec.appendChild(o); });
  const gir = document.createElement("input"); gir.type = "password"; gir.autocomplete = "off"; gir.placeholder = "API anahtarı";
  gir.style.cssText = "width:100%;margin:8px 0;padding:10px;border-radius:10px;border:1px solid var(--kenar);background:var(--ulgen-navy);color:var(--yazi)";
  const kim = document.createElement("input"); kim.type = "text"; kim.autocomplete = "off"; kim.placeholder = "ElevenLabs ses kimliği (yalnız elevenlabs için)";
  kim.style.cssText = gir.style.cssText;
  const sonuc = document.createElement("pre"); sonuc.style.cssText = "white-space:pre-wrap;font-size:12px;color:var(--soluk)";
  const kaydet = document.createElement("button"); kaydet.className = "dugme aktif"; kaydet.textContent = "Kaydet";
  const dene = document.createElement("button"); dene.className = "dugme"; dene.textContent = "Bağlantıyı dene"; dene.style.marginLeft = "8px";
  kaydet.onclick = async () => {
    const c = await istek("/yz/anahtar", { saglayici: sec.value, anahtar: gir.value, ses_kimligi: kim.value });
    gir.value = ""; sonuc.textContent = c.tamam ? "Kaydedildi (" + c.yer + "). Şimdi 'Bağlantıyı dene'yi kullanın." : (c.hata || "Kaydedilemedi.");
  };
  dene.onclick = async () => {
    dene.disabled = true; sonuc.textContent = "Deneniyor...";
    try { const c = await istek("/yz/dene", { saglayici: sec.value }); sonuc.textContent = c.cikti || c.hata || "Yanıt yok."; }
    finally { dene.disabled = false; }
  };
  kap.appendChild(sec); kap.appendChild(gir); kap.appendChild(kim); kap.appendChild(kaydet); kap.appendChild(dene); kap.appendChild(sonuc);
  k.appendChild(kap);
}

async function sesPaneli(k) {
  baslik(k, "Ses seçimi");
  // 1) Yerel ses (bu cihazın sesi): ad, hız, perde
  const kap = ekle(k, "Okuma sesi (bu cihazda)", "Sabit cümleler dışındaki yanıtlar bu sesle okunur.");
  const t = sesTercihi();
  const sec = document.createElement("select"); sec.className = "dugme"; sec.style.cssText = "max-width:100%;margin-top:6px";
  const doldur = () => {
    sec.innerHTML = "";
    const oto = document.createElement("option"); oto.value = ""; oto.textContent = "Otomatik"; sec.appendChild(oto);
    speechSynthesis.getVoices().filter(v => /tr/i.test(v.lang)).concat(speechSynthesis.getVoices().filter(v => !/tr/i.test(v.lang)))
      .forEach(v => { const o = document.createElement("option"); o.value = v.name; o.textContent = v.name + " (" + v.lang + ")"; sec.appendChild(o); });
    sec.value = t.ad || "";
  };
  if ("speechSynthesis" in window) { doldur(); speechSynthesis.onvoiceschanged = doldur; }
  const kaydetTercih = () => { t.ad = sec.value; t.hiz = parseFloat(hiz.value); t.perde = parseFloat(perde.value);
    try { localStorage.setItem("ulgen_ses", JSON.stringify(t)); } catch (e) { /* özel gezinti */ } };
  const kaydirak = (ad, min, max, adim, deger) => { const e = document.createElement("input"); e.type = "range"; e.min = min; e.max = max; e.step = adim; e.value = deger; e.style.cssText = "width:100%"; e.title = ad; return e; };
  const hiz = kaydirak("Hız", 0.6, 1.4, 0.05, t.hiz || 0.95), perde = kaydirak("Perde", 0.5, 1.5, 0.05, t.perde || 0.8);
  const dene = document.createElement("button"); dene.className = "dugme aktif"; dene.textContent = "Dene"; dene.style.marginTop = "6px";
  dene.onclick = () => { kaydetTercih(); yerelKonus("Merhaba, ben Ülgen. Sesim böyle."); };
  sec.onchange = kaydetTercih; hiz.onchange = kaydetTercih; perde.onchange = kaydetTercih;
  kap.appendChild(sec); kap.appendChild(document.createTextNode("Hız")); kap.appendChild(hiz);
  kap.appendChild(document.createTextNode("Perde")); kap.appendChild(perde); kap.appendChild(dene);
  // 1b) Bulut sesi (ElevenLabs): yalnız Mac'in kendi tarayıcısından açılıp kapatılır
  if (yerel) {
    const durum = await istek("/ses/durum");
    const b = ekle(k, "Bulut sesi (ElevenLabs, kendi sesiniz)",
      "Açıkken okunacak YANIT METNİ ElevenLabs'e gönderilir. İlaç, sağlık, kasa, parola içeren yanıtlar hiç gönderilmez. Bu ay " + durum.bulut_kullanilan + " / " + durum.bulut_sinir + " karakter; sınır dolunca yerel ses okur.");
    const t = document.createElement("button"); t.className = "dugme" + (durum.bulut ? " aktif" : ""); t.style.marginTop = "6px";
    t.textContent = "Bulut sesi: " + (durum.bulut ? "açık" : "kapalı");
    t.onclick = async () => { await istek("/ses/bulut-ayar", { acik: !durum.bulut }); bulutSes = !durum.bulut; ayarCiz(); };
    b.appendChild(t);
    const dene2 = document.createElement("button"); dene2.className = "dugme"; dene2.textContent = "Kendi sesimi dene"; dene2.style.cssText = "margin:6px 0 0 8px";
    dene2.onclick = async () => {
      sesKilidiniAc(); dene2.disabled = true;
      const tamam = await bulutOku("Merhaba, ben Ülgen. Bu benim sesim.", true);
      balonEkle(tamam ? "Kendi sesiniz çalındı." : "Kendi sesiniz çalınamadı: " + (sonBulutNeden || "bilinmeyen neden"), "asistan");
      dene2.disabled = false;
    };
    b.appendChild(dene2);
    const y = ekle(k, "Yalnız benim sesim",
      "Açıkken kendi sesiniz okuyamadığında (ilaç/sağlık gibi hassas yanıtlar, aylık sınır, ağ hatası) kadın sistem sesine geçilmez; yanıt yalnız yazı olarak kalır. Kapalıyken o yanıtları sistem sesi okur (ilaç hatırlatmalarını duymak için kapalı tutabilirsiniz).");
    const yb = document.createElement("button"); yb.style.marginTop = "6px";
    const boya = () => { yb.className = "dugme" + (yalnizBenimSes() ? " aktif" : ""); yb.textContent = "Yalnız benim sesim: " + (yalnizBenimSes() ? "açık" : "kapalı"); };
    boya();
    yb.onclick = () => { try { localStorage.setItem("ulgen_yalniz_ben", yalnizBenimSes() ? "0" : "1"); } catch (e) {} boya(); };
    y.appendChild(yb);
  }
  // 2) Sabit cümleler için kendi mp3 dosyalarınız
  baslik(k, "Kendi ses dosyalarınız (her biri tek cümle, mp3, en çok 4 MB)");
  const cumleler = await istek("/ses/cumleler");
  cumleler.forEach(c => {
    const d = ekle(k, c.metin, c.var ? "Kendi dosyanız yüklü" : "Dosya yok (yerel ses okur)");
    const f = document.createElement("input"); f.type = "file"; f.accept = "audio/mpeg,.mp3,audio/*"; f.style.display = "none";
    const sec = document.createElement("button"); sec.className = "dugme aktif"; sec.textContent = c.var ? "Dosyayı değiştir (mp3)" : "Dosya seç (mp3)";
    sec.style.marginTop = "6px"; sec.onclick = () => f.click();
    const durum = document.createElement("small"); durum.style.marginTop = "4px";
    f.onchange = async () => {
      const dosya = f.files[0];
      if (!dosya) return;
      if (dosya.size > 4 * 1024 * 1024) {
        durum.style.color = "var(--ulgen-danger)";
        durum.textContent = "Dosya çok büyük: " + (dosya.size / 1048576).toFixed(1) + " MB (en çok 4 MB). Tek cümlelik kısa bir kayıt seçin.";
        f.value = ""; return;
      }
      durum.style.color = ""; durum.textContent = "Yükleniyor: " + dosya.name + "…";
      try {
        const h = { "Content-Type": "audio/mpeg" }; if (anahtar) h["Authorization"] = "Bearer " + anahtar;
        const r = await fetch("/ses/klip/" + c.ad, { method: "POST", headers: h, body: dosya });
        const v = await r.json().catch(() => ({}));
        if (!r.ok) { durum.style.color = "var(--ulgen-danger)"; durum.textContent = v.hata || ("Yüklenemedi (HTTP " + r.status + ")."); return; }
        balonEkle("Ses dosyası yüklendi.", "asistan");
        klipler = await istek("/ses/klipler"); ayarCiz();
      } catch (e) { durum.style.color = "var(--ulgen-danger)"; durum.textContent = "Yüklenemedi: " + (e && e.message ? e.message : e); }
    };
    d.appendChild(sec); d.appendChild(f); d.appendChild(durum);
    if (c.var) {
      const b = document.createElement("button"); b.className = "dugme"; b.textContent = "Dinle"; b.style.margin = "6px 6px 0 0"; b.onclick = () => klipCal(c.ad);
      const s = document.createElement("button"); s.className = "dugme"; s.textContent = "Kaldır"; s.style.marginTop = "6px";
      s.onclick = async () => { await istek("/ses/klip-sil", { ad: c.ad }); klipler = await istek("/ses/klipler"); ayarCiz(); };
      d.appendChild(b); d.appendChild(s);
    }
  });
}

// Kendini güncelleme: depodan yeni kodu çeker; ortam, veri ve anahtarlar korunur, eski kod yedeklenir.
async function guncellemePaneli(k) {
  baslik(k, "Güncelleme");
  let d;
  try { d = await istek("/guncelle/durum"); } catch (e) { ekle(k, "Güncelleme durumu okunamadı."); return; }
  const kap = ekle(k, "Kurulu sürüm: " + d.kurulu + (d.uzak ? "  ·  depodaki: " + d.uzak : ""),
    d.hata ? d.hata : (d.yeni_var ? "Yeni sürüm var." : "Güncelsiniz."));
  const st = "width:100%;margin:4px 0;padding:9px;border-radius:10px;border:1px solid var(--kenar);background:var(--ulgen-navy);color:var(--yazi)";
  const dug = (yazi, ac, tehlike) => { const b = document.createElement("button"); b.className = "dugme" + (ac ? " aktif" : ""); b.textContent = yazi;
    b.style.cssText = "margin:6px 6px 0 0" + (tehlike ? ";border-color:var(--ulgen-danger);color:var(--ulgen-danger)" : ""); kap.appendChild(b); return b; };
  if (!d.depo) {
    const gir = document.createElement("input"); gir.placeholder = "GitHub deposu (örn. hakanuste/Ulgen)"; gir.autocomplete = "off"; gir.style.cssText = st; kap.appendChild(gir);
    const kay = dug("Depoyu kaydet", true);
    kay.onclick = async () => { const c = await istek("/guncelle/depo", { depo: gir.value.trim() }); balonEkle(c.depo ? "Güncelleme deposu: " + c.depo : (c.hata || "Kaydedilemedi."), "asistan"); ayarCiz(); };
    return;
  }
  const den = dug("Denetle"); den.onclick = () => ayarCiz();
  if (d.yeni_var) {
    const gu = dug("Güncelle", true);
    gu.onclick = async () => {
      if (!confirm("Ülgen " + d.kurulu + " → " + d.uzak + " güncellenecek; eski kod yedeklenir ve sunucu yeniden başlar. Devam edilsin mi?")) return;
      gu.disabled = true; balonEkle("Güncelleniyor…", "asistan");
      const c = await istek("/guncelle/uygula", { onay: true });
      if (!c.tamam) { balonEkle("Güncelleme yapılmadı: " + (c.hata || "bilinmeyen hata"), "asistan"); gu.disabled = false; return; }
      balonEkle("Güncellendi: " + c.eski + " → " + c.yeni + ". Sunucu yeniden başlıyor; sayfa birazdan yenilenecek.", "asistan");
      setTimeout(function bekle() { fetch("/saglik", { cache: "no-store" }).then(r => r.json()).then(j => { if (j.surum === c.yeni) location.reload(); else setTimeout(bekle, 1500); }).catch(() => setTimeout(bekle, 1500)); }, 4000);
    };
  }
  if (d.geri_alinabilir) {
    const ge = dug("Önceki sürüme dön", false, true);
    ge.onclick = async () => {
      if (!confirm("Son güncellemeden önceki kod geri konulacak. Emin misiniz?")) return;
      const c = await istek("/guncelle/geri-al", { onay: true });
      balonEkle(c.tamam ? "Geri alındı (" + c.geri + "). Sunucu yeniden başlıyor." : "Geri alınamadı: " + (c.hata || ""), "asistan");
    };
  }
}

// Kılavuz klasöründeki PDF/metin dosyalarını Obsidian kasasına not olarak aktarır (yeni dosyalar kendiliğinden).
async function kilavuzPaneli(k) {
  baslik(k, "Kılavuzlar → Obsidian");
  let d;
  try { d = await istek("/kilavuz/durum"); } catch (e) { ekle(k, "Kılavuz durumu okunamadı."); return; }
  const kap = ekle(k, "Klasör: " + d.kaynak + (d.klasor_var ? "" : "  (BULUNAMADI)"),
    "Kasa: " + d.kasa + "  ·  aktarılmayı bekleyen: " + d.bekleyen +
    (d.calisiyor ? "  ·  ŞİMDİ AKTARILIYOR: " + d.dosya + " (" + d.bitti + "/" + d.toplam + ")" : "") +
    (d.hata && d.hata.length ? "  ·  Hata: " + d.hata.join("; ") : ""));
  const dug = (yazi, ac) => { const b = document.createElement("button"); b.className = "dugme" + (ac ? " aktif" : ""); b.textContent = yazi; b.style.cssText = "margin:6px 6px 0 0"; kap.appendChild(b); return b; };
  const sim = dug("Şimdi aktar", true);
  sim.onclick = async () => {
    sim.disabled = true; await istek("/kilavuz/aktar", {});
    balonEkle("Kılavuzlar Obsidian'a aktarılıyor; büyük PDF'ler birkaç dakika sürebilir. Ayarlar sayfasını yenileyerek ilerlemeyi görebilirsiniz.", "asistan");
    const bekle = async () => { const g = await istek("/kilavuz/durum"); if (g.calisiyor) setTimeout(bekle, 3000); else ayarCiz(); };
    setTimeout(bekle, 2000);
  };
  const oto = dug("Kendiliğinden aktar: " + (d.otomatik ? "açık" : "kapalı"), d.otomatik);
  oto.onclick = async () => { await istek("/kilavuz/ayar", { otomatik: !d.otomatik }); ayarCiz(); };
  const gir = document.createElement("input"); gir.placeholder = "Klasörü değiştir (örn. ~/Documents/Klavuzlar)"; gir.autocomplete = "off";
  gir.style.cssText = "width:100%;margin:6px 0;padding:9px;border-radius:10px;border:1px solid var(--kenar);background:var(--ulgen-navy);color:var(--yazi)"; kap.appendChild(gir);
  const kay = dug("Klasörü kaydet");
  kay.onclick = async () => { const c = await istek("/kilavuz/ayar", { klasor: gir.value }); balonEkle(c.hata ? c.hata : "Kılavuz klasörü: " + c.kaynak, "asistan"); ayarCiz(); };
}

async function macPaneli(k) {
  baslik(k, "Mac Takvim ve Hatırlatıcılar ⇄ Ülgen");
  let d;
  try { d = await istek("/mac/durum"); } catch (e) { ekle(k, "Mac eşitleme durumu okunamadı."); return; }
  const son = d.son ? new Date(d.son * 1000).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }) : "henüz yok";
  const sy = d.sayilar || {};
  const kap = ekle(k, "Mac'teki randevular ve hatırlatıcılar Ülgen'e kendiliğinden gelir (yalnız okunur; Mac'ten dışarı çıkmaz).",
    "Son eşitleme: " + son + (d.calisiyor ? "  ·  ŞİMDİ EŞİTLENİYOR" : "") +
    (sy.yeni !== undefined ? "  ·  yeni: " + sy.yeni + ", güncellenen: " + sy.guncel + ", kapanan: " + sy.kapandi : "") +
    (d.hata && d.hata.length ? "  ·  Sorun: " + d.hata.join("; ") : "") +
    (d.mac ? "" : "  ·  (bu bilgisayar macOS değil; eşitleme çalışmaz)"));
  const dug = (yazi, ac) => { const b = document.createElement("button"); b.className = "dugme" + (ac ? " aktif" : ""); b.textContent = yazi; b.style.cssText = "margin:6px 6px 0 0"; kap.appendChild(b); return b; };
  const sim = dug("Şimdi eşitle", true);
  sim.onclick = async () => {
    sim.disabled = true; await istek("/mac/esitle", {});
    balonEkle("Mac Takvim ve Hatırlatıcılar eşitleniyor. İlk seferde macOS izin sorabilir; 'Tamam' deyin.", "asistan");
    setTimeout(ayarCiz, 8000);
  };
  const oto = dug("Kendiliğinden eşitle: " + (d.senk ? "açık" : "kapalı"), d.senk);
  oto.onclick = async () => { await istek("/mac/ayar", { senk: !d.senk }); ayarCiz(); };
  const bil = dug("Mac bildirimi: " + (d.bildirim ? "açık" : "kapalı"), d.bildirim);
  bil.onclick = async () => { await istek("/mac/ayar", { bildirim: !d.bildirim }); ayarCiz(); };
}

async function takvimPaneli(k) {
  baslik(k, "iPhone alarmı: tekrar");
  let d;
  try { d = await istek("/takvim/ayar"); } catch (e) { return; }
  const kap = ekle(k, "iPhone takvimi 'aldım' yanıtını bilemez; ilaç alarmı tekrar sayısı kadar çalar. Kaç kez, kaç dakikada bir çalsın? (Değişince İlaçlar sayfasında 'iPhone takvimine aktar'ı yeniden yapın.)",
    "Şu an: " + d.tekrar + " kez, " + d.aralik + " dakikada bir.");
  const sat = (yazi, degerler, anahtar, simdiki, birim) => {
    const s = document.createElement("div"); s.style.marginTop = "8px"; s.append(yazi + " ");
    degerler.forEach(v => { const b = document.createElement("button"); b.className = "dugme" + (v === simdiki ? " aktif" : ""); b.textContent = v + birim; b.style.cssText = "margin:4px 6px 0 0";
      b.onclick = async () => { const o = {}; o[anahtar] = v; const c = await istek("/takvim/ayar", o); if (c.hata) balonEkle(c.hata, "asistan"); ayarCiz(); }; s.appendChild(b); });
    kap.appendChild(s); };
  sat("Tekrar sayısı:", [1, 2, 3, 6], "tekrar", d.tekrar, "");
  sat("Aralık:", d.araliklar, "aralik", d.aralik, " dk");
}

async function ayarCiz() {
  const a = await istek("/ayar/ozet"); const k = document.getElementById("pAyarlar"); k.innerHTML = "";
  if (yerel) await takvimPaneli(k);
  if (yerel) await macPaneli(k);
  if (yerel) await kilavuzPaneli(k);
  if (yerel) await guncellemePaneli(k);
  await sesPaneli(k);
  baslik(k, "Ayarlar (salt okunur; API anahtarları gösterilmez)");
  Object.keys(a).sort().forEach(n => ekle(k, n, typeof a[n] === "object" ? JSON.stringify(a[n]) : String(a[n])));
  ekle(k, "Değiştirmek için Mac'te ~/ÜlgenVeri/ayar.json dosyasını düzenleyin.", "Güvenlik ayarları (yerel_yetki, sifresiz_veritabani_izni) arayüzden değiştirilemez; bilerek böyle.");
}

const gunAdlari = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];

function gorevDuzeltFormu(kap, x, ekleme) {
  if (kap.querySelector(".duzeltForm")) return;
  const f = document.createElement("div"); f.className = "duzeltForm"; f.style.marginTop = "8px";
  const alan = (tur, yer, deger) => { const e = document.createElement("input"); e.type = tur; e.value = deger; e.placeholder = yer; e.autocomplete = "off";
    e.style.cssText = "width:100%;margin:4px 0;padding:9px;border-radius:10px;border:1px solid var(--kenar);background:var(--ulgen-navy);color:var(--yazi)"; f.appendChild(e); return e; };
  const ad = alan("text", "Ad", x.baslik);
  let zaman = null, gunler = [];
  if (x.tur === "rutin") {
    zaman = alan("time", "Saat", x.zaman || "");
    const sar = document.createElement("div"); sar.style.margin = "6px 0";
    const secili = new Set((x.tekrar || "").split(",").filter(Boolean));
    gunAdlari.forEach((g, n) => {
      const b = document.createElement("button"); b.type = "button"; b.textContent = g; b.style.cssText = "margin:0 4px 4px 0";
      const boya = () => { b.className = "dugme" + (secili.has(String(n)) ? " aktif" : ""); };
      boya(); b.onclick = () => { const a = String(n); if (secili.has(a)) secili.delete(a); else secili.add(a); boya(); };
      sar.appendChild(b);
    });
    f.appendChild(sar); gunler = secili;
  } else {
    zaman = alan("datetime-local", "Zaman", (x.zaman || "").replace(" ", "T"));
  }
  const k = document.createElement("button"); k.className = "dugme aktif"; k.textContent = "Kaydet";
  const v = document.createElement("button"); v.className = "dugme"; v.textContent = "Vazgeç"; v.style.marginLeft = "8px";
  v.onclick = () => f.remove();
  k.onclick = async () => {
    k.disabled = true;
    const tekrar = x.tur === "rutin" ? Array.from(gunler).sort().join(",") : "";
    const c = ekleme ? await istek("/gorev/ekle", { tur: x.tur, baslik: ad.value, zaman: zaman.value, tekrar: tekrar })
                     : await istek("/gorev/duzenle", { id: x.id, baslik: ad.value, zaman: zaman.value, tekrar: tekrar });
    balonEkle(c.yanit || c.hata, "asistan");
    if (/^(Düzelttim|Ekledim)/.test(c.yanit || "")) gorevlerCiz(); else k.disabled = false;
  };
  f.appendChild(k); f.appendChild(v); kap.appendChild(f);
}

function gorevDugmeleri(d, x, tamamla) {
  if (tamamla) {
    const b = document.createElement("button");
    b.className = "dugme"; b.style.cssText = "margin:6px 6px 0 0"; b.textContent = "Tamamlandı";
    b.onclick = async () => { b.disabled = true; await istek("/gorev/bitir", { id: x.id }); gorevlerCiz(); };
    d.appendChild(b);
  }
  const du = document.createElement("button");
  du.className = "dugme"; du.style.cssText = "margin:6px 6px 0 0"; du.textContent = "Düzelt";
  du.onclick = () => gorevDuzeltFormu(d, x);
  d.appendChild(du);
  const si = document.createElement("button");
  si.className = "dugme"; si.style.cssText = "margin-top:6px;border-color:var(--ulgen-danger);color:var(--ulgen-danger)"; si.textContent = "Sil";
  si.onclick = async () => {
    if (!confirm("#" + x.id + " " + x.baslik + " kalıcı silinecek. Emin misiniz?")) return;
    si.disabled = true;
    const c = await istek("/gorev/sil", { id: x.id, onay: true });
    balonEkle(c.yanit || c.hata, "asistan"); gorevlerCiz();
  };
  d.appendChild(si);
}

async function gorevlerCiz() {
  const g = await istek("/gorevler");
  const k = document.getElementById("pGorevler");
  k.innerHTML = "";
  const yeni = ekle(k, "Yeni kayıt ekle", "Görev, randevu ya da rutin; sohbetten de yazabilirsiniz.");
  [["gorev", "+ Görev"], ["randevu", "+ Randevu"], ["rutin", "+ Rutin"]].forEach(([tur, ad]) => {
    const b = document.createElement("button"); b.className = "dugme aktif"; b.textContent = ad; b.style.cssText = "margin:6px 6px 0 0";
    b.onclick = () => { const eski = yeni.querySelector(".duzeltForm"); if (eski) eski.remove();
      gorevDuzeltFormu(yeni, { tur: tur, baslik: "", zaman: "", tekrar: tur === "rutin" ? "0,1,2,3,4,5,6" : "" }, true); };
    yeni.appendChild(b);
  });
  baslik(k, "Görevler");
  if (!g.gorev.length) ekle(k, "Açık görev yok.");
  g.gorev.forEach(x => gorevDugmeleri(ekle(k, "#" + x.id + " " + x.baslik, x.zaman || "zamansız"), x, true));
  baslik(k, "Randevular");
  if (!g.randevu.length) ekle(k, "Randevu yok.");
  g.randevu.forEach(x => gorevDugmeleri(ekle(k, "#" + x.id + " " + x.baslik, x.zaman), x, false));
  baslik(k, "Rutinler");
  if (!g.rutin.length) ekle(k, "Rutin yok.");
  g.rutin.forEach(x => gorevDugmeleri(ekle(k, "#" + x.id + " " + x.baslik,
    x.zaman + "  (" + (x.tekrar || "").split(",").filter(Boolean).map(n => gunAdlari[+n]).join(" ") + ")"), x, false));
  const o = await istek("/ozet");
  baslik(k, "Hatırlatıcılar");
  if (!o.hatirlaticilar.length) ekle(k, "Bekleyen hatırlatıcı yok.");
  o.hatirlaticilar.forEach(h => {
    const d = ekle(k, h.mesaj, h.zaman);
    const du = document.createElement("button");
    du.className = "dugme"; du.style.cssText = "margin:6px 6px 0 0"; du.textContent = "Düzelt";
    du.onclick = () => {
      if (d.querySelector(".duzeltForm")) return;
      const f = document.createElement("div"); f.className = "duzeltForm"; f.style.marginTop = "8px";
      const st = "width:100%;margin:4px 0;padding:9px;border-radius:10px;border:1px solid var(--kenar);background:var(--ulgen-navy);color:var(--yazi)";
      const m = document.createElement("input"); m.value = h.mesaj; m.style.cssText = st;
      const z = document.createElement("input"); z.type = "datetime-local"; z.value = h.zaman.replace(" ", "T"); z.style.cssText = st;
      const kay = document.createElement("button"); kay.className = "dugme aktif"; kay.textContent = "Kaydet";
      const va = document.createElement("button"); va.className = "dugme"; va.textContent = "Vazgeç"; va.style.marginLeft = "8px";
      va.onclick = () => f.remove();
      kay.onclick = async () => {
        kay.disabled = true;
        const c = await istek("/hatirlatici/duzenle", { id: h.id, mesaj: m.value, zaman: z.value });
        balonEkle(c.yanit || c.hata, "asistan");
        if (/^Düzelttim/.test(c.yanit || "")) gorevlerCiz(); else kay.disabled = false;
      };
      f.appendChild(m); f.appendChild(z); f.appendChild(kay); f.appendChild(va); d.appendChild(f);
    };
    d.appendChild(du);
    const si = document.createElement("button");
    si.className = "dugme"; si.style.cssText = "margin-top:6px;border-color:var(--ulgen-danger);color:var(--ulgen-danger)"; si.textContent = "Sil";
    si.onclick = async () => {
      if (!confirm("«" + h.mesaj + "» kalıcı silinecek. Emin misiniz?")) return;
      si.disabled = true;
      const c = await istek("/hatirlatici/sil", { id: h.id, onay: true });
      balonEkle(c.yanit || c.hata, "asistan"); gorevlerCiz();
    };
    d.appendChild(si);
  });
}

const durumYazi = { alindi: "alındı", almadi: "almadı", atlandi: "atlandı", tamamlandi: "tamamlandı",
                    bekliyor: "bekliyor", ertelendi: "ertelendi", yanitsiz: "YANITSIZ (bilinmiyor)" };

function ilacDuzeltFormu(kap, i) {
  if (kap.querySelector(".duzeltForm")) return;
  const f = document.createElement("div"); f.className = "duzeltForm"; f.style.marginTop = "8px";
  const alan = (yer, deger) => { const e = document.createElement("input"); e.value = deger; e.placeholder = yer; e.autocomplete = "off";
    e.style.cssText = "width:100%;margin:4px 0;padding:9px;border-radius:10px;border:1px solid var(--kenar);background:var(--ulgen-navy);color:var(--yazi)"; f.appendChild(e); return e; };
  const ad = alan("İlaç adı", i.ad), not = alan("Not (örn. yemekten sonra)", i.doz_notu || ""), saat = alan("Saatler (örn. 08:00 20:00)", i.saatler || "");
  const k = document.createElement("button"); k.className = "dugme aktif"; k.textContent = "Kaydet";
  const v = document.createElement("button"); v.className = "dugme"; v.textContent = "Vazgeç"; v.style.marginLeft = "8px";
  v.onclick = () => f.remove();
  k.onclick = async () => {
    k.disabled = true;
    const c = await istek("/ilac/duzenle", { id: i.id, ad: ad.value, doz_notu: not.value, saatler: saat.value });
    balonEkle(c.yanit, "asistan");
    if (/^Düzelttim/.test(c.yanit)) ilacCiz(); else k.disabled = false;
  };
  f.appendChild(k); f.appendChild(v); kap.appendChild(f);
}

async function kayitliIlaclar(k) {
  const liste = await istek("/ilac/liste");
  baslik(k, "Kayıtlı ilaçlar");
  if (!liste.length) { ekle(k, "Kayıtlı ilaç yok."); return; }
  liste.forEach(i => {
    const d = ekle(k, i.ad + (i.doz_notu ? " (" + i.doz_notu + ")" : "") + (i.aktif ? "" : "  — durduruldu"), i.saatler || "saat yok");
    const du = document.createElement("button");
    du.className = "dugme"; du.style.cssText = "margin:6px 6px 0 0"; du.textContent = "Düzelt";
    du.onclick = () => ilacDuzeltFormu(d, i);
    d.appendChild(du);
    const b = document.createElement("button");
    b.className = "dugme"; b.style.cssText = "margin-top:6px;border-color:var(--ulgen-danger);color:var(--ulgen-danger)"; b.textContent = "Sil (hatalı girdi)";
    b.onclick = async () => {
      if (!confirm(i.ad + " ve tüm doz kayıtları kalıcı silinecek. Emin misiniz?")) return;
      b.disabled = true;
      const c = await istek("/ilac/sil", { id: i.id, onay: true });
      balonEkle(c.yanit, "asistan"); ilacCiz();
    };
    d.appendChild(b);
  });
}

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
  await kayitliIlaclar(k);
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

let ajanListe = null;
async function ajanAc() {
  const sec = document.getElementById("ajanSec");
  if (!ajanListe) {
    try { ajanListe = await istek("/uzmanlar"); } catch (e) { ajanListe = { uzmanlar: [] }; }
    sec.replaceChildren();
    const a = document.createElement("option"); a.value = "arastirma"; a.textContent = "Araştırma ajanı (alanı olanı uzmana devreder)"; sec.appendChild(a);
    ajanListe.uzmanlar.forEach(u => { const o = document.createElement("option"); o.value = u.ad; o.textContent = u.ad + " – " + u.alan; sec.appendChild(o); });
  }
  document.getElementById("ajanDurum").textContent = "";
  document.getElementById("ajanPanel").classList.add("acik");
  document.getElementById("ajanGorev").focus();
}
function ajanKapat() { document.getElementById("ajanPanel").classList.remove("acik"); }
async function ajanGonder() {
  const ajan = document.getElementById("ajanSec").value;
  const gorev = document.getElementById("ajanGorev").value.trim();
  const d = document.getElementById("ajanDurum");
  if (!gorev) { d.textContent = "Görev boş."; return; }
  d.textContent = "Gönderiliyor…";
  try {
    const y = await istek("/ajanlar/gorev", { ajan: ajan, gorev: gorev });
    if (y && y.hata) { d.textContent = y.hata; return; }
    document.getElementById("ajanGorev").value = "";
    ajanKapat();
    balonEkle("Görev " + (y.ad || ajan) + " ajanına verildi. Bitince sonucu burada yayınlayacak.", "asistan");
  } catch (e) { d.textContent = "Gönderilemedi: " + (e.message || e); }
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
