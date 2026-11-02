import os, sys, tempfile
os.environ["HOME"] = tempfile.mkdtemp()
sys.path.insert(0, "/home/claude/Ulgen_proje")
from ulgen import sunucu, veritabani, cihazlar
from ulgen.cekirdek import Ulgen
from playwright.sync_api import sync_playwright
veritabani.kur(); u = Ulgen()
u.sohbet_isle("ilaç ekle: Alfa 10:00 18:57"); u.zamanlayici.adim(__import__("datetime").datetime.now())
u.sohbet_isle("görev ekle: #1 faturayı öde bugün")
srv = sunucu.yerel_sunucu(u, 0); sunucu.arka_planda_calistir(srv)
port = srv.server_address[1]; tok = cihazlar.olustur("ui", 1)[1]
with sync_playwright() as p:
    b = p.chromium.launch()
    for ad, vp in (("masaustu", (1672, 941)), ("telefon", (430, 900))):
        pg = b.new_page(viewport={"width": vp[0], "height": vp[1]})
        pg.on("pageerror", lambda e: print("JSHATA", e))
        pg.add_init_script("localStorage.setItem('asistan_anahtar','%s')" % tok)
        pg.goto("http://127.0.0.1:%d/" % port); pg.wait_for_timeout(1800)
        pg.screenshot(path="/tmp/e2e/%s.png" % ad)
        if ad == "masaustu":
            pg.click("button[data-s=sistem]"); pg.wait_for_timeout(800)
            pg.screenshot(path="/tmp/e2e/masaustu-sistem.png")
    b.close()
