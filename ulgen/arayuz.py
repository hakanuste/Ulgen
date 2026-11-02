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
         font-size: 16px; white-space: pre-wrap; word-wrap: break-word; }
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
#kodPanel { position: fixed; inset: 0; background: var(--bg); display: none; flex-direction: column;
            padding: calc(env(safe-area-inset-top) + 8px) 10px calc(env(safe-area-inset-bottom) + 8px); z-index: 5; }
#kodPanel.acik { display: flex; }
#kodPanel .satir { display: flex; gap: 6px; margin: 4px 0; flex-wrap: wrap; align-items: center; }
#kodPanel select, #kodPanel input { background: var(--kart); color: var(--yazi); border: 1px solid var(--ulgen-ocean);
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
body[data-s="bilgi"] #sohbetKolon, body[data-s="yz"] #sohbetKolon, body[data-s="ayarlar"] #sohbetKolon { display: none; }
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
  #afis { display: block; position: relative; height: 58px; flex: none; overflow: hidden; border-bottom: 1px solid var(--altin2); }
  body[data-s="ana"] #afis { height: 250px; }
  #afis .arka { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(3,9,20,.25), rgba(3,9,20,.1) 60%, var(--ulgen-bg) 100%), url(/varlik/afis.webp) center 35% / cover; }
  #mobilLogo { display: none; position: absolute; left: 50%; top: calc(env(safe-area-inset-top) + 8px); width: 170px; margin-left: -85px; filter: drop-shadow(0 0 14px rgba(120,223,255,.5)); }
  #mobilAlt { display: none; position: absolute; left: 0; right: 0; bottom: 12px; text-align: center; color: #fff; font-size: 15px; text-shadow: 0 1px 4px #000; }
  body[data-s="ana"] #mobilLogo, body[data-s="ana"] #mobilAlt { display: block; }
  #baslikOrta { top: calc(env(safe-area-inset-top) + 12px); } #baslikOrta small, #baslikOrta .yd { display: none; }
  #baslikOrta b { font-size: 22px !important; letter-spacing: 6px !important; }
  body[data-s="ana"] #baslikOrta { display: none; }
  #hamBtn, #sagUst .ik { width: 44px; height: 44px; border-radius: 50%; border: 1px solid var(--altin2); background: rgba(13,36,59,.7); color: var(--altin); display: grid; place-items: center; }
  #hamBtn { position: absolute; left: 14px; top: calc(env(safe-area-inset-top) + 8px); z-index: 3; cursor: pointer; }
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
<div id="pSaglik" class="panel"></div>
<div id="pProjeler" class="panel"></div>
<div id="pBilgi" class="panel"></div>
<div id="pYz" class="panel"></div>
<div id="pAyarlar" class="panel"></div>
<div id="pSistem" class="panel"></div>
<section id="mobilAna">
  <div id="kareler">
    <button class="kare" onclick="sekme('sohbet')"><svg class="i"><use href="#i-sohbet"/></svg>Sohbet</button>
    <button class="kare" onclick="sekme('gorevler')"><svg class="i"><use href="#i-gorev"/></svg>Görevler<em class="rz" id="kGorev"></em></button>
    <button class="kare" onclick="sekme('ilac')"><svg class="i"><use href="#i-hap"/></svg>İlaçlar</button>
    <button class="kare" onclick="sekme('saglik')"><svg class="i"><use href="#i-kalp"/></svg>Sağlık</button>
    <button class="kare" onclick="sekme('projeler')"><svg class="i"><use href="#i-katman"/></svg>Projeler</button>
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
</div>
<div id="alt">
  <div id="mikSatir">
    <button id="klavyeBtn" class="yuvarlak" onclick="giriseOdak()" title="Yaz"><svg class="i"><use href="#i-klavye"/></svg></button>
    <span class="dalga" id="dalgaS"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></span>
    <button id="mikBtn" class="yuvarlak" onclick="mikrofon()" title="Konuş"><svg class="i"><use href="#i-mik"/></svg></button>
    <span class="dalga" id="dalga"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></span>
  </div>
  <div id="yazSatir">
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

function menuAc() { document.body.classList.add("menuAcik"); }
function menuKapat() { document.body.classList.remove("menuAcik"); }
function giriseOdak() { sekme("sohbet"); document.getElementById("giris").focus(); }

async function gonderMetin(m) {
  if (window.innerWidth < 900 && aktifSekme === "ana") sekme("sohbet");
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
  document.body.classList.toggle("dinliyor", acik);
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

// Çevrimdışı ses: Mac'te faster-whisper kuruluysa kayıt yerel olarak metne çevrilir
// (ses internete çıkmaz). Kurulu değilse tarayıcının kendi tanıması kullanılır.
let cevrimdisiSes = false, kayitci = null;
async function sesDurumuYukle() {
  try { cevrimdisiSes = !!(await istek("/ses/durum")).cevrimdisi; } catch (e) { cevrimdisiSes = false; }
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
const paneller = { gorevler: "pGorevler", ilac: "pIlac", bildirim: "pBildirim", kasa: "pKasa", saglik: "pSaglik", projeler: "pProjeler", bilgi: "pBilgi", yz: "pYz", ayarlar: "pAyarlar", sistem: "pSistem" };
const gecmisBildirim = [];
let aktifSekme = "ana";

const sohbetli = ad => ad === "ana" || ad === "sohbet";
function sekme(ad) {
  menuKapat();
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
      const [g, il, sis] = await Promise.all([istek("/gorevler"), istek("/ilac/bugun"), istek("/sistem")]);
      rozetYaz(g, il);
      document.getElementById("surumRozet").textContent = "v" + sis.surum;
      const m = document.getElementById("mobilOzet"); m.replaceChildren();
      ozetKarti(m, g, il); ilacKarti(m, il);
      return;
    }
    const [g, il, sis] = await Promise.all([istek("/gorevler"), istek("/ilac/bugun"), istek("/sistem")]);
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
    const sg = await istek("/saglik/bugun");
    kartK(serit, "Sağlık", sg.veri_var ? ["Adım: " + (sg.adim === null ? "—" : sg.adim.toLocaleString("tr-TR")),
      "Nabız: " + (sg.nabiz === null ? "—" : sg.nabiz) + " • Uyku: " + uykuYazi(sg.uyku_dk)] :
      ["Veri yok", "iPhone Kestirmesi kurulunca dolar"], "kalp", "", "ilac");
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
    const h = document.createElement("div"); h.className = "halka"; h.style.setProperty("--p", Math.min(100, (sg.adim || 0) / 100) + "%");
    h.innerHTML = "<span><b></b>adım</span>"; h.querySelector("b").textContent = sg.adim === null ? "—" : sg.adim.toLocaleString("tr-TR");
    const uc = document.createElement("div"); uc.className = "sag3";
    const oge = (ikon, renk, deger, ad) => { const d = document.createElement("div"); d.className = "oge";
      d.innerHTML = '<svg class="i" style="color:' + renk + '"><use href="#i-' + ikon + '"/></svg><b></b>' + ad; d.querySelector("b").textContent = deger; return d; };
    uc.appendChild(h); uc.appendChild(oge("kalp", "var(--ulgen-danger)", sg.nabiz === null ? "—" : sg.nabiz, "nabız")); uc.appendChild(oge("ay", "var(--ulgen-ice)", uykuYazi(sg.uyku_dk), "uyku"));
    k5.appendChild(uc);
    if (!sg.veri_var) { const n = document.createElement("div"); n.style.cssText = "text-align:center;font-size:12px;color:var(--soluk);margin-top:6px"; n.textContent = "iPhone Kestirmesi kurulunca dolar (SAGLIK_KESTIRME.md)"; k5.appendChild(n); }
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
  const rb = document.getElementById("rzBildirim"); rb.textContent = gecmisBildirim.length; rb.classList.toggle("var", gecmisBildirim.length > 0);
}
async function havaYukle() {
  try {
    const h = await istek("/hava");
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
    else if (!g.value) ekle(sonuc, "Aramak için yazın. Kasa: " + r.dizin.kasa);
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
  anahtarKutusu(k);
}

function anahtarKutusu(k) {
  baslik(k, "Bulut anahtarı ekle (Mac'in Anahtar Zinciri'ne yazılır)");
  const kap = document.createElement("div"); kap.className = "satir2";
  const sec = document.createElement("select"); sec.className = "dugme";
  ["gemini", "nvidia", "groq", "mistral", "openrouter"].forEach(a => { const o = document.createElement("option"); o.value = a; o.textContent = a; sec.appendChild(o); });
  const gir = document.createElement("input"); gir.type = "password"; gir.autocomplete = "off"; gir.placeholder = "API anahtarı";
  gir.style.cssText = "width:100%;margin:8px 0;padding:10px;border-radius:10px;border:1px solid var(--kenar);background:var(--ulgen-navy);color:var(--yazi)";
  const sonuc = document.createElement("pre"); sonuc.style.cssText = "white-space:pre-wrap;font-size:12px;color:var(--soluk)";
  const kaydet = document.createElement("button"); kaydet.className = "dugme aktif"; kaydet.textContent = "Kaydet";
  const dene = document.createElement("button"); dene.className = "dugme"; dene.textContent = "Bağlantıyı dene"; dene.style.marginLeft = "8px";
  kaydet.onclick = async () => {
    const c = await istek("/yz/anahtar", { saglayici: sec.value, anahtar: gir.value });
    gir.value = ""; sonuc.textContent = c.tamam ? "Kaydedildi (" + c.yer + "). Şimdi 'Bağlantıyı dene'yi kullanın." : (c.hata || "Kaydedilemedi.");
  };
  dene.onclick = async () => {
    dene.disabled = true; sonuc.textContent = "Deneniyor...";
    try { const c = await istek("/yz/dene", { saglayici: sec.value }); sonuc.textContent = c.cikti || c.hata || "Yanıt yok."; }
    finally { dene.disabled = false; }
  };
  kap.appendChild(sec); kap.appendChild(gir); kap.appendChild(kaydet); kap.appendChild(dene); kap.appendChild(sonuc);
  k.appendChild(kap);
}

async function ayarCiz() {
  const a = await istek("/ayar/ozet"); const k = document.getElementById("pAyarlar"); k.innerHTML = "";
  baslik(k, "Ayarlar (salt okunur; API anahtarları gösterilmez)");
  Object.keys(a).sort().forEach(n => ekle(k, n, typeof a[n] === "object" ? JSON.stringify(a[n]) : String(a[n])));
  ekle(k, "Değiştirmek için Mac'te ~/ÜlgenVeri/ayar.json dosyasını düzenleyin.", "Güvenlik ayarları (yerel_yetki, sifresiz_veritabani_izni) arayüzden değiştirilemez; bilerek böyle.");
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
