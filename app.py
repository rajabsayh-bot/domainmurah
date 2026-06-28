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
TIMEOUT = 15
MAX_DOMAIN = 50  # Batas maksimal per akun

# 📋 Daftar User-Agent Acak
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 14; SM-S921B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Redmi Note 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
]

# ==============================================
# 🛠️ FUNGSI PENDUKUNG
# ==============================================
def get_token(sesi):
    try:
        r = sesi.get(f"{BASE_URL}/cart.php?a=add&domain=register", timeout=TIMEOUT)
        return re.search(r'name="token" value="([a-f0-9]{32,})"', r.text).group(1)
    except:
        return None

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

def proses_domain(domain, email, password):
    ua = random.choice(USER_AGENTS)
    sesi = requests.Session()
    sesi.headers.update({
        "User-Agent": ua,
        "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    })

    hasil = {
        "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "domain": domain,
        "email": email,
        "password": password,
        "harga": "-",
        "invoice": "-",
        "link": "-",
        "qris": "",
        "status": "",
        "info": "-"
    }

    token = get_token(sesi)
    if not token:
        hasil["status"] = "❌ Gagal dapat token"
        return hasil

    # Cek domain
    try:
        r_cek = sesi.post(
            f"{BASE_URL}/index.php?rp=/domain/check",
            headers={"Content-Type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest", "Referer": f"{BASE_URL}/cart.php?a=add&domain=register"},
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
        headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": f"{BASE_URL}/cart.php?a=add&domain=register"},
        data={"a": "addToCart", "domain": domain, "token": token, "years": 1, "idprotection": 0, "dnsmanagement": 0, "emailforwarding": 0, "whois": 0},
        timeout=TIMEOUT
    )
    time.sleep(0.4)

    # Set nameserver
    sesi.post(
        f"{BASE_URL}/cart.php?a=confdomains",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"token": token, "update": "true", "domainns1": "kiki.bunny.net", "domainns2": "coco.bunny.net"},
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

    # Checkout dengan data akun yang SAMA
    res = sesi.post(
        f"{BASE_URL}/cart.php?a=checkout",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": BASE_URL, "Referer": f"{BASE_URL}/cart.php?a=confdomains"},
        data={
            "token": token, "checkout": "true", "custtype": "new",
            "firstname": "Budi", "lastname": "Santoso",
            "email": email, "emailoptin": "0",
            "phonenumber": "628123456789", "address1": "Jl. Mawar No.1",
            "city": "Sukabumi", "state": "Jawa Barat", "postcode": "43111", "country": "ID",
            "password": password, "password2": password,
            "securityqid": "0", "securityans": "",
            "paymentmethod": "duitkupop", "accepttos": "on", "marketingoptin": "0"
        },
        timeout=20, allow_redirects=True
    )

    # Cek hasil
    if "viewinvoice.php" in res.text or "viewinvoice.php" in res.url:
        inv = re.search(r'viewinvoice\.php\?id=(\d+)', res.text + res.url)
        if inv:
            inv_id = inv.group(1)
            hasil["invoice"] = inv_id
            hasil["link"] = f"{BASE_URL}/viewinvoice.php?id={inv_id}"
            hasil["status"] = "✅ Berhasil"
            r_qr = sesi.get(hasil["link"], timeout=12)
            kode_qr = re.search(r'data-qr="([^"]+)"', r_qr.text)
            hasil["qris"] = buat_qr_base64(kode_qr.group(1)) if kode_qr else ""
    else:
        err = re.search(r'<div class="alert[^>]*>(.*?)</div>|<li>(.*?)</li>', res.text, re.S)
        hasil["info"] = (err.group(1) or err.group(2) or "Tidak ada pesan error")[:180].strip()
        hasil["status"] = "❌ Gagal"

    return hasil

# ==============================================
# 🎨 HALAMAN WEB
# ==============================================
HALAMAN_HTML = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tools Daftar Domain</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen p-4 md:p-8">
    <div class="max-w-3xl mx-auto bg-white rounded-xl shadow-lg p-6">
        <h1 class="text-2xl font-bold text-center text-indigo-700 mb-2">📝 Tools Daftar Domain</h1>
        <p class="text-center text-gray-600 mb-6">✅ 1 Email = Bisa beli 2 - 50 domain sekaligus</p>

        <!-- Form Input -->
        <form id="formInput" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Jumlah Domain (2 - 50)</label>
                <input type="number" id="jumlah" min="2" max="50" value="2" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required>
            </div>

            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Daftar Domain (1 baris = 1 domain)</label>
                <textarea id="daftar_domain" rows="6" placeholder="Contoh:&#10;domain1.biz.id&#10;domain2.biz.id&#10;domain3.biz.id" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required></textarea>
            </div>

            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Email Akun (Sama untuk semua domain)</label>
                <input type="email" id="email" placeholder="contoh@web-library.net" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required>
            </div>

            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Password Akun (Sama untuk semua)</label>
                <input type="text" id="password" placeholder="Minimal 6 karakter" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required>
            </div>

            <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 rounded-lg transition">🚀 Proses Semua Domain</button>
        </form>

        <!-- Hasil Proses -->
        <div id="hasil" class="mt-8 hidden"></div>
    </div>

    <script>
        const form = document.getElementById('formInput');
        const hasilDiv = document.getElementById('hasil');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            hasilDiv.innerHTML = '<div class="text-center py-6 text-gray-600">⏳ Sedang diproses, tunggu sebentar...</div>';
            hasilDiv.classList.remove('hidden');

            const domains = document.getElementById('daftar_domain').value.split('\\n').map(d => d.trim()).filter(d => d);
            const jumlah = parseInt(document.getElementById('jumlah').value);

            if (domains.length !== jumlah) {
                hasilDiv.innerHTML = `<div class="text-red-600 p-4 border rounded-lg">❌ Jumlah domain yang dimasukkan tidak sesuai dengan jumlah yang ditentukan!</div>`;
                return;
            }

            if (jumlah < 2 || jumlah > 50) {
                hasilDiv.innerHTML = `<div class="text-red-600 p-4 border rounded-lg">❌ Jumlah harus antara 2 sampai 50!</div>`;
                return;
            }

            const data = {
                domains: domains,
                email: document.getElementById('email').value.trim(),
                password: document.getElementById('password').value.trim()
            };

            try {
                const res = await fetch('/proses', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const hasil = await res.json();

                let html = `<h2 class="text-xl font-semibold text-green-700 mb-4">✅ Hasil Proses ${hasil.length} Domain</h2>`;
                hasil.forEach((item, i) => {
                    html += `
                    <div class="border rounded-lg p-4 mb-4 ${item.status.includes('✅') ? 'bg-green-50' : 'bg-red-50'}">
                        <h3 class="font-bold text-lg mb-2">No.${i+1} - ${item.domain}</h3>
                        <p><strong>Status:</strong> ${item.status}</p>
                        <p><strong>Harga:</strong> ${item.harga}</p>
                        <p><strong>Email:</strong> ${item.email}</p>
                        <p><strong>Password:</strong> ${item.password}</p>
                        ${item.invoice !== '-' ? `<p><strong>Invoice:</strong> ${item.invoice}</p>` : ''}
                        ${item.link !== '-' ? `<p><strong>Link:</strong> <a href="${item.link}" target="_blank" class="text-blue-600 underline">Buka Invoice</a></p>` : ''}
                        ${item.qris ? `<p class="mt-2"><strong>QRIS:</strong><br><img src="data:image/png;base64,${item.qris}" class="mt-1 w-32 h-32"></p>` : ''}
                        ${item.info !== '-' ? `<p class="mt-2 text-sm text-gray-700"><strong>Info:</strong> ${item.info}</p>` : ''}
                    </div>`;
                });

                hasilDiv.innerHTML = html;
            } catch (err) {
                hasilDiv.innerHTML = `<div class="text-red-600 p-4 border rounded-lg">❌ Terjadi kesalahan: ${err}</div>`;
            }
        });
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

    hasil_akhir = []
    for domain in daftar_domain:
        hasil_akhir.append(proses_domain(domain, email, password))
        time.sleep(1)  # Jeda aman antar domain
    return jsonify(hasil_akhir)

if __name__ == '__main__':
    app.run(debug=True)
