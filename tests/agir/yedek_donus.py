import os, sys, tempfile
os.environ["HOME"] = tempfile.mkdtemp()
sys.path.insert(0, "/home/claude/Ulgen_proje")
from ulgen import veritabani, yedek
from ulgen.cekirdek import Ulgen
veritabani.kur(); u = Ulgen()
for i in range(50): u.sohbet_isle("görev ekle: g%d"%i)
d=tempfile.mkdtemp(); k=os.path.join(d,"y.bin")
yedek.al(k,"parola123")
c=lambda: veritabani.sorgu("SELECT COUNT(*) c FROM gorev",(),True)[0]["c"]
print("önce", c())
veritabani.sorgu("DELETE FROM gorev")
print("silindi", c())
yedek.geri_yukle(k,"parola123"); print("geri yüklendi", c())
try: yedek.geri_yukle(k,"yanlis"); print("YANLIŞ PAROLA KABUL EDİLDİ!")
except Exception as e: print("yanlış parola reddedildi:", type(e).__name__)
b=bytearray(open(k,"rb").read()); b[len(b)//2]^=0xFF; open(k+"2","wb").write(b)
try: yedek.geri_yukle(k+"2","parola123"); print("BOZUK YEDEK KABUL EDİLDİ!")
except Exception as e: print("bozuk yedek reddedildi:", type(e).__name__)
print("sonra", c(), veritabani.sorgu("PRAGMA integrity_check",(),True))
# düz sqlite okunamaz mı
import sqlite3
p=os.path.expanduser("~/ÜlgenVeri/veri.db")
try: sqlite3.connect(p).execute("select count(*) from sqlite_master").fetchone(); print("DB DÜZ OKUNDU (şifresiz!)")
except Exception as e: print("DB düz sqlite ile okunamıyor:", e)
