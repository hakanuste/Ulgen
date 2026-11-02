import os, sys, tempfile, json, random, string, threading, http.client, time
os.environ["HOME"] = tempfile.mkdtemp()
sys.path.insert(0, "/home/claude/Ulgen_proje")
from ulgen import sunucu, veritabani, cihazlar, ayar
from ulgen.cekirdek import Ulgen
veritabani.kur(); u = Ulgen()
srv = sunucu.yerel_sunucu(u, 0); sunucu.arka_planda_calistir(srv)
port = srv.server_address[1]; tok = cihazlar.olustur("agir", 1)[1]
H = {"Authorization": "Bearer " + tok, "Content-Type": "application/json"}
def rq(m, y, b=None, h=None, host=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
    hh = dict(h if h is not None else H)
    if host: hh["Host"] = host
    c.request(m, y, body=b, headers=hh); r = c.getresponse(); d = r.read(); c.close(); return r.status, d, r.headers
hata = []
# 2) kötü Host, yol gezme, dev gövde, bozuk JSON
if rq("GET","/sistem",host="evil.com")[0] == 200: hata.append("host")
for y in ["/../../etc/passwd","/varlik/../ayar.json","/varlik/%2e%2e/x","//etc/passwd"]:
    k,d,_ = rq("GET", y)
    if b"root:" in d: hata.append(("gezinme", y))
for g in [b"{", b"[]", b"null", b"\xff\xfe", b"x"*300000, json.dumps({"metin": "a"*100000}).encode()]:
    k = rq("POST", "/sohbet", g)[0]
    if k >= 500: hata.append(("govde", len(g), k))
# 3) bulanık sohbet girdileri
rnd = random.Random(7)
girdiler = ["".join(rnd.choice(string.printable+"ğüşöçıİ✓\u0000") for _ in range(rnd.randint(0,120))) for _ in range(400)]
girdiler += ["ilaç ekle: X 99:99","ilaç ekle:","görev ekle:","tamam #999999","aldım D1","sabah raporu","haftalık raporu","özel kasadan banka getir","rm -rf /","terminal: rm -rf ~","hatırlat 25:61 x","hafızayı sil","'; DROP TABLE doz;--","ilaç ekle: A 08:00 ve 08:00 ve 08:00","akşam raporu ver"]
for g in girdiler:
    k,d,_ = rq("POST","/sohbet",json.dumps({"metin":g}).encode())
    if k >= 500: hata.append(("sohbet", g[:40], k))
# 4) eşzamanlı yük
sonuc = []
def is_(i):
    for j in range(25):
        k = rq("POST","/sohbet",json.dumps({"metin":"görev ekle: yük %d-%d"%(i,j)}).encode())[0]
        k2 = rq("GET","/sistem")[0]
        sonuc.append((k,k2))
ts = [threading.Thread(target=is_, args=(i,)) for i in range(16)]
t0=time.time(); [t.start() for t in ts]; [t.join() for t in ts]
print("yük 800 çift istek %.1f sn" % (time.time()-t0))
bad = [s for s in sonuc if s[0]!=200 or s[1]!=200]
if bad: hata.append(("yük", len(bad), bad[:3]))
# 5) başlıklar
_,_,h = rq("GET","/")
for n in ["Content-Security-Policy","X-Content-Type-Options","Cross-Origin-Opener-Policy"]:
    if n not in h: hata.append(("baslik", n))
# 6) veri bütünlüğü
r = veritabani.sorgu("PRAGMA integrity_check", (), True)
print("integrity:", r)
n = veritabani.sorgu("SELECT COUNT(*) c FROM gorev WHERE baslik LIKE 'yük%'", (), True)[0]["c"]
print("kaydedilen görev:", n, "(beklenen 400)")
if n != 400: hata.append(("kayip", n))
# 1) yetkisiz her uç
for y in ["/sistem","/ayar/ozet","/raporlar","/saglik/bugun","/ilac/bugun","/kasa/durum","/hava","/ses/durum","/projeler","/bilgi/ara?q=a"]:
    k = rq("GET", y, h={})[0]
    if k not in (401, 404): hata.append(("yetkisiz", y, k))
# doz kimliği yalıtımı
for g in ["ilaç ekle: Alfa 10:00","ilaç ekle: Beta 10:00"]: u.sohbet_isle(g)
from datetime import datetime
u.zamanlayici.ilac.doz_uret(datetime.now().replace(hour=10, minute=1))
print("DOZ HATA SAYISI", len(hata)); print(hata)
