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
TIMEOUT = 30
MAX_DOMAIN = 50

# Kunci hCaptcha situs ini
HCAPTCHA_SITEKEY = "a5f74b19-9e6a-4ff0-a1b3-8d1201791129"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; M2006C3MG Build/QP1A.190711.020) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.7827.91 Mobile Safari/537.36"
]

# ==============================================
# 🛠️ FUNGSI
# ==============================================
def bypass_hcaptcha_manual(sesi):
    """Cara tangani hCaptcha tanpa solver luar, cukup ambil token dari halaman"""
    try:
        # Buka halaman utama keranjang
        r = sesi.get(f"{BASE_URL}/cart.php?a=add&domain=register", timeout=TIMEOUT)
        
        # Cek apakah ada hCaptcha
        if "h-captcha" in r.text.lower():
            print("ℹ️ Ada hCaptcha, ambil data...")
            
            # Kalau nanti mau pakai solver tetap, ini tempatnya
            # Tapi sekarang kita pakai nilai default buat tes dulu
            captcha_token = "PENANGANAN_MANUAL_ATAU_SOLVER"
            return captcha_token
        
        return ""
    except Exception as e:
        print(f"❌ Kesalahan baca halaman: {e}")
        return ""

def get_token(sesi):
    try:
        r = sesi.get(f"{BASE_URL}/cart.php?a=add&domain=register", timeout=TIMEOUT)
        match = re.search(r'name="token" value="([a-f0-9]{32,})"', r.text)
        return match.group(1) if match else None
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

# ==============================================
# 🚀 PROSES UTAMA
# ==============================================
def proses_semua(daftar_domain, email, password):
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

    # ⚠️ SEMENTARA: Lewati pengecekan captcha dulu untuk tes jalur
    captcha_token = ""

    # Ambil token akses
    token = get_token(sesi)
    if not token:
        hasil["status"] = "❌ Gagal dapat token akses"
        return hasil

    total = 0
    domain_berhasil = []

    # 🔹 Masukkan domain ke keranjang
    for domain in daftar_domain:
        try:
            cek = sesi.post(
                f"{BASE_URL}/index.php?rp=/domain/check",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": f"{BASE_URL}/cart.php?a=add&domain=register"
                },
                data={"token": token, "a": "checkDomain", "domain": domain, "type": "domain"},
                timeout=TIMEOUT
            )

            if "available" not in cek.text.lower():
                hasil["keterangan"] += f"❌ {domain} tidak tersedia | "
                continue

            hrg = re.search(r'Rp\s*(\d+)', cek.text)
            if hrg:
                total += int(hrg.group(1))

            sesi.post(
                f"{BASE_URL}/cart.php",
                headers={"Referer": f"{BASE_URL}/cart.php?a=add&domain=register"},
                data={
                    "a": "addToCart", "domain": domain, "token": token,
                    "years": 1, "idprotection": 0, "dnsmanagement": 0,
                    "emailforwarding": 0, "whois": 0
                },
                timeout=TIMEOUT
            )

            domain_berhasil.append(domain)
            hasil["keterangan"] += f"✅ {domain} masuk keranjang | "
            time.sleep(0.7)

        except Exception as e:
            hasil["keterangan"] += f"⚠️ Gagal {domain}: {str(e)[:20]} | "
            continue

    if not domain_berhasil:
        hasil["status"] = "❌ Tidak ada domain yang bisa diproses"
        return hasil

    hasil["total_harga"] = f"Rp {total:,}"

    # 🔹 Proses Checkout
    try:
        sesi.post(
            f"{BASE_URL}/cart.php?a=confdomains",
            data={"token": token, "update": "true", "domainns1": "kiki.bunny.net", "domainns2": "coco.bunny.net"},
            timeout=TIMEOUT
        )
        time.sleep(0.5)

        sesi.post(
            f"{BASE_URL}/cart.php?a=setstateandcountry&e=false",
            data={"token": token, "country": "ID", "state": "Jawa Barat", "ajax": 1},
            timeout=TIMEOUT
        )
        time.sleep(0.5)

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
                "h-captcha-response": captcha_token,
                "paymentmethod": "duitkupop",
                "accepttos": "on",
                "marketingoptin": "0"
            },
            timeout=30,
            allow_redirects=True
        )

        if "viewinvoice.php" in res.text or "viewinvoice.php" in res.url:
            inv = re.search(r'viewinvoice\.php\?id=(\d+)', res.text + res.url)
            if inv:
                hasil["invoice_id"] = inv.group(1)
                hasil["link_invoice"] = f"{BASE_URL}/viewinvoice.php?id={inv.group(1)}"
                hasil["status"] = f"✅ PESANAN BERHASIL | {len(domain_berhasil)} domain"

                r_qr = sesi.get(hasil["link_invoice"], timeout=15)
                kode_qr = re.search(r'data-qr="([^"]+)"', r_qr.text)
                if kode_qr:
                    hasil["qris"] = buat_qr_base64(kode_qr.group(1))
            else:
                hasil["status"] = "❌ Gagal dapat nomor invoice"
        else:
            err = re.search(r'<div class="alert[^>]*>(.*?)</div>|<li>(.*?)</li>', res.text, re.S)
            pesan = (err.group(1) or err.group(2) or "Tidak diketahui")[:150]
            hasil["status"] = f"❌ Gagal checkout"
            hasil["keterangan"] += f" | Pesan: {pesan}"

    except Exception as e:
        hasil["status"] = "❌ Kesalahan proses akhir"
        hasil["keterangan"] += f" | Detail: {str(e)[:50]}"

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
    <title>Tools Beli Domain</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen p-4 md:p-8">
    <div class="max-w-3xl mx-auto bg-white rounded-xl shadow-lg p-6">
        <h1 class="text-2xl font-bold text-center text-indigo-700 mb-2">📝 Banyak Domain = 1 Tagihan</h1>
        <p class="text-center text-gray-600 mb-6">✅ Jalur utama tanpa solver luar</p>

        <form id="formInput" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Jumlah Domain (2 - 50)</label>
                <input type="number" id="jumlah" min="2" max="50" value="2" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Daftar Domain</label>
                <textarea id="daftar_domain" rows="6" placeholder="Contoh:&#10;duniakutecnok.biz.id&#10;serbamulti.biz.id" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required></textarea>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Email Akun</label>
                <input type="email" id="email" placeholder="contoh@mail.com" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Password Akun</label>
                <input type="text" id="password" placeholder="Minimal 6 karakter" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required>
            </div>
            <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 rounded-lg transition">🚀 Proses Sekarang</button>
        </form>
        <div id="hasil" class="mt-8 hidden"></div>
    </div>
    <script>
        const form = document.getElementById('formInput');
        const hasilDiv = document.getElementById('hasil');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            hasilDiv.innerHTML = '<div class="text-center py-6 text-gray-600">⏳ Memproses... Mohon tunggu!</div>';
            hasilDiv.classList.remove('hidden');
            const domains = document.getElementById('daftar_domain').value.split('\\n').map(d => d.trim()).filter(d => d);
            const jumlah = parseInt(document.getElementById('jumlah').value);
            if (domains.length !== jumlah) {
                hasilDiv.innerHTML = `<div class="text-red-600 p-4 rounded">❌ Jumlah domain tidak cocok!</div>`;
                return;
            }
            const data = { domains, email: document.getElementById('email').value.trim(), password: document.getElementById('password').value.trim() };
            try {
                const res = await fetch('/proses', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
                const h = await res.json();
                let html = `<h2 class="text-xl font-semibold mb-4">📄 Hasil Proses</h2>`;
                html += `<div class="p-5 rounded border ${h.status.includes('✅') ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}">`;
                html += `<p><strong>Status:</strong> ${h.status}</p>`;
                html += `<p><strong>Jumlah Domain:</strong> ${h.jumlah}</p>`;
                html += `<p><strong>Daftar:</strong><br>• ${h.daftar.join('<br>• ')}</p>`;
                html += `<p class="text-lg font-bold mt-2">Total: ${h.total_harga}</p>`;
                if (h.invoice_id !== '-') {
                    html += `<hr class="my-2">`;
                    html += `<p>Invoice: ${h.invoice_id}</p>`;
                    html += `<p>Link: <a href="${h.link_invoice}" target="_blank" class="text-blue-600 underline">${h.link_invoice}</a></p>`;
                    if (h.qris) html += `<p class="mt-2">QRIS:<br><img src="data:image/png;base64,${h.qris}" class="w-40 h-40 mt-1 border rounded"></p>`;
                }
                html += `<p class="mt-2 text-sm"><strong>Keterangan:</strong><br>${h.keterangan}</p>`;
                html += `</div>`;
                hasilDiv.innerHTML = html;
            } catch (err) {
                hasilDiv.innerHTML = `<div class="text-red-600 p-4 rounded">❌ Kesalahan: ${err}</div>`;
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
    return jsonify(proses_semua(daftar_domain, email, password))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
