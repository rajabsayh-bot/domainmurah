import os
import re
import json
import time
import random
import requests
from datetime import datetime
from colorama import Fore, Style, init

# Inisialisasi warna teks
init(autoreset=True)

# ==============================================
# ✅ KONFIGURASI
# ==============================================
NAMA_JSON = "data_regis.json"
NAMA_TXT  = "daftar_regis.txt"
BASE_URL  = "https://hosting.arxan.app"
TIMEOUT = 15

# 📋 Daftar User-Agent acak
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 14; SM-S921B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Redmi Note 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
]

# ==============================================
# 📋 Ambil Token
# ==============================================
def get_token(sesi):
    try:
        r = sesi.get(f"{BASE_URL}/cart.php?a=add&domain=register", timeout=TIMEOUT)
        return re.search(r'name="token" value="([a-f0-9]{32,})"', r.text).group(1)
    except Exception as e:
        return None

# ==============================================
# 🖼️ Tampil QRIS
# ==============================================
def tampil_qr(kode):
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=1, border=1)
        qr.add_data(kode)
        qr.make(fit=True)
        return "\n".join("".join("██" if b else "  " for b in baris) for baris in qr.get_matrix())
    except:
        return "⚠️ QR tidak bisa dibuat"

# ==============================================
# 🚀 Proses Satu Domain
# ==============================================
def proses_domain(domain, email, password):
    # Ambil User-Agent acak
    ua = random.choice(USER_AGENTS)

    sesi = requests.Session()
    sesi.headers.update({
        "User-Agent": ua,
        "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br"
    })

    hasil = {
        "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "domain": domain,
        "email": email,
        "password": password,
        "user_agent": ua,
        "harga": "-",
        "invoice": "-",
        "link": "-",
        "qris": "-",
        "status": "",
        "info": "-"
    }

    print(Fore.YELLOW + f"ℹ️ Pakai UA: {ua[:60]}...")

    token = get_token(sesi)
    if not token:
        hasil["status"] = "❌ Gagal dapat token"
        return hasil

    # Cek domain & harga
    try:
        r_cek = sesi.post(
            f"{BASE_URL}/index.php?rp=/domain/check",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{BASE_URL}/cart.php?a=add&domain=register"
            },
            data={"token": token, "a": "checkDomain", "domain": domain, "type": "domain"},
            timeout=TIMEOUT
        )
        if "available" in r_cek.text.lower():
            harga = re.search(r'Rp\s*(\d+)', r_cek.text)
            hasil["harga"] = f"Rp {harga.group(1)}" if harga else "Rp -"
        else:
            hasil["status"] = "❌ Domain tidak tersedia"
            return hasil
    except:
        hasil["status"] = "⚠️ Gagal cek domain"
        return hasil

    # Masuk keranjang
    sesi.post(
        f"{BASE_URL}/cart.php",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": f"{BASE_URL}/cart.php?a=add&domain=register"
        },
        data={
            "a": "addToCart",
            "domain": domain,
            "token": token,
            "years": 1,
            "idprotection": 0,
            "dnsmanagement": 0,
            "emailforwarding": 0,
            "whois": 0
        },
        timeout=TIMEOUT
    )
    time.sleep(0.4)

    # Set nameserver
    sesi.post(
        f"{BASE_URL}/cart.php?a=confdomains",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "token": token,
            "update": "true",
            "domainns1": "kiki.bunny.net",
            "domainns2": "coco.bunny.net"
        },
        timeout=TIMEOUT
    )
    time.sleep(0.4)

    # Set wilayah
    sesi.post(
        f"{BASE_URL}/cart.php?a=setstateandcountry&e=false",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"token": token, "country": "ID", "state": "Jawa Barat", "ajax": 1},
        timeout=TIMEOUT
    )
    time.sleep(0.4)

    # Proses checkout
    res = sesi.post(
        f"{BASE_URL}/cart.php?a=checkout",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/cart.php?a=confdomains"
        },
        data={
            "token": token,
            "checkout": "true",
            "custtype": "new",
            "firstname": "Budi",
            "lastname": "Santoso",
            "email": email,
            "emailoptin": "0",
            "phonenumber": "628123456789",
            "address1": "Jl. Mawar No.1",
            "city": "Sukabumi",
            "state": "Jawa Barat",
            "postcode": "43111",
            "country": "ID",
            "password": password,
            "password2": password,
            "securityqid": "0",
            "securityans": "",
            "paymentmethod": "duitkupop",
            "accepttos": "on",
            "marketingoptin": "0"
        },
        timeout=20,
        allow_redirects=True
    )

    # Cek hasil
    if "viewinvoice.php" in res.text or "viewinvoice.php" in res.url:
        inv = re.search(r'viewinvoice\.php\?id=(\d+)', res.text + res.url)
        if inv:
            hasil["invoice"] = inv.group(1)
            hasil["link"] = f"{BASE_URL}/viewinvoice.php?id={inv.group(1)}"
            hasil["status"] = "✅ Berhasil"
            r_qr = sesi.get(hasil["link"], timeout=12)
            kode_qr = re.search(r'data-qr="([^"]+)"', r_qr.text)
            hasil["qris"] = tampil_qr(kode_qr.group(1)) if kode_qr else "❌ QR tidak ada"
    else:
        err = re.search(r'<div class="alert[^>]*>(.*?)</div>|<li>(.*?)</li>', res.text, re.S)
        hasil["info"] = (err.group(1) or err.group(2) or "Tidak ada pesan error")[:180].strip()
        hasil["status"] = "❌ Gagal"

    return hasil

# ==============================================
# 💾 Tampil & Simpan Hasil
# ==============================================
def tampilkan_semua(daftar):
    print(Fore.GREEN + "\n" + "=" * 60)
    for no, h in enumerate(daftar, 1):
        print(f"{Fore.CYAN}🔹 No.{no}")
        print(f"🌐 Domain   : {h['domain']}")
        print(f"💲 Harga    : {h['harga']}")
        print(f"📧 Email    : {h['email']}")
        print(f"🔑 Password : {h['password']}")
        print(f"📊 Status   : {h['status']}")
        if "✅" in h["status"]:
            print(f"🧾 Invoice  : {h['invoice']}")
            print(f"🔗 Link     : {h['link']}")
            print(f"📱 QRIS     :\n{h['qris']}")
        if "❌" in h["status"]:
            print(f"ℹ️ Info     : {h['info']}")
        print(Fore.GREEN + "-" * 60)

def simpan_semua(daftar):
    with open(NAMA_JSON, "w", encoding="utf-8") as f:
        json.dump(daftar, f, indent=2, ensure_ascii=False)
    with open(NAMA_TXT, "a", encoding="utf-8") as f:
        for h in daftar:
            f.write(f"""
WAKTU   : {h['waktu']}
DOMAIN  : {h['domain']}
HARGA   : {h['harga']}
EMAIL   : {h['email']}
PASS    : {h['password']}
UA      : {h['user_agent']}
STATUS  : {h['status']}
INFO    : {h['info']}
----------------------------------------
""")

# ==============================================
# 🚀 Menu Utama
# ==============================================
if __name__ == "__main__":
    os.system("clear" if os.name == "posix" else "cls")
    print(Fore.MAGENTA + Style.BRIGHT + """
╔══════════════════════════════════════════════╗
║          TOOLS DAFTAR DOMAIN                 ║
║ ✅ User-Agent Acak | Tanpa Proxy             ║
╚══════════════════════════════════════════════╝
    """)

    # Jumlah domain
    while True:
        try:
            jml = int(input(Fore.YELLOW + "\n🔢 Mau proses berapa domain? : "))
            if jml > 0:
                break
            print(Fore.RED + "❌ Angka harus lebih dari 0!")
        except:
            print(Fore.RED + "❌ Masukkan angka yang benar!")

    # Masukkan domain
    daftar_domain = []
    for i in range(1, jml + 1):
        while True:
            d = input(Fore.YELLOW + f"📝 Domain ke-{i}: ").strip().lower()
            if "." in d and len(d) > 5:
                daftar_domain.append(d)
                break
            print(Fore.RED + "⚠️ Format salah! Contoh: namamu.biz.id")

    # Masukkan email
    while True:
        email = input(Fore.YELLOW + "\n📧 Masukkan email: ").strip().lower()
        if "@" in email and "." in email.split("@")[-1]:
            break
        print(Fore.RED + "❌ Format email salah!")

    # Masukkan password
    while True:
        pw = input(Fore.YELLOW + "🔑 Masukkan password akun: ").strip()
        if len(pw) >= 6:
            break
        print(Fore.RED + "❌ Password minimal 6 karakter!")

    # Proses semua
    print(Fore.BLUE + "\n🔃 Memproses...\n")
    hasil_akhir = []
    for d in daftar_domain:
        print(Fore.CYAN + f"➡️ Memproses: {d}")
        hasil_akhir.append(proses_domain(d, email, pw))
        time.sleep(0.8)

    tampilkan_semua(hasil_akhir)
    simpan_semua(hasil_akhir)
    print(Fore.GREEN + "\n✅ Selesai!")
