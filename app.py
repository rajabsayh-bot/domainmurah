from flask import Flask, render_template_string, request, jsonify
import re
import time
import random
import requests
from datetime import datetime
import qrcode
from io import BytesIO
import base64

app = Flask(__name__)

# ==============================================
# ✅ KONFIGURASI
# ==============================================
BASE_URL = "https://hosting.arxan.app"
HCAPTCHA_SITEKEY = "a5f74b19-9e6a-4ff0-a1b3-8d1201791129"
TIMEOUT = 30
MAX_DOMAIN = 50

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; M2006C3MG Build/QP1A.190711.020) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.7827.91 Mobile Safari/537.36"
]

# ==============================================
# 🛠️ FUNGSI
# ==============================================
def get_token(sesi):
    try:
        r = sesi.get(f"{BASE_URL}/cart.php?a=add&domain=register", timeout=TIMEOUT)
        match = re.search(r'name="token" value="([a-f0-9]{32,})"', r.text)
        return match.group(1) if match else None
    except:
        return None

def cek_domain_tersedia(sesi, token, domain):
    try:
        r = sesi.post(
            f"{BASE_URL}/cart.php?a=checkdomain",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{BASE_URL}/cart.php?a=add&domain=register"
            },
            data={"token": token, "domain": domain, "sld": domain.split(".")[0], "tld": "." + domain.split(".")[1], "action": "check"},
            timeout=TIMEOUT
        )
        return "available" in r.text.lower()
    except:
        return False

def tambah_ke_keranjang(sesi, token, domain):
    try:
        r = sesi.post(
            f"{BASE_URL}/cart.php",
            headers={"Referer": f"{BASE_URL}/cart.php?a=add&domain=register"},
            data={"a": "addDomain", "token": token, "domain": domain, "regperiod": 1, "dnsmanagement": 0, "emailforwarding": 0, "idprotection": 0},
            timeout=TIMEOUT
        )
        return "success" in r.text.lower() or "added" in r.text.lower()
    except:
        return False

def buat_qr_base64(data):
    try:
        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()
    except:
        return ""

# ==============================================
# 🚀 PROSES UTAMA
# ==============================================
def proses_semua(daftar_domain, email, password, captcha_token=""):
    sesi = requests.Session()
    sesi.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    })

    hasil = {
        "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "jumlah": len(daftar_domain),
        "daftar": daftar_domain,
        "email": email,
        "password": password,
        "total_harga": "Rp 0",
        "invoice_id": "-",
        "link_invoice": "-",
        "qris": "",
        "status": "",
        "keterangan": ""
    }

    token = get_token(sesi)
    if not token:
        hasil["status"] = "❌ Gagal dapat token akses"
        return hasil

    domain_berhasil = []
    for domain in daftar_domain:
        if cek_domain_tersedia(sesi, token, domain):
            if tambah_ke_keranjang(sesi, token, domain):
                domain_berhasil.append(domain)
                hasil["keterangan"] += f"✅ {domain} masuk keranjang | "
            else:
                hasil["keterangan"] += f"⚠️ {domain} gagal masuk | "
        else:
            hasil["keterangan"] += f"❌ {domain} tidak tersedia | "
        time.sleep(0.4)

    if not domain_berhasil:
        hasil["status"] = "❌ Tidak ada domain bisa diproses"
        return hasil

    hasil["total_harga"] = f"Rp {len(domain_berhasil):,}"

    # LANGSUNG KE CHECKOUT DENGAN DATA LENGKAP & BENAR
    try:
        sesi.post(f"{BASE_URL}/cart.php?a=confdomains", data={"token": token, "update": "true", "domainns1": "kiki.bunny.net", "domainns2": "coco.bunny.net"}, timeout=TIMEOUT)
        time.sleep(0.5)

        sesi.post(f"{BASE_URL}/cart.php?a=setstateandcountry", data={"token": token, "country": "ID", "state": "Jawa Barat"}, timeout=TIMEOUT)
        time.sleep(0.5)

        # ✅ DATA CHECKOUT DIPERBAIKI SESUAI FORMAT WHMCS
        data_checkout = {
            "token": token,
            "checkout": "true",
            "custtype": "new",
            "firstname": "Budi",
            "lastname": "Santoso",
            "email": email,
            "emailoptin": "0",
            "phonenumber": "628123456789",
            "address1": "Jl. Mawar No.1",
            "address2": "",
            "city": "Sukabumi",
            "state": "Jawa Barat",
            "postcode": "43111",
            "country": "ID",
            "password": password,
            "password2": password,
            "securityqid": "0",
            "securityans": "",
            "h-captcha-response": captcha_token.strip(),
            "paymentmethod": "duitkupop",
            "accepttos": "1"
        }

        res = sesi.post(
            f"{BASE_URL}/cart.php?a=checkout",
            headers={
                "Origin": BASE_URL,
                "Referer": f"{BASE_URL}/cart.php?a=confdomains",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data=data_checkout,
            timeout=30,
            allow_redirects=True
        )

        # AMBIL LINK INVOICE
        if "viewinvoice.php" in res.text or "viewinvoice.php" in res.url:
            inv = re.search(r'viewinvoice\.php\?id=(\d+)', res.text + res.url)
            if inv:
                hasil["invoice_id"] = inv.group(1)
                hasil["link_invoice"] = f"{BASE_URL}/viewinvoice.php?id={inv.group(1)}"
                hasil["status"] = f"✅ BERHASIL | Invoice #{inv.group(1)} didapat"
                r_qr = sesi.get(hasil["link_invoice"], timeout=15)
                kode_qr = re.search(r'data-qr="([^"]+)"', r_qr.text)
                if kode_qr:
                    hasil["qris"] = buat_qr_base64(kode_qr.group(1))
            else:
                hasil["status"] = "⚠️ Berhasil masuk, tapi tidak dapat nomor invoice"
        else:
            err = re.search(r'<div class="alert[^>]*>(.*?)</div>', res.text, re.S)
            pesan = (err.group(1).strip() if err else "Belum selesai")[:150]
            
            if "captcha" in pesan.lower():
                hasil["status"] = "🔐 Perlu isi hCaptcha di bawah"
                hasil["keterangan"] += f" | Selesaikan verifikasi lalu proses lagi"
            elif "password" in pesan.lower():
                hasil["status"] = "❌ Password ditolak"
                hasil["keterangan"] += f" | Saran: gunakan 8-16 karakter, campur huruf & angka"
            else:
                hasil["status"] = "ℹ️ Belum selesai"
                hasil["keterangan"] += f" | Pesan situs: {pesan}"

    except Exception as e:
        hasil["status"] = "❌ Kesalahan proses akhir"
        hasil["keterangan"] += f" | Detail: {str(e)[:50]}"

    return hasil

# ==============================================
# 🎨 HALAMAN
# ==============================================
HALAMAN_HTML = f"""
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tools Beli Domain</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://js.hcaptcha.com/1/api.js" async defer></script>
</head>
<body class="bg-gray-100 min-h-screen p-4 md:p-8">
    <div class="max-w-3xl mx-auto bg-white rounded-xl shadow-lg p-6">
        <h1 class="text-2xl font-bold text-center text-indigo-700 mb-2">📝 Banyak Domain = 1 Tagihan</h1>
        <p class="text-center text-gray-600 mb-6">✅ Langsung ke Invoice</p>

        <form id="formInput" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Jumlah Domain (2 - 50)</label>
                <input type="number" id="jumlah" min="2" max="50" value="2" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Daftar Domain</label>
                <textarea id="daftar_domain" rows="5" placeholder="Contoh:&#10;duniakutecnok.biz.id&#10;sosialmed.biz.id" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required></textarea>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Email Akun</label>
                <input type="email" id="email" placeholder="contoh@gmail.com" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Password Akun (8-16 karakter, campur huruf & angka)</label>
                <input type="text" id="password" placeholder="Contoh: BagongPan123" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required>
            </div>

            <div id="captcha_area" class="p-3 border rounded-lg bg-gray-50 hidden">
                <p class="text-sm font-medium text-gray-700 mb-2">🔐 Verifikasi Keamanan</p>
                <div class="h-captcha" data-sitekey="{HCAPTCHA_SITEKEY}" data-callback="onCaptchaSuccess"></div>
                <input type="hidden" id="captcha_token" value="">
            </div>

            <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 rounded-lg transition">🚀 Proses Sekarang</button>
        </form>

        <div id="hasil" class="mt-8 hidden"></div>
    </div>

    <script>
        function onCaptchaSuccess(token) {{
            document.getElementById('captcha_token').value = token;
        }}

        const form = document.getElementById('formInput');
        const hasilDiv = document.getElementById('hasil');
        const captchaArea = document.getElementById('captcha_area');

        form.addEventListener('submit', async (e) => {{
            e.preventDefault();
            captchaArea.classList.add('hidden');

            hasilDiv.innerHTML = '<div class="text-center py-6 text-gray-600">⏳ Memproses...</div>';
            hasilDiv.classList.remove('hidden');

            const domains = document.getElementById('daftar_domain').value.split('\\n').map(d => d.trim()).filter(d => d);
            const jumlah = parseInt(document.getElementById('jumlah').value);
            const captcha = document.getElementById('captcha_token').value.trim();
            const pass = document.getElementById('password').value.trim();

            if (domains.length !== jumlah) {{
                hasilDiv.innerHTML = `<div class="text-red-600 p-4 rounded">❌ Jumlah domain tidak cocok!</div>`;
                return;
            }}

            if (pass.length < 8 || pass.length > 64) {{
                hasilDiv.innerHTML = `<div class="text-red-600 p-4 rounded">❌ Password harus 8-64 karakter!</div>`;
                return;
            }}

            const data = {{ domains, email: document.getElementById('email').value.trim(), password: pass, captcha_token: captcha }};

            try {{
                const res = await fetch('/proses', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify(data) }});
                const h = await res.json();

                if (h.status.includes("Perlu isi hCaptcha")) {{
                    hasilDiv.innerHTML = `<div class="text-yellow-700 bg-yellow-50 p-4 rounded">🔐 Selesaikan captcha di bawah, lalu klik proses lagi</div>`;
                    captchaArea.classList.remove('hidden');
                    return;
                }}

                let html = `<h2 class="text-xl font-semibold mb-4">📄 Hasil Proses</h2>`;
                html += `<div class="p-5 rounded border ${{h.status.includes('✅') ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}}">`;
                html += `<p><strong>Status:</strong> ${{h.status}}</p>`;
                html += `<p><strong>Jumlah Domain:</strong> ${{h.jumlah}}</p>`;
                html += `<p><strong>Daftar:</strong><br>• ${{h.daftar.join('<br>• ')}}</p>`;
                html += `<p class="text-lg font-bold mt-2">Total: ${{h.total_harga}}</p>`;
                if (h.link_invoice !== "-") {{
                    html += `<hr class="my-2">`;
                    html += `<p>📄 Link Invoice: <a href="${{h.link_invoice}}" target="_blank" class="text-blue-600 font-bold underline">${{h.link_invoice}}</a></p>`;
                    if (h.qris) html += `<p class="mt-2">QRIS:<br><img src="data:image/png;base64,${{h.qris}}" class="w-40 h-40 mt-1 border rounded"></p>`;
                }}
                html += `<p class="mt-2 text-sm"><strong>Keterangan:</strong><br>${{h.keterangan}}</p>`;
                html += `</div>`;

                hasilDiv.innerHTML = html;
            }} catch (err) {{
                hasilDiv.innerHTML = `<div class="text-red-600 p-4 rounded">❌ Kesalahan: ${{err}}</div>`;
            }}
        }});
    </script>
</body>
</html>
"""

@app.route('/')
def halaman_utama():
    return render_template_string(HALAMAN_HTML)

@app.route('/proses', methods=['POST'])
def jalankan_proses():
    data = request.get_json()
    return jsonify(proses_semua(data.get('domains', []), data.get('email', ''), data.get('password', ''), data.get('captcha_token', '')))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
def cek_domain_tersedia(sesi, token, domain):
    try:
        r = sesi.post(
            f"{BASE_URL}/cart.php?a=checkdomain",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{BASE_URL}/cart.php?a=add&domain=register"
            },
            data={"token": token, "domain": domain, "sld": domain.split(".")[0], "tld": "." + domain.split(".")[1], "action": "check"},
            timeout=TIMEOUT
        )
        return "available" in r.text.lower()
    except:
        return False

def tambah_ke_keranjang(sesi, token, domain):
    try:
        r = sesi.post(
            f"{BASE_URL}/cart.php",
            headers={"Referer": f"{BASE_URL}/cart.php?a=add&domain=register"},
            data={"a": "addDomain", "token": token, "domain": domain, "regperiod": 1, "dnsmanagement": 0, "emailforwarding": 0, "idprotection": 0},
            timeout=TIMEOUT
        )
        return "success" in r.text.lower() or "added" in r.text.lower()
    except:
        return False

def buat_qr_base64(data):
    try:
        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()
    except:
        return ""

# ==============================================
# 🚀 PROSES UTAMA
# ==============================================
def proses_semua(daftar_domain, email, password, captcha_token=""):
    sesi = requests.Session()
    sesi.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    })

    hasil = {
        "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "jumlah": len(daftar_domain),
        "daftar": daftar_domain,
        "email": email,
        "password": password,
        "total_harga": "Rp 0",
        "invoice_id": "-",
        "link_invoice": "-",
        "qris": "",
        "status": "",
        "keterangan": ""
    }

    token = get_token(sesi)
    if not token:
        hasil["status"] = "❌ Gagal dapat token akses"
        return hasil

    domain_berhasil = []
    for domain in daftar_domain:
        if cek_domain_tersedia(sesi, token, domain):
            if tambah_ke_keranjang(sesi, token, domain):
                domain_berhasil.append(domain)
                hasil["keterangan"] += f"✅ {domain} masuk keranjang | "
            else:
                hasil["keterangan"] += f"⚠️ {domain} gagal masuk | "
        else:
            hasil["keterangan"] += f"❌ {domain} tidak tersedia | "
        time.sleep(0.4)

    if not domain_berhasil:
        hasil["status"] = "❌ Tidak ada domain bisa diproses"
        return hasil

    hasil["total_harga"] = f"Rp {len(domain_berhasil):,}"

    # LANGSUNG KE ISI DATA & PEMBAYARAN
    try:
        sesi.post(f"{BASE_URL}/cart.php?a=confdomains", data={"token": token, "update": "true", "domainns1": "kiki.bunny.net", "domainns2": "coco.bunny.net"}, timeout=TIMEOUT)
        sesi.post(f"{BASE_URL}/cart.php?a=setstateandcountry", data={"token": token, "country": "ID", "state": "Jawa Barat"}, timeout=TIMEOUT)

        res = sesi.post(
            f"{BASE_URL}/cart.php?a=checkout",
            headers={"Origin": BASE_URL, "Referer": f"{BASE_URL}/cart.php?a=confdomains"},
            data={
                "token": token,
                "checkout": "true",
                "custtype": "new",
                "firstname": "Budi",
                "lastname": "Santoso",
                "email": email,
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
                "h-captcha-response": captcha_token.strip(),
                "paymentmethod": "duitkupop",
                "accepttos": "on"
            },
            timeout=30,
            allow_redirects=True
        )

        # AMBIL LINK INVOICE LANGSUNG
        if "viewinvoice.php" in res.text or "viewinvoice.php" in res.url:
            inv = re.search(r'viewinvoice\.php\?id=(\d+)', res.text + res.url)
            if inv:
                hasil["invoice_id"] = inv.group(1)
                hasil["link_invoice"] = f"{BASE_URL}/viewinvoice.php?id={inv.group(1)}"
                hasil["status"] = f"✅ BERHASIL | Invoice didapat"
                r_qr = sesi.get(hasil["link_invoice"], timeout=15)
                kode_qr = re.search(r'data-qr="([^"]+)"', r_qr.text)
                if kode_qr:
                    hasil["qris"] = buat_qr_base64(kode_qr.group(1))
            else:
                hasil["status"] = "ℹ️ Berhasil masuk, tapi tidak dapat nomor invoice"
        else:
            err = re.search(r'<div class="alert[^>]*>(.*?)</div>', res.text, re.S)
            pesan = (err.group(1) if err else "Perlu verifikasi")[:120]
            if "captcha" in pesan.lower():
                hasil["status"] = "🔐 Perlu isi hCaptcha di bawah"
            else:
                hasil["status"] = "ℹ️ Siap proses"
                hasil["keterangan"] += f" | Info: {pesan}"

    except Exception as e:
        hasil["status"] = "❌ Kesalahan proses akhir"
        hasil["keterangan"] += f" | Detail: {str(e)[:50]}"

    return hasil

# ==============================================
# 🎨 HALAMAN
# ==============================================
HALAMAN_HTML = f"""
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tools Beli Domain</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://js.hcaptcha.com/1/api.js" async defer></script>
</head>
<body class="bg-gray-100 min-h-screen p-4 md:p-8">
    <div class="max-w-3xl mx-auto bg-white rounded-xl shadow-lg p-6">
        <h1 class="text-2xl font-bold text-center text-indigo-700 mb-2">📝 Banyak Domain = 1 Tagihan</h1>
        <p class="text-center text-gray-600 mb-6">✅ Langsung ke data & invoice</p>

        <form id="formInput" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Jumlah Domain (2 - 50)</label>
                <input type="number" id="jumlah" min="2" max="50" value="2" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Daftar Domain</label>
                <textarea id="daftar_domain" rows="5" placeholder="Contoh:&#10;duniakutecnok.biz.id&#10;sosialmed.biz.id" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required></textarea>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Email Akun</label>
                <input type="email" id="email" placeholder="contoh@gmail.com" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Password Akun</label>
                <input type="text" id="password" placeholder="Masukkan password" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required>
            </div>

            <div id="captcha_area" class="p-3 border rounded-lg bg-gray-50 hidden">
                <p class="text-sm font-medium text-gray-700 mb-2">🔐 Verifikasi Keamanan</p>
                <div class="h-captcha" data-sitekey="{HCAPTCHA_SITEKEY}" data-callback="onCaptchaSuccess"></div>
                <input type="hidden" id="captcha_token" value="">
            </div>

            <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 rounded-lg transition">🚀 Proses Sekarang</button>
        </form>

        <div id="hasil" class="mt-8 hidden"></div>
    </div>

    <script>
        function onCaptchaSuccess(token) {{
            document.getElementById('captcha_token').value = token;
        }}

        const form = document.getElementById('formInput');
        const hasilDiv = document.getElementById('hasil');
        const captchaArea = document.getElementById('captcha_area');

        form.addEventListener('submit', async (e) => {{
            e.preventDefault();
            captchaArea.classList.add('hidden');

            hasilDiv.innerHTML = '<div class="text-center py-6 text-gray-600">⏳ Memproses...</div>';
            hasilDiv.classList.remove('hidden');

            const domains = document.getElementById('daftar_domain').value.split('\\n').map(d => d.trim()).filter(d => d);
            const jumlah = parseInt(document.getElementById('jumlah').value);
            const captcha = document.getElementById('captcha_token').value.trim();

            if (domains.length !== jumlah) {{
                hasilDiv.innerHTML = `<div class="text-red-600 p-4 rounded">❌ Jumlah domain tidak cocok!</div>`;
                return;
            }}

            const data = {{ domains, email: document.getElementById('email').value.trim(), password: document.getElementById('password').value.trim(), captcha_token: captcha }};

            try {{
                const res = await fetch('/proses', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify(data) }});
                const h = await res.json();

                if (h.status.includes("Perlu isi hCaptcha")) {{
                    hasilDiv.innerHTML = `<div class="text-yellow-700 bg-yellow-50 p-4 rounded">🔐 Selesaikan captcha di bawah, lalu klik proses lagi</div>`;
                    captchaArea.classList.remove('hidden');
                    return;
                }}

                let html = `<h2 class="text-xl font-semibold mb-4">📄 Hasil Proses</h2>`;
                html += `<div class="p-5 rounded border ${{h.status.includes('✅') ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}}">`;
                html += `<p><strong>Status:</strong> ${{h.status}}</p>`;
                html += `<p><strong>Jumlah Domain:</strong> ${{h.jumlah}}</p>`;
                html += `<p><strong>Daftar:</strong><br>• ${{h.daftar.join('<br>• ')}}</p>`;
                html += `<p class="text-lg font-bold mt-2">Total: ${{h.total_harga}}</p>`;
                if (h.link_invoice !== "-") {{
                    html += `<hr class="my-2">`;
                    html += `<p>📄 Link Invoice: <a href="${{h.link_invoice}}" target="_blank" class="text-blue-600 font-bold underline">${{h.link_invoice}}</a></p>`;
                    if (h.qris) html += `<p class="mt-2">QRIS:<br><img src="data:image/png;base64,${{h.qris}}" class="w-40 h-40 mt-1 border rounded"></p>`;
                }}
                html += `<p class="mt-2 text-sm"><strong>Keterangan:</strong><br>${{h.keterangan}}</p>`;
                html += `</div>`;

                hasilDiv.innerHTML = html;
            }} catch (err) {{
                hasilDiv.innerHTML = `<div class="text-red-600 p-4 rounded">❌ Kesalahan: ${{err}}</div>`;
            }}
        }});
    </script>
</body>
</html>
"""

@app.route('/')
def halaman_utama():
    return render_template_string(HALAMAN_HTML)

@app.route('/proses', methods=['POST'])
def jalankan_proses():
    data = request.get_json()
    return jsonify(proses_semua(data.get('domains', []), data.get('email', ''), data.get('password', ''), data.get('captcha_token', '')))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
            headers={"Referer": f"{BASE_URL}/cart.php?a=add&domain=register"},
            data={
                "a": "addDomain",
                "token": token,
                "domain": domain,
                "regperiod": 1,
                "dnsmanagement": 0,
                "emailforwarding": 0,
                "idprotection": 0
            },
            timeout=TIMEOUT
        )
        return "success" in r.text.lower() or "added" in r.text.lower()
    except:
        return False

def buat_qr_base64(data):
    try:
        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()
    except:
        return ""

# ==============================================
# 🚀 PROSES UTAMA
# ==============================================
def proses_semua(daftar_domain, email, password, captcha_token=""):
    sesi = requests.Session()
    sesi.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    })

    hasil = {
        "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "jumlah": len(daftar_domain),
        "daftar": daftar_domain,
        "email": email,
        "password": password,
        "total_harga": "Rp 0",
        "invoice_id": "-",
        "link_invoice": "-",
        "qris": "",
        "status": "",
        "keterangan": ""
    }

    if len(password) < 8 or len(password) > 64:
        hasil["status"] = "❌ Password harus 8–64 karakter"
        return hasil

    token = get_token(sesi)
    if not token:
        hasil["status"] = "❌ Gagal dapat token akses"
        return hasil

    domain_berhasil = []
    total = 0

    for domain in daftar_domain:
        if not domain:
            continue
        if cek_domain_tersedia(sesi, token, domain):
            if tambah_ke_keranjang(sesi, token, domain):
                domain_berhasil.append(domain)
                total += 1
                hasil["keterangan"] += f"✅ {domain} masuk keranjang | "
            else:
                hasil["keterangan"] += f"⚠️ {domain} gagal masuk keranjang | "
        else:
            hasil["keterangan"] += f"❌ {domain} tidak tersedia | "
        time.sleep(0.5)

    if not domain_berhasil:
        hasil["status"] = "❌ Tidak ada domain yang bisa diproses"
        return hasil

    hasil["total_harga"] = f"Rp {total * 1:,}"

    # Proses Checkout
    try:
        sesi.post(
            f"{BASE_URL}/cart.php?a=confdomains",
            data={"token": token, "update": "true", "domainns1": "kiki.bunny.net", "domainns2": "coco.bunny.net"},
            timeout=TIMEOUT
        )
        time.sleep(0.5)

        sesi.post(
            f"{BASE_URL}/cart.php?a=setstateandcountry",
            data={"token": token, "country": "ID", "state": "Jawa Barat"},
            timeout=TIMEOUT
        )
        time.sleep(0.5)

        res = sesi.post(
            f"{BASE_URL}/cart.php?a=checkout",
            headers={"Origin": BASE_URL, "Referer": f"{BASE_URL}/cart.php?a=confdomains"},
            data={
                "token": token,
                "checkout": "true",
                "custtype": "new",
                "firstname": "Budi",
                "lastname": "Santoso",
                "email": email,
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
                "h-captcha-response": captcha_token.strip(),
                "g-recaptcha-response": captcha_token.strip(),
                "paymentmethod": "duitkupop",
                "accepttos": "on"
            },
            timeout=30,
            allow_redirects=True
        )

        if "viewinvoice.php" in res.text or "viewinvoice.php" in res.url:
            inv = re.search(r'viewinvoice\.php\?id=(\d+)', res.text + res.url)
            if inv:
                hasil["invoice_id"] = inv.group(1)
                hasil["link_invoice"] = f"{BASE_URL}/viewinvoice.php?id={inv.group(1)}"
                hasil["status"] = f"✅ BERHASIL | {len(domain_berhasil)} domain"
                r_qr = sesi.get(hasil["link_invoice"], timeout=15)
                kode_qr = re.search(r'data-qr="([^"]+)"', r_qr.text)
                if kode_qr:
                    hasil["qris"] = buat_qr_base64(kode_qr.group(1))
            else:
                hasil["status"] = "⚠️ Berhasil masuk, tidak dapat nomor invoice"
        else:
            err = re.search(r'<div class="alert[^>]*>(.*?)</div>', res.text, re.S)
            pesan = (err.group(1) if err else "Masukkan jawaban hCaptcha")[:120]
            if "captcha" in pesan.lower():
                hasil["status"] = "🔐 Perlu verifikasi hCaptcha"
                hasil["keterangan"] += f" | Silakan selesaikan captcha di bawah"
            else:
                hasil["status"] = "ℹ️ Siap checkout"
                hasil["keterangan"] += f" | Pesan: {pesan}"

    except Exception as e:
        hasil["status"] = "❌ Kesalahan proses akhir"
        hasil["keterangan"] += f" | Detail: {str(e)[:50]}"

    return hasil

# ==============================================
# 🎨 HALAMAN WEB DENGAN CAPTCHA TERTANAM
# ==============================================
HALAMAN_HTML = f"""
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tools Beli Domain</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Muat skrip hCaptcha resmi -->
    <script src="https://js.hcaptcha.com/1/api.js" async defer></script>
</head>
<body class="bg-gray-100 min-h-screen p-4 md:p-8">
    <div class="max-w-3xl mx-auto bg-white rounded-xl shadow-lg p-6">
        <h1 class="text-2xl font-bold text-center text-indigo-700 mb-2">📝 Banyak Domain = 1 Tagihan</h1>
        <p class="text-center text-gray-600 mb-6">✅ Semua proses di sini saja, tidak perlu buka situs lain</p>

        <form id="formInput" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Jumlah Domain (2 - 50)</label>
                <input type="number" id="jumlah" min="2" max="50" value="2" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Daftar Domain</label>
                <textarea id="daftar_domain" rows="5" placeholder="Contoh:&#10;duniakutecnok.biz.id&#10;serbamulti.biz.id" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required></textarea>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Email Akun</label>
                <input type="email" id="email" placeholder="contoh@gmail.com" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Password Akun (8 - 64 karakter)</label>
                <input type="text" id="password" placeholder="Minimal 8 karakter" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required>
            </div>

            <!-- ✅ CAPTCHA MUNCUL DI SINI SESUAI WEB ASLI -->
            <div id="captcha_area" class="p-3 border rounded-lg bg-gray-50 hidden">
                <p class="text-sm font-medium text-gray-700 mb-2">🔐 Verifikasi Keamanan</p>
                <div class="h-captcha" data-sitekey="{HCAPTCHA_SITEKEY}" data-callback="onCaptchaSuccess"></div>
                <input type="hidden" id="captcha_token" value="">
            </div>

            <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 rounded-lg transition">🚀 Proses Sekarang</button>
        </form>

        <div id="hasil" class="mt-8 hidden"></div>
    </div>

    <script>
        let captchaSelesai = false;

        // Simpan jawaban captcha kalau berhasil
        function onCaptchaSuccess(token) {{
            document.getElementById('captcha_token').value = token;
            captchaSelesai = true;
        }}

        const form = document.getElementById('formInput');
        const hasilDiv = document.getElementById('hasil');
        const captchaArea = document.getElementById('captcha_area');

        form.addEventListener('submit', async (e) => {{
            e.preventDefault();
            captchaArea.classList.add('hidden');
            captchaSelesai = false;

            hasilDiv.innerHTML = '<div class="text-center py-6 text-gray-600">⏳ Memproses cek domain & keranjang...</div>';
            hasilDiv.classList.remove('hidden');

            const domains = document.getElementById('daftar_domain').value.split('\\n').map(d => d.trim()).filter(d => d);
            const jumlah = parseInt(document.getElementById('jumlah').value);
            const captcha = document.getElementById('captcha_token').value.trim();

            if (domains.length !== jumlah) {{
                hasilDiv.innerHTML = `<div class="text-red-600 p-4 rounded">❌ Jumlah domain tidak cocok!</div>`;
                return;
            }}

            const data = {{
                domains: domains,
                email: document.getElementById('email').value.trim(),
                password: document.getElementById('password').value.trim(),
                captcha_token: captcha
            }};

            try {{
                const res = await fetch('/proses', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(data)
                }});
                const h = await res.json();

                // Kalau perlu captcha, tampilkan di sini
                if (h.status.includes("verifikasi hCaptcha") || h.status.includes("Perlu verifikasi")) {{
                    hasilDiv.innerHTML = `<div class="text-yellow-700 bg-yellow-50 p-4 rounded">🔐 Silakan selesaikan verifikasi di bawah, lalu klik Proses lagi</div>`;
                    captchaArea.classList.remove('hidden');
                    return;
                }}

                let html = `<h2 class="text-xl font-semibold mb-4">📄 Hasil Proses</h2>`;
                html += `<div class="p-5 rounded border ${{h.status.includes('✅') ? 'bg-green-50 border-green-200' : h.status.includes('ℹ️') ? 'bg-yellow-50 border-yellow-200' : 'bg-red-50 border-red-200'}}">`;
                html += `<p><strong>Status:</strong> ${{h.status}}</p>`;
                html += `<p><strong>Jumlah Domain:</strong> ${{h.jumlah}}</p>`;
                html += `<p><strong>Daftar:</strong><br>• ${{h.daftar.join('<br>• ')}}</p>`;
                html += `<p class="text-lg font-bold mt-2">Total: ${{h.total_harga}}</p>`;

                if (h.invoice_id !== '-') {{
                    html += `<hr class="my-2">`;
                    html += `<p>Invoice: ${{h.invoice_id}}</p>`;
                    html += `<p>Link: <a href="${{h.link_invoice}}" target="_blank" class="text-blue-600 underline">${{h.link_invoice}}</a></p>`;
                    if (h.qris) html += `<p class="mt-2">QRIS:<br><img src="data:image/png;base64,${{h.qris}}" class="w-40 h-40 mt-1 border rounded"></p>`;
                }}

                html += `<p class="mt-2 text-sm"><strong>Keterangan:</strong><br>${{h.keterangan}}</p>`;
                html += `</div>`;

                hasilDiv.innerHTML = html;
            }} catch (err) {{
                hasilDiv.innerHTML = `<div class="text-red-600 p-4 rounded">❌ Kesalahan: ${{err}}</div>`;
            }}
        }});
    </script>
</body>
</html>
"""

@app.route('/')
def halaman_utama():
    return render_template_string(HALAMAN_HTML)

@app.route('/proses', methods=['POST'])
def jalankan_proses():
    data = request.get_json()
    daftar_domain = data.get('domains', [])
    email = data.get('email', '')
    password = data.get('password', '')
    captcha = data.get('captcha_token', '')
    return jsonify(proses_semua(daftar_domain, email, password, captcha))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
