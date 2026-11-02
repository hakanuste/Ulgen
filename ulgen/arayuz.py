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
</style>
</head>
<body>
<header>
  <h1><span id="nokta" class="nokta"></span>ÜLGEN</h1>
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
<div id="sekmeler">
  <button class="aktif" data-s="sohbet" onclick="sekme('sohbet')">Sohbet</button>
  <button data-s="gorevler" onclick="sekme('gorevler')">Görevler</button>
  <button data-s="ilac" onclick="sekme('ilac')">İlaç</button>
  <button data-s="bildirim" onclick="sekme('bildirim')">Bildirim</button>
  <button data-s="sistem" onclick="sekme('sistem')">Sistem</button>
</div>
<div id="pGorevler" class="panel"></div>
<div id="pIlac" class="panel"></div>
<div id="pBildirim" class="panel"></div>
<div id="pSistem" class="panel"></div>
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

// ---- sekmeler ------------------------------------------------------------
const paneller = { gorevler: "pGorevler", ilac: "pIlac", bildirim: "pBildirim", sistem: "pSistem" };
const gecmisBildirim = [];
let aktifSekme = "sohbet";

function sekme(ad) {
  aktifSekme = ad;
  document.querySelectorAll("#sekmeler button").forEach(b => b.classList.toggle("aktif", b.dataset.s === ad));
  for (const [k, id] of Object.entries(paneller)) document.getElementById(id).classList.toggle("acik", k === ad);
  const sohbet = ad === "sohbet";
  for (const id of ["yaklasan", "beyin", "akis", "alt"]) document.getElementById(id).style.display = sohbet ? "" : "none";
  if (!sohbet) panelYenile(ad);
}

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
