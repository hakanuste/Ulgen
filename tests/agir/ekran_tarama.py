import os, sys, tempfile
os.environ["HOME"] = tempfile.mkdtemp()
sys.path.insert(0, "/home/claude/Ulgen_proje")
from ulgen import sunucu, veritabani, cihazlar
from ulgen.cekirdek import Ulgen
from playwright.sync_api import sync_playwright
veritabani.kur(); u = Ulgen(); u.sohbet_isle("ilaç ekle: Alfa 10:00"); u.sohbet_isle("görev ekle: x")
srv = sunucu.yerel_sunucu(u, 0); sunucu.arka_planda_calistir(srv)
port = srv.server_address[1]; tok = cihazlar.olustur("t", 1)[1]
sorun=[]
with sync_playwright() as p:
    b = p.chromium.launch()
    for ad,vp in (("masaustu",(1672,941)),("m1240",(1240,700)),("m1280",(1280,720)),("ipadyatay",(1180,820)),("ipad",(820,1180)),("iphone14plus",(430,932)),("kucuk",(360,640)),("yatay",(932,430))):
        pg = b.new_page(viewport={"width":vp[0],"height":vp[1]})
        pg.on("pageerror", lambda e: sorun.append(("JS",ad,str(e)[:120])))
        pg.on("console", lambda m: sorun.append(("KONSOL",ad,m.text[:120])) if m.type=="error" else None)
        pg.add_init_script("localStorage.setItem('asistan_anahtar','%s')"%tok)
        pg.goto("http://127.0.0.1:%d/"%port); pg.wait_for_timeout(500)
        tabs = pg.eval_on_selector_all("[data-s]","els=>[...new Set(els.map(e=>e.dataset.s))]")
        for t in tabs:
            pg.evaluate("t=>{const b=document.querySelector('button[data-s=%s]')||document.querySelector('[data-s=%s]'); b&&b.click();}"%(t,t) if False else "t=>{const e=[...document.querySelectorAll('[data-s]')].find(x=>x.dataset.s===t&&x.tagName==='BUTTON'); if(e) e.click();}", t)
            pg.wait_for_timeout(150)
            tas = pg.evaluate("document.documentElement.scrollWidth-innerWidth")
            if tas>0: sorun.append(("TAŞMA",ad,t,tas))
        pg.evaluate("()=>{const e=[...document.querySelectorAll('[data-s]')].find(x=>x.dataset.s==='sohbet'&&x.tagName==='BUTTON'); if(e) e.click();}"); pg.wait_for_timeout(200)
        pg.fill("#giris","merhaba"); pg.click(".gonder"); pg.wait_for_timeout(800)
        print(ad,"sekme:",len(tabs))
    b.close()
print("SORUN:",sorun)
