"""Telefon uyumlu web arayüzü (tek sayfa, ek kütüphane gerektirmez).

Konuşma tanıma ve sesli okuma tarayıcının Web Speech API'si ile yapılır.
Not: Chrome ses tanımayı Google'a, Safari Apple'a gönderir.
"""

SAYFA = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Ülgen">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#0b0f14">
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

/* ---- ÜLGEN teması: koyu lacivert + altın ---- */
:root { --bg:#060b17; --kart:#0d1730; --kart2:#101d3b; --yazi:#e8eefc; --soluk:#8d9bb8; --vurgu:#37a8ff;
        --kullanici:#14437a; --kenar:#1a2a4d; --altin:#c9a24a; --altin2:#7d6428; --yesil:#3fd07a; --kirmizi:#ff6b5e; }
body { background: radial-gradient(1200px 600px at 70% -10%, #0e2150 0%, var(--bg) 60%); }
.dugme { border-color: var(--kenar); }
.dugme.aktif { background: linear-gradient(180deg,#4db6ff,#2a8fe0); }
.balon.asistan, .balon.kullanici { border: 1px solid var(--kenar); }
.balon.kullanici { background: linear-gradient(180deg,#17508f,#123e72); }
.satir2 { border: 1px solid var(--kenar); background: var(--kart); }
#kok { display: flex; flex-direction: column; flex: 1; min-height: 0; }
#ana { display: flex; flex-direction: column; flex: 1; min-height: 0; }
#yan { display: contents; }
#marka, #kullanici { display: none; }
#serit { display: none; }
#icerik { display: flex; flex: 1; min-height: 0; flex-direction: column; }
#sohbetKolon { display: flex; flex-direction: column; flex: 1; min-height: 0; }
#pano { display: none; }
body:not([data-s="sohbet"]) #sohbetKolon { display: none; }
#saat { font-variant-numeric: tabular-nums; color: var(--altin); font-size: 13px; }
@media (min-width: 900px) {
  #kok { flex-direction: row; }
  #yan { display: flex; flex-direction: column; width: 232px; flex-shrink: 0; padding: 18px 14px;
         border-right: 1px solid var(--altin2); background: linear-gradient(180deg,#081126,#060b17); }
  #marka { display: block; text-align: center; padding: 10px 0 22px; }
  #marka b { display: block; font-size: 26px; letter-spacing: 6px; color: var(--altin);
             text-shadow: 0 0 14px rgba(201,162,74,.35); }
  #marka small { color: var(--soluk); font-size: 11px; letter-spacing: 1px; }
  #marka i { display: block; width: 92px; height: 92px; margin: 0 auto 12px; border-radius: 50%;
             background: radial-gradient(circle at 50% 40%, #1b3d86 0%, #0a1634 62%, #060b17 100%);
             border: 2px solid var(--altin2); box-shadow: 0 0 24px rgba(55,168,255,.25) inset, 0 0 18px rgba(201,162,74,.2); }
  #sekmeler { flex-direction: column; border: 0; padding: 0; gap: 6px; overflow: visible; }
  #sekmeler button { flex: none; text-align: left; font-size: 15px; padding: 11px 14px; color: var(--yazi);
                     border: 1px solid transparent; border-radius: 12px; }
  #sekmeler button.aktif { background: linear-gradient(90deg,#0f2a5c,#0b1d42); color: var(--yazi);
                           border-color: var(--vurgu); box-shadow: 0 0 12px rgba(55,168,255,.25); }
  #kullanici { display: block; margin-top: auto; padding: 12px 6px 0; border-top: 1px solid var(--kenar);
               font-size: 13px; color: var(--soluk); }
  #kullanici b { color: var(--yazi); display: block; font-size: 14px; }
  header { border-bottom: 1px solid var(--altin2); justify-content: flex-start; gap: 10px; padding-top: 14px; }
  #saat { margin-right: auto; }
  header h1 { display: none; }
  #serit { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; padding: 14px 16px 4px; }
  .kartK { background: linear-gradient(180deg,var(--kart2),var(--kart)); border: 1px solid var(--kenar);
           border-radius: 14px; padding: 12px 14px; font-size: 13px; color: var(--soluk); }
  .kartK b { display: block; color: var(--yazi); font-size: 15px; margin-bottom: 4px; }
  .kartK.uyari { border-color: #7a3a2f; }
  .cubuk { height: 6px; background: #0a1226; border-radius: 4px; margin-top: 6px; overflow: hidden; }
  .cubuk i { display: block; height: 100%; background: linear-gradient(90deg,#2a8fe0,#4db6ff); }
  #icerik { flex-direction: row; gap: 14px; padding: 12px 16px 14px; }
  #sohbetKolon { flex: 1 1 58%; border: 1px solid var(--kenar); border-radius: 16px; background: rgba(13,23,48,.55);
                 overflow: hidden; }
  body[data-s="sohbet"] #pano { display: flex; flex-direction: column; gap: 12px; flex: 0 0 340px; overflow-y: auto; }
  .panel { flex: 1; }
}
#pano .kartK { color: var(--yazi); }
#pano h4 { margin: 0 0 8px; font-size: 14px; color: var(--altin); font-weight: 600; }
#pano .s { display: flex; justify-content: space-between; gap: 8px; padding: 5px 0; font-size: 13px;
           border-top: 1px solid var(--kenar); }
#pano .s span:last-child { color: var(--soluk); }
#pano .ok { color: var(--yesil) !important; } #pano .bekle { color: var(--altin) !important; }
@media (max-width: 899px) {
  #serit { display: none; }
  #ana { order: 1; } #yan { display: contents; }
  #sekmeler { order: 2; border-top: 1px solid var(--altin2); border-bottom: 0;
              padding: 6px 6px calc(env(safe-area-inset-bottom) + 6px); background: #060b17; }
}
</style>
</head>
<body>
<div id="kok">
<aside id="yan">
  <div id="marka"><i></i><b>ÜLGEN</b><small>Kişisel Yapay Zekâ Yardımcı</small></div>
  <nav id="sekmeler">
  <button class="aktif" data-s="sohbet" onclick="sekme('sohbet')">Ana Sayfa</button>
  <button data-s="gorevler" onclick="sekme('gorevler')">Görevler</button>
  <button data-s="ilac" onclick="sekme('ilac')">İlaç</button>
  <button data-s="bildirim" onclick="sekme('bildirim')">Bildirim</button>
  <button data-s="kasa" onclick="sekme('kasa')">Özel Kasa</button>
  <button data-s="sistem" onclick="sekme('sistem')">Sistem</button>
  </nav>
  <div id="kullanici"><b>Hakan Üste</b><span id="surumYazi">ÜLGEN</span> <span id="nokta2" class="nokta"></span></div>
</aside>
<div id="ana">
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
<div id="alt">
  <button id="mikBtn" class="yuvarlak" onclick="mikrofon()" title="Konuş">🎙</button>
  <textarea id="giris" rows="1" placeholder="Yazın ya da konuşun" onkeydown="tusla(event)"></textarea>
  <button class="yuvarlak gonder" onclick="gonder()" title="Gönder">➤</button>
</div>
</section>
<aside id="pano"></aside>
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
  const d = document.createElement("div");
  d.className = "balon " + tur;
  d.textContent = metin;
  const a = document.getElementById("akis");
  a.appendChild(d);
  a.scrollTop = a.scrollHeight;
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
let aktifSekme = "sohbet";

function sekme(ad) {
  aktifSekme = ad;
  document.body.dataset.s = ad;
  document.querySelectorAll("#sekmeler button").forEach(b => b.classList.toggle("aktif", b.dataset.s === ad));
  for (const [k, id] of Object.entries(paneller)) document.getElementById(id).classList.toggle("acik", k === ad);
  if (ad === "sohbet") panoYenile(); else panelYenile(ad);
}
document.body.dataset.s = "sohbet";

// ---- pano (geniş ekran): özet şeridi + sağ kartlar -------------------------
function kartK(ust, baslik, govde, ek) {
  const d = document.createElement("div"); d.className = "kartK" + (ek || "");
  const b = document.createElement("b"); b.textContent = baslik; d.appendChild(b);
  (Array.isArray(govde) ? govde : [govde]).forEach(g => {
    if (g instanceof Node) d.appendChild(g);
    else { const p = document.createElement("div"); p.textContent = g; d.appendChild(p); }
  });
  ust.appendChild(d); return d;
}
function cubuk(oran) { const c = document.createElement("div"); c.className = "cubuk";
  const i = document.createElement("i"); i.style.width = Math.max(0, Math.min(100, oran)) + "%"; c.appendChild(i); return c; }
function satirS(kap, a, b, sinif) { const r = document.createElement("div"); r.className = "s";
  const x = document.createElement("span"); x.textContent = a; const y = document.createElement("span"); y.textContent = b;
  if (sinif) y.className = sinif; r.appendChild(x); r.appendChild(y); kap.appendChild(r); }

async function panoYenile() {
  if (window.innerWidth < 900) return;
  try {
    const [g, il, sis] = await Promise.all([istek("/gorevler"), istek("/ilac/bugun"), istek("/sistem")]);
    const serit = document.getElementById("serit"); serit.replaceChildren();
    const bek = il.filter(x => x.durum === "bekliyor" || x.durum === "ertelendi" || x.durum === "yanitsiz").length;
    const acik = g.gorev.length;
    kartK(serit, "Günün Özeti", [acik + " görev · " + il.length + " ilaç · " + g.randevu.length + " randevu"]);
    kartK(serit, "İlaçlar", bek ? bek + " bekleyen doz" : "Bekleyen doz yok", bek ? " uyari" : "");
    kartK(serit, "Görevler", acik ? acik + " tamamlanmamış" : "Açık görev yok", acik ? " uyari" : "");
    kartK(serit, "Sağlık", ["Adım, nabız, uyku:", "Aşama 7'de (iPhone Sağlık köprüsü)"]);
    kartK(serit, "Sistem", ["ÜLGEN " + sis.surum + " · " + (sis.butunluk.saglam ? "Çalışıyor" : "SORUNLU"),
      "Veritabanı: " + (sis.veritabani_sifreli ? "şifreli" : "ŞİFRESİZ")], sis.veritabani_sifreli ? "" : " uyari");
    document.getElementById("surumYazi").textContent = "ÜLGEN " + sis.surum;
    const p = document.getElementById("pano"); p.replaceChildren();
    const k1 = kartK(p, "İlaç Takvimi", []);
    if (!il.length) satirS(k1, "Bugün doz yok", "");
    il.forEach(x => satirS(k1, "D" + x.id + " – " + x.ilac_ad, x.planli.slice(11, 16) + " " + durumYazi[x.durum].split(" ")[0],
      x.durum === "alindi" ? "ok" : (x.durum === "bekliyor" ? "bekle" : "")));
    const k2 = kartK(p, "Görevler", []);
    if (!g.gorev.length) satirS(k2, "Açık görev yok", "");
    g.gorev.slice(0, 6).forEach(x => satirS(k2, x.baslik, x.zaman ? x.zaman.slice(5, 16) : "Zamansız"));
    const k3 = kartK(p, "Yapay Zekâ Modelleri", []);
    sis.kota.forEach(t => satirS(k3, t.ad, t.engelli ? "Engelli" : "Hazır", t.engelli ? "" : "ok"));
    const k4 = kartK(p, "Sistem Durumu", []);
    const h = sis.donanim || {};
    if (h.cpu !== undefined) { satirS(k4, "CPU", Math.round(h.cpu) + "%"); k4.appendChild(cubuk(h.cpu)); }
    if (h.ram_toplam) { satirS(k4, "RAM", h.ram_kullanilan + " / " + h.ram_toplam + " GB"); k4.appendChild(cubuk(100 * h.ram_kullanilan / h.ram_toplam)); }
    if (h.disk_toplam) { satirS(k4, "Disk", h.disk_kullanilan + " / " + h.disk_toplam + " GB"); k4.appendChild(cubuk(100 * h.disk_kullanilan / h.disk_toplam)); }
  } catch (e) { /* oturum yoksa istek() zaten bildirir */ }
}
function saatYaz() {
  const d = new Date();
  document.getElementById("saat").textContent = d.toLocaleDateString("tr-TR", { weekday: "long", day: "numeric", month: "long" }) +
    "  " + d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
}
saatYaz(); setInterval(saatYaz, 20000); setInterval(() => { if (aktifSekme === "sohbet") panoYenile(); }, 30000);
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
  if (iyi && kopuk) { kopuk = false; denemeAraligi = 5000; ozetYukle(); if (aktifSekme !== "sohbet") panelYenile(aktifSekme); }
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
  if (!document.hidden) { bildirimleriAl(); if (aktifSekme !== "sohbet") panelYenile(aktifSekme); }
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
