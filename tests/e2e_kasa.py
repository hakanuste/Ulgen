import os, sys, tempfile, json
os.environ["HOME"] = tempfile.mkdtemp()
sys.path.insert(0, "/home/claude/Ulgen_proje")
from ulgen import sunucu, veritabani, cihazlar, ozelkasa
from ulgen.cekirdek import Ulgen
from playwright.sync_api import sync_playwright
veritabani.kur()
u = Ulgen()
srv = sunucu.yerel_sunucu(u, 0); sunucu.arka_planda_calistir(srv)
port = srv.server_address[1]
tok = cihazlar.olustur("e2e", 1)[1]
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context()
    pg = ctx.new_page()
    pg.on("dialog", lambda d: (print("DIYALOG:", d.message.replace("\n"," | ")[:160]), d.accept()))
    pg.on("pageerror", lambda e: print("JSHATA", e))
    cdp = ctx.new_cdp_session(pg)
    cdp.send("WebAuthn.enable")
    cdp.send("WebAuthn.addVirtualAuthenticator", {"options": {
        "protocol": "ctap2", "transport": "internal", "hasResidentKey": True,
        "hasUserVerification": True, "isUserVerified": True, "hasPrf": True,
        "automaticPresenceSimulation": True}})
    pg.add_init_script("localStorage.setItem('asistan_anahtar','%s')" % tok)
    pg.goto("http://localhost:%d/" % port)
    pg.click("button[data-s=kasa]")
    pg.fill("#pKasa input[type=password]", "dogru-parola-123")
    pg.click("text=Kasayı kur"); pg.wait_for_timeout(1500)
    pg.fill("#pKasa input[type=password]", "dogru-parola-123")
    pg.click("text=Face ID'yi bağla"); pg.wait_for_timeout(2500)
    print("passkey sayisi:", ozelkasa.passkey_sayisi())
    pg.fill("#pKasa input[type=password]", "dogru-parola-123")
    pg.fill("#pKasa input[type=text]", "banka")
    pg.fill("#pKasa textarea", "IBAN-GIZLI-77")
    pg.click("text=Kasaya ekle"); pg.wait_for_timeout(1500)
    print("adlar:", ozelkasa.adlar())
    print(u.sohbet_isle("özel kasadan banka getir")["yanit"][:80])
    pg.click("button[data-s=sohbet]"); pg.click("button[data-s=kasa]"); pg.wait_for_timeout(800)
    pg.click("text=Face ID ile onayla"); pg.wait_for_timeout(2500)
    print("EKRAN:", pg.inner_text("#pKasa pre"))
    pg.click("text=Face ID ile onayla") if pg.locator("text=Face ID ile onayla").count() else print("istek yakildi (tekrar yok)")
    b.close()
