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
</style>
</head>
<body>
<header>
  <h1><span id="nokta" class="nokta"></span>ÜLGEN</h1>
  <button id="sesBtn" class="dugme aktif" onclick="sesDegistir()">Ses: açık</button>
  <button id="surekliBtn" class="dugme" onclick="surekliDegistir()">Sürekli dinle: kapalı</button>
</header>
<div id="yaklasan"></div>
<div id="beyin" style="font-size:12px;color:var(--soluk);padding:2px 16px"></div>
<div id="akis"></div>
<div id="alt">
  <button id="mikBtn" class="yuvarlak" onclick="mikrofon()" title="Konuş">🎙</button>
  <textarea id="giris" rows="1" placeholder="Yazın ya da konuşun" onkeydown="tusla(event)"></textarea>
  <button class="yuvarlak gonder" onclick="gonder()" title="Gönder">➤</button>
</div>
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

async function bildirimleriAl() {
  try {
    const liste = await istek("/bildirimler?son=" + sonBildirim);
    for (const b of liste) {
      sonBildirim = Math.max(sonBildirim, b.id);
      balonEkle("⏰ " + b.metin, "bildirim");
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

anahtarIste();
istek("/durum").then(d => { sonBildirim = d.son_bildirim || 0; }).catch(() => {});
ozetYukle();
setInterval(ozetYukle, 60000);
setInterval(bildirimleriAl, 20000);
balonEkle("Merhaba, hoş geldiniz. Size nasıl yardımcı olabilirim?", "asistan");
</script>
</body>
</html>
"""
