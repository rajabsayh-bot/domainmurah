import re
import time
import requests
import random
import string
from datetime import datetime

# ==============================================
# ⚙️ KONFIGURASI
# ==============================================
BASE_URL    = "https://hosting.arxan.app"
MAILTM_API  = "https://api.mail.tm"
PASS_MAILTM = "Akun77@@"
DOMAIN_TM   = "web-library.net"
USER_AGENT  = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36"
TIMEOUT     = 20
JEDA        = 0.8

# ==============================================
# 📧 BUAT 1 AKUN MAIL.TM SAJA
# ==============================================
def rand_str(p=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=p))

def buat_satu_akun():
    print("🔄 Membuat akun utama...")
    for _ in range(10):
        alamat = f"{rand_str()}@{DOMAIN_TM}"
        try:
            r = requests.post(
                f"{MAILTM_API}/accounts",
                json={"address": alamat, "password": PASS_MAILTM},
                headers={"Content-Type": "application/json"},
                timeout=TIMEOUT
            )
            if r.status_code == 201:
                r_login = requests.post(
                    f"{MAILTM_API}/token",
                    json={"address": alamat, "password": PASS_MAILTM},
                    headers={"Content-Type": "application/json"},
                    timeout=TIMEOUT
                )
                if r_login.status_code == 200:
                    print(f"✅ Akun utama siap: {alamat}")
                    return alamat, PASS_MAILTM
            elif "already used" in r.text.lower():
                time.sleep(0.2)
        except:
            time.sleep(0.4)
    return None, None

# ==============================================
# 🎲 DATA AKUN
# ==============================================
def data_acak():
    return {
        "firstname": rand_str(5).capitalize(),
        "lastname": rand_str(7).capitalize(),
        "phonenumber": "628" + ''.join(random.choices(string.digits, k=9)),
        "address1": f"Jl. {rand_str(8)} No.{random.randint(1,200)}",
        "city": "Sukabumi",
        "state": "Jawa Barat",
        "postcode": "43111",
        "country": "ID",
        "paymentmethod": "duitkupop"
    }

# ==============================================
# 🛠️ FUNGSI PENDUKUNG
# ==============================================
def get_token(sesi):
    for _ in range(2):
        try:
            r = sesi.get(f"{BASE_URL}/cart.php?a=add&domain=register", timeout=TIMEOUT)
            token = re.search(r'name="token" value="([a-f0-9]{32,})"', r.text)
            if token:
                return token.group(1)
        except:
            pass
        time.sleep(0.5)
    return None

def cek_domain(sesi, token, domain):
    try:
        res = sesi.post(
            f"{BASE_URL}/index.php?rp=/domain/check",
            headers={"Content-Type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest"},
            data={"token": token, "a": "checkDomain", "domain": domain, "type": "domain"},
            timeout=TIMEOUT
        )
        return res.status_code == 200 and "available" in res.text.lower()
    except:
        return False

# ==============================================
# 🚀 PROSES UTAMA
# ==============================================
def main():
    print("="*50)
    print("🚀 1 AKUN UNTUK BANYAK DOMAIN")
    print("💡 Harga total = jumlah × harga per domain")
    print("="*50)

    # Langkah 1: Buat akun utama
    email_utama, pass_utama = buat_satu_akun()
    if not email_utama:
        print("❌ Gagal buat akun utama!")
        return

    # Langkah 2: Tentukan jumlah domain
    try:
        jumlah = int(input("\n🔢 Mau pesan berapa domain? : "))
        if jumlah < 1:
            print("❌ Minimal 1!")
            return
    except:
        print("❌ Masukkan angka yang benar!")
        return

    # Langkah 3: Input daftar domain
    daftar_domain = []
    print(f"\n📝 Masukkan {jumlah} domain satu per satu:")
    for i in range(1, jumlah+1):
        while True:
            d = input(f"Domain ke-{i}: ").strip().lower()
            if "." in d and len(d) > 4:
                daftar_domain.append(d)
                break
            print("⚠️ Format salah, coba lagi!")

    # Langkah 4: Masukkan semua ke keranjang
    print("\n🔄 Memproses semua domain ke dalam 1 akun...")
    sesi = requests.Session()
    sesi.headers.update({"User-Agent": USER_AGENT})
    token = get_token(sesi)

    if not token:
        print("❌ Gagal dapat token!")
        return

    domain_valid = []
    for domain in daftar_domain:
        print(f"➡️ Cek: {domain}")
        if cek_domain(sesi, token, domain):
            sesi.post(
                f"{BASE_URL}/cart.php",
                data={"a": "addToCart", "domain": domain, "token": token, "whois": 0, "sideorder": 0},
                timeout=TIMEOUT
            )
            domain_valid.append(domain)
            print(f"✅ Ditambahkan ke keranjang")
        else:
            print(f"❌ Tidak tersedia / sudah dipakai")
        time.sleep(JEDA)

    if not domain_valid:
        print("\n❌ Tidak ada domain yang bisa diproses!")
        return

    print(f"\n✅ Total masuk keranjang: {len(domain_valid)} domain")
    print("💵 Harga =", len(domain_valid), "× harga satuan =", len(domain_valid), "perak")

    # Langkah 5: Proses checkout
    sandi_akun = input("\n🔑 Buat password untuk akun ini: ").strip()
    if len(sandi_akun) < 6:
        print("❌ Password minimal 6 karakter!")
        return

    data = data_acak()
    data["email"] = email_utama
    data["password"] = data["password2"] = sandi_akun

    print("\n🔄 Menyelesaikan pembayaran...")
    sesi.post(
        f"{BASE_URL}/cart.php?a=confdomains",
        data={"token": token, "update": "true", "domainns1": "kiki.bunny.net", "domainns2": "coco.bunny.net"},
        timeout=TIMEOUT
    )

    res = sesi.post(
        f"{BASE_URL}/cart.php?a=checkout",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": BASE_URL, "Referer": f"{BASE_URL}/cart.php?a=checkout"},
        data={
            "token": token, "checkout": "true", "custtype": "new",
            "firstname": data["firstname"], "lastname": data["lastname"],
            "email": data["email"], "phonenumber": data["phonenumber"],
            "address1": data["address1"], "city": data["city"],
            "state": data["state"], "postcode": data["postcode"], "country": data["country"],
            "password": data["password"], "password2": data["password2"],
            "paymentmethod": "duitkupop", "accepttos": "on"
        },
        timeout=TIMEOUT,
        allow_redirects=True
    )

    inv = re.search(r'viewinvoice\.php\?id=(\d+)', res.text)
    waktu = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Simpan hasil
    hasil = f"""
=====================================
📋 HASIL PEMESANAN
Waktu   : {waktu}
Jumlah  : {len(domain_valid)} domain
Harga   : {len(domain_valid)} perak
=====================================
📧 Email Akun    : {email_utama}
🔑 Pass Akun     : {sandi_akun}
🔑 Pass Mail.TM  : {pass_utama}
🌐 Daftar Domain :
"""
    for no, d in enumerate(domain_valid, 1):
        hasil += f"{no}. {d}\n"

    if inv:
        link = f"{BASE_URL}/viewinvoice.php?id={inv.group(1)}"
        hasil += f"\n🔗 Link Invoice: {link}\n✅ Status: Berhasil"
    else:
        hasil += "\n❌ Status: Gagal saat checkout"

    print("\n" + hasil)
    with open(f"hasil_satuakun_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w", encoding="utf-8") as f:
        f.write(hasil)
    print("\n✅ Data tersimpan otomatis ke file .txt")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Proses dihentikan")