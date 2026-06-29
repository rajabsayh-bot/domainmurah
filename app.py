from flask import Flask, render_template_string, request, jsonify
import re
import time
import random
import http.client
import urllib.parse
from datetime import datetime

app = Flask(__name__)

BASE_URL = "hosting.arxan.app"
HCAPTCHA_SITEKEY = "a5f74b19-9e6a-4ff0-a1b3-8d1201791129"
TIMEOUT = 25

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; M2006C3MG Build/QP1A.190711.020) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.7827.91 Mobile Safari/537.36"
]

def http_request(method, path, data=None, headers=None):
    try:
        conn = http.client.HTTPSConnection(BASE_URL, timeout=TIMEOUT)
        if not headers:
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
                "Content-Type": "application/x-www-form-urlencoded"
            }
        body = urllib.parse.urlencode(data) if data else None
        conn.request(method, path, body=body, headers=headers)
        res = conn.getresponse()
        resp_text = res.read().decode("utf-8", errors="ignore")
        conn.close()
        return resp_text, res.status
    except Exception as e:
        return "", 0

def get_token():
    text, _ = http_request("GET", "/cart.php?a=add&domain=register")
    match = re.search(r'name="token" value="([a-f0-9]{32,})"', text)
    return match.group(1) if match else None

def cek_domain(token, domain):
    data = {
        "token": token,
        "domain": domain,
        "sld": domain.split(".")[0],
        "tld": "." + domain.split(".")[1],
        "action": "check"
    }
    text, _ = http_request("POST", "/cart.php?a=checkdomain", data=data, headers={"X-Requested-With": "XMLHttpRequest"})
    return "available" in text.lower()

def tambah_keranjang(token, domain):
    data = {
        "a": "addDomain",
        "token": token,
        "domain": domain,
        "regperiod": 1,
        "dnsmanagement": 0,
        "emailforwarding": 0,
        "idprotection": 0
    }
    text, _ = http_request("POST", "/cart.php", data=data)
    return "success" in text.lower() or "added" in text.lower()

def proses_semua(daftar_domain, email, password, captcha_token=""):
    hasil = {
        "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "jumlah": len(daftar_domain),
        "daftar": daftar_domain,
        "email": email,
        "password": password,
        "total_harga": "Rp 0",
        "invoice_id": "-",
        "link_invoice": "-",
        "status": "",
        "keterangan": ""
    }

    if len(password) < 8 or len(password) > 64:
        hasil["status"] = "❌ Password harus 8-64 karakter"
        return hasil

    token = get_token()
    if not token:
        hasil["status"] = "❌ Gagal dapat token akses"
        return hasil

    domain_berhasil = []
    for domain in daftar_domain:
        if cek_domain(token, domain):
            if tambah_keranjang(token, domain):
                domain_berhasil.append(domain)
                hasil["keterangan"] += f"✅ {domain} masuk keranjang | "
            else:
                hasil["keterangan"] += f"⚠️ {domain} gagal masuk | "
        else:
            hasil["keterangan"] += f"❌ {domain} tidak tersedia | "
        time.sleep(0.3)

    if not domain_berhasil:
        hasil["status"] = "❌ Tidak ada domain bisa diproses"
        return hasil

    hasil["total_harga"] = f"Rp {len(domain_berhasil):,}"

    http_request("POST", "/cart.php?a=confdomains", data={
        "token": token, "update": "true", "domainns1": "kiki.bunny.net", "domainns2": "coco.bunny.net"
    })
    time.sleep(0.4)

    http_request("POST", "/cart.php?a=setstateandcountry", data={
        "token": token, "country": "ID", "state": "Jawa Barat"
    })
    time.sleep(0.4)

    data_checkout = {
        "token": token,
        "checkout": "1",
        "custtype": "new",
        "firstname": "Budi",
        "lastname": "Santoso",
        "email": email.strip(),
        "phonenumber": "628123456789",
        "address1": "Jl. Mawar No.1",
        "city": "Sukabumi",
        "state": "Jawa Barat",
        "postcode": "43111",
        "country": "ID",
        "password": password.strip(),
        "password2": password.strip(),
        "securityqid": "0",
        "securityans": "",
        "h-captcha-response": captcha_token.strip(),
        "paymentmethod": "duitkupop",
        "accepttos": "1"
    }

    res_text, status = http_request("POST", "/cart.php?a=checkout", data=data_checkout, headers={"Referer": f"https://{BASE_URL}/cart.php?a=confdomains"})

    if "viewinvoice.php" in res_text:
        inv = re.search(r'viewinvoice\.php\?id=(\d+)', res_text)
        if inv:
            hasil["invoice_id"] = inv.group(1)
            hasil["link_invoice"] = f"https://{BASE_URL}/viewinvoice.php?id={inv.group(1)}"
            hasil["status"] = f"✅ BERHASIL! Invoice #{inv.group(1)} didapat"
        else:
            hasil["status"] = "⚠️ Berhasil masuk, tidak dapat nomor invoice"
    else:
        pesan = re.search(r'<div class="alert[^>]*>(.*?)</div>', res_text, re.S)
        pesan = pesan.group(1).strip()[:150] if pesan else "Belum selesai"
        if "captcha" in pesan.lower():
            hasil["status"] = "🔐 Perlu isi hCaptcha di bawah"
        elif "password" in pesan.lower():
            hasil["status"] = "❌ Password ditolak"
            hasil["keterangan"] += f" | Saran: pakai huruf + angka saja"
        else:
            hasil["status"] = "ℹ️ Siap checkout"
            hasil["keterangan"] += f" | Pesan: {pesan}"

    return hasil

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
<body class="bg-gray-100 min-h-screen p-4">
    <div class="max-w-xl mx-auto bg-white rounded-xl shadow p-5">
        <h1 class="text-xl font-bold text-center text-indigo-700 mb-4">🛒 Beli Domain Sekaligus</h1>

        <form id="formInput" class="space-y-4">
            <div>
                <label class="text-sm font-medium">Email Akun</label>
                <input type="email" id="email" class="w-full mt-1 p-2 border rounded" value="rokoteapan@gmail.com" required>
            </div>
            <div>
                <label class="text-sm font-medium">Password Akun (8-64 karakter)</label>
                <input type="text" id="password" class="w-full mt-1 p-2 border rounded" placeholder="Contoh: BagongPan123" required>
                <p class="text-xs text-gray-500 mt-1">Hindari simbol @ ganda biar aman</p>
            </div>
            <div>
                <label class="text-sm font-medium">Daftar Domain</label>
                <textarea id="domains" rows="4" class="w-full mt-1 p-2 border rounded" placeholder="duniakutecnok.biz.id&#10;sosialmed.biz.id" required></textarea>
            </div>

            <div id="captcha_box" class="hidden p-3 border rounded bg-gray-50">
                <p class="text-sm font-medium mb-2">🔐 Verifikasi Keamanan</p>
                <div class="h-captcha" data-sitekey="{HCAPTCHA_SITEKEY}" data-callback="setCaptcha"></div>
                <input type="hidden" id="captcha" value="">
            </div>

            <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2.5 rounded">🚀 Proses Sekarang</button>
        </form>

        <div id="hasil" class="mt-5 hidden p-4 rounded border"></div>
    </div>

    <script>
        function setCaptcha(token) {{
            document.getElementById('captcha').value = token;
        }}

        const form = document.getElementById('formInput');
        const hasil = document.getElementById('hasil');
        const captchaBox = document.getElementById('captcha_box');

        form.addEventListener('submit', async (e) => {{
            e.preventDefault();
            captchaBox.classList.add('hidden');
            hasil.classList.remove('hidden');
            hasil.className = 'mt-5 p-4 rounded border bg-gray-50';
            hasil.innerHTML = '<p class="text-center">⏳ Memproses...</p>';

            const listDomain = document.getElementById('domains').value.split('\\n').map(d => d.trim()).filter(d => d);
            const email = document.getElementById('email').value.trim();
            const pass = document.getElementById('password').value.trim();
            const captcha = document.getElementById('captcha').value.trim();

            try {{
                const res = await fetch('/proses', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ domains: listDomain, email: email, password: pass, captcha_token: captcha }})
                }});
                const data = await res.json();

                if (data.status.includes("Perlu isi hCaptcha")) {{
                    hasil.className = 'mt-5 p-4 rounded border bg-yellow-50';
                    hasil.innerHTML = '<p class="text-yellow-800">🔐 Selesaikan verifikasi di bawah, lalu klik proses lagi</p>';
                    captchaBox.classList.remove('hidden');
                    return;
                }}

                let warna = data.status.includes("✅") ? "bg-green-50 border-green-200" : "bg-yellow-50 border-yellow-200";
                let html = `<p><strong>Status:</strong> ${{data.status}}</p>
                <p><strong>Jumlah Domain:</strong> ${{data.jumlah}}</p>
                <p><strong>Daftar:</strong><br>• ${{data.daftar.join('<br>• ')}}</p>
                <p class="font-bold mt-2">Total: ${{data.total_harga}}</p>`;

                if (data.link_invoice !== "-") {{
                    html += `<hr class="my-2">
                    <p>📄 Link Invoice: <a href="${{data.link_invoice}}" target="_blank" class="text-blue-600 font-bold underline">${{data.link_invoice}}</a></p>`;
                }}

                html += `<p class="mt-2 text-sm"><strong>Keterangan:</strong><br>${{data.keterangan}}</p>`;

                hasil.className = `mt-5 p-4 rounded border ${{warna}}`;
                hasil.innerHTML = html;

            }} catch (err) {{
                hasil.className = 'mt-5 p-4 rounded border bg-red-50';
                hasil.innerHTML = `<p class="text-red-700">❌ Kesalahan: ${{err}}</p>`;
            }}
        }});
    </script>
</body>
</html>
"""

@app.route('/')
def halaman():
    return render_template_string(HALAMAN_HTML)

@app.route('/proses', methods=['POST'])
def proses():
    data = request.get_json()
    return jsonify(proses_semua(data.get('domains', []), data.get('email', ''), data.get('password', ''), data.get('captcha_token', '')))

# Khusus Vercel
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
else:
    app = app
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
        time.sleep(0.3)

    if not domain_berhasil:
        hasil["status"] = "❌ Tidak ada domain bisa diproses"
        return hasil

    hasil["total_harga"] = f"Rp {len(domain_berhasil):,}"

    # LANGSUNG CHECKOUT DENGAN FORMAT DATA YANG BENAR
    try:
        sesi.post(f"{BASE_URL}/cart.php?a=confdomains", data={"token": token, "update": "true", "domainns1": "kiki.bunny.net", "domainns2": "coco.bunny.net"}, timeout=TIMEOUT)
        time.sleep(0.4)

        sesi.post(f"{BASE_URL}/cart.php?a=setstateandcountry", data={"token": token, "country": "ID", "state": "Jawa Barat"}, timeout=TIMEOUT)
        time.sleep(0.4)

        # ✅ Data dikirim rapi, tanpa karakter yang bikin bingung
        data_checkout = {
            "token": token,
            "checkout": "1",
            "custtype": "new",
            "firstname": "Budi",
            "lastname": "Santoso",
            "email": email.strip(),
            "phonenumber": "628123456789",
            "address1": "Jl. Mawar No.1",
            "city": "Sukabumi",
            "state": "Jawa Barat",
            "postcode": "43111",
            "country": "ID",
            "password": password.strip(),
            "password2": password.strip(),
            "securityqid": "0",
            "securityans": "",
            "h-captcha-response": captcha_token.strip(),
            "paymentmethod": "duitkupop",
            "accepttos": "1"
        }

        res = sesi.post(
            f"{BASE_URL}/cart.php?a=checkout",
            headers={"Referer": f"{BASE_URL}/cart.php?a=confdomains", "Origin": BASE_URL},
            data=data_checkout,
            timeout=30,
            allow_redirects=True
        )

        # Ambil link invoice
        if "viewinvoice.php" in res.text or "viewinvoice.php" in res.url:
            inv = re.search(r'viewinvoice\.php\?id=(\d+)', res.text + res.url)
            if inv:
                hasil["invoice_id"] = inv.group(1)
                hasil["link_invoice"] = f"{BASE_URL}/viewinvoice.php?id={inv.group(1)}"
                hasil["status"] = f"✅ BERHASIL! Invoice #{inv.group(1)} didapat"
                r_qr = sesi.get(hasil["link_invoice"], timeout=15)
                kode_qr = re.search(r'data-qr="([^"]+)"', r_qr.text)
                if kode_qr:
                    hasil["qris"] = buat_qr_base64(kode_qr.group(1))
            else:
                hasil["status"] = "⚠️ Berhasil masuk, tidak dapat nomor invoice"
        else:
            pesan = re.search(r'<div class="alert[^>]*>(.*?)</div>', res.text, re.S)
            pesan = pesan.group(1).strip()[:150] if pesan else "Belum selesai"

            if "captcha" in pesan.lower():
                hasil["status"] = "🔐 Perlu isi hCaptcha di bawah"
            elif "password" in pesan.lower():
                hasil["status"] = "❌ Password ditolak"
                hasil["keterangan"] += f" | Saran: gunakan campuran huruf & angka saja dulu, hindari @ ganda"
            else:
                hasil["status"] = "ℹ️ Siap checkout"
                hasil["keterangan"] += f" | Pesan: {pesan}"

    except Exception as e:
        hasil["status"] = "❌ Kesalahan proses"
        hasil["keterangan"] += f" | {str(e)[:50]}"

    return hasil

# ==============================================
# 🎨 HALAMAN WEB
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
<body class="bg-gray-100 min-h-screen p-4">
    <div class="max-w-xl mx-auto bg-white rounded-xl shadow p-5">
        <h1 class="text-xl font-bold text-center text-indigo-700 mb-4">🛒 Beli Domain Sekaligus</h1>

        <form id="formInput" class="space-y-4">
            <div>
                <label class="text-sm font-medium">Email Akun</label>
                <input type="email" id="email" class="w-full mt-1 p-2 border rounded" value="rokoteapan@gmail.com" required>
            </div>
            <div>
                <label class="text-sm font-medium">Password Akun (8-64 karakter)</label>
                <input type="text" id="password" class="w-full mt-1 p-2 border rounded" placeholder="Contoh: BagongPan123" required>
                <p class="text-xs text-gray-500 mt-1">Sebaiknya pakai huruf + angka saja dulu</p>
            </div>
            <div>
                <label class="text-sm font-medium">Daftar Domain</label>
                <textarea id="domains" rows="4" class="w-full mt-1 p-2 border rounded" placeholder="duniakutecnok.biz.id&#10;sosialmed.biz.id" required></textarea>
            </div>

            <div id="captcha_box" class="hidden p-3 border rounded bg-gray-50">
                <p class="text-sm font-medium mb-2">🔐 Verifikasi Keamanan</p>
                <div class="h-captcha" data-sitekey="{HCAPTCHA_SITEKEY}" data-callback="setCaptcha"></div>
                <input type="hidden" id="captcha" value="">
            </div>

            <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2.5 rounded">🚀 Proses Sekarang</button>
        </form>

        <div id="hasil" class="mt-5 hidden p-4 rounded border"></div>
    </div>

    <script>
        function setCaptcha(token) {{
            document.getElementById('captcha').value = token;
        }}

        const form = document.getElementById('formInput');
        const hasil = document.getElementById('hasil');
        const captchaBox = document.getElementById('captcha_box');

        form.addEventListener('submit', async (e) => {{
            e.preventDefault();
            captchaBox.classList.add('hidden');
            hasil.classList.remove('hidden');
            hasil.className = 'mt-5 p-4 rounded border bg-gray-50';
            hasil.innerHTML = '<p class="text-center">⏳ Memproses...</p>';

            const listDomain = document.getElementById('domains').value.split('\\n').map(d => d.trim()).filter(d => d);
            const email = document.getElementById('email').value.trim();
            const pass = document.getElementById('password').value.trim();
            const captcha = document.getElementById('captcha').value.trim();

            if (pass.length < 8 || pass.length > 64) {{
                hasil.className = 'mt-5 p-4 rounded border bg-red-50';
                hasil.innerHTML = '<p class="text-red-700">❌ Password harus 8-64 karakter!</p>';
                return;
            }}

            try {{
                const res = await fetch('/proses', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ domains: listDomain, email: email, password: pass, captcha_token: captcha }})
                }});
                const data = await res.json();

                if (data.status.includes("Perlu isi hCaptcha")) {{
                    hasil.className = 'mt-5 p-4 rounded border bg-yellow-50';
                    hasil.innerHTML = '<p class="text-yellow-800">🔐 Selesaikan verifikasi di bawah, lalu klik proses lagi</p>';
                    captchaBox.classList.remove('hidden');
                    return;
                }}

                let warna = data.status.includes("✅") ? "bg-green-50 border-green-200" : "bg-yellow-50 border-yellow-200";
                let html = `<p><strong>Status:</strong> ${data.status}</p>
                <p><strong>Jumlah Domain:</strong> ${data.jumlah}</p>
                <p><strong>Daftar:</strong><br>• ${data.daftar.join('<br>• ')}</p>
                <p class="font-bold mt-2">Total: ${data.total_harga}</p>`;

                if (data.link_invoice !== "-") {{
                    html += `<hr class="my-2">
                    <p>📄 Link Invoice: <a href="${data.link_invoice}" target="_blank" class="text-blue-600 font-bold underline">${data.link_invoice}</a></p>`;
                    if (data.qris) html += `<p class="mt-2">QRIS:<br><img src="data:image/png;base64,${data.qris}" class="w-36 h-36 mt-1 border rounded"></p>`;
                }}

                html += `<p class="mt-2 text-sm"><strong>Keterangan:</strong><br>${data.keterangan}</p>`;

                hasil.className = `mt-5 p-4 rounded border ${warna}`;
                hasil.innerHTML = html;

            }} catch (err) {{
                hasil.className = 'mt-5 p-4 rounded border bg-red-50';
                hasil.innerHTML = `<p class="text-red-700">❌ Kesalahan: ${err}</p>`;
            }}
        }});
    </script>
</body>
</html>
"""

@app.route('/')
def halaman():
    return render_template_string(HALAMAN_HTML)

@app.route('/proses', methods=['POST'])
def proses():
    data = request.get_json()
    return jsonify(proses_semua(data.get('domains', []), data.get('email', ''), data.get('password', ''), data.get('captcha_token', '')))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
