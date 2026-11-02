import os, sys, tempfile, shutil
os.environ["HOME"] = tempfile.mkdtemp()
sys.path.insert(0, "/home/claude/Ulgen_proje")
from datetime import datetime, timedelta
from ulgen import veritabani, yedek, ayar, rapor
from ulgen.cekirdek import Ulgen
veritabani.kur(); u = Ulgen()
msgs = []
u.zamanlayici._bildir = msgs.append
for z in (u.zamanlayici.ilac, u.zamanlayici.gorev, u.zamanlayici.rapor): z._bildir = msgs.append
u.sohbet_isle("ilaç ekle: Alfa 08:00 20:00"); u.sohbet_isle("ilaç ekle: Beta 13:00")
u.sohbet_isle("görev ekle: kira öde yarın 10:00")
t = datetime(2026,11,2,0,0); son = t + timedelta(days=30)
n=0
while t < son:
    u.zamanlayici.adim(t); t += timedelta(minutes=1); n+=1
    if t.minute==2 and t.hour in (8,13,20):   # her doza "aldım" de
        for d in u.zamanlayici.ilac.acik_dozlar(t):
            u.zamanlayici.ilac.yanit(d["id"], "alindi", simdi=t)
c=lambda q: veritabani.sorgu(q,(),True)[0]["c"]
print("adım", n, "doz", c("SELECT COUNT(*) c FROM doz"), "alındı", c("SELECT COUNT(*) c FROM doz WHERE durum IN ('alindi','tamamlandi')"))
print("rapor sabah/aksam/hafta:", [c("SELECT COUNT(*) c FROM rapor WHERE tur='%s'"%x) for x in ("sabah","aksam","haftalik")])
print("bildirim sayısı", len(msgs))
print(rapor.haftalik(t)[:300])
# yedek -> bozma -> geri yükleme
veritabani.kapat()
d=tempfile.mkdtemp(); k=os.path.join(d,"y.bin")
veritabani.kur()
try:
    yedek.al(k, "parola123"); print("yedek ok", os.path.getsize(k))
except Exception as e: print("yedek fn adı farklı:", e, [x for x in dir(yedek) if not x.startswith('_')])
