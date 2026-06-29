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
MAX_DOMAIN = 50

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

# ==============================================
# 🚀 ALUR SESUAI PERMINTAAN
# ==============================================
def proses_semua(daftar_domain, email, password):
    ua = random.choice(USER_AGENTS)
    sesi = requests.Session()
    sesi.headers.update({
        "User-Agent": ua,
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

    # Ambil token awal
    token = get_token(sesi)
    if not token:
        hasil["status"] = "❌ Gagal dapat token akses"
        return hasil

    total = 0
    domain_berhasil = []

    # 🔹 Langkah 1: Masukkan semua domain ke keranjang
    for domain in daftar_domain:
        try:
            # Cek ketersediaan
            cek = sesi.post(
                f"{BASE_URL}/index.php?rp=/domain/check",
                headers={"Content-Type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest", "Referer": f"{BASE_URL}/cart.php?a=add&domain=register"},
                data={"token": token, "a": "checkDomain", "domain": domain, "type": "domain"},
                timeout=TIMEOUT
            )

            if "available" not in cek.text.lower():
                hasil["keterangan"] += f"❌ {domain} tidak tersedia | "
                continue

            # Ambil harga
            hrg = re.search(r'Rp\s*(\d+)', cek.text)
            if hrg:
                total += int(hrg.group(1))

            # Masuk ke keranjang
            sesi.post(
                f"{BASE_URL}/cart.php",
                headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": f"{BASE_URL}/cart.php?a=add&domain=register"},
                data={"a": "addToCart", "domain": domain, "token": token, "years": 1, "idprotection": 0, "dnsmanagement": 0, "emailforwarding": 0, "whois": 0},
                timeout=TIMEOUT
            )

            domain_berhasil.append(domain)
            hasil["keterangan"] += f"✅ {domain} masuk keranjang | "
            time.sleep(0.6)

        except Exception as e:
            hasil["keterangan"] += f"⚠️ Gagal {domain}: {str(e)[:20]} | "
            continue

    if not domain_berhasil:
        hasil["status"] = "❌ Tidak ada domain yang bisa diproses"
        return hasil

    hasil["total_harga"] = f"Rp {total:,}"

    # 🔹 Langkah 2: Setelah semua masuk, LANGSUNG buat pesanan
    try:
        # Atur nameserver
        sesi.post(
            f"{BASE_URL}/cart.php?a=confdomains",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"token": token, "update": "true", "domainns1": "kiki.bunny.net", "domainns2": "coco.bunny.net"},
            timeout=TIMEOUT
        )
        time.sleep(0.5)

        # Atur wilayah
        sesi.post(
            f"{BASE_URL}/cart.php?a=setstateandcountry&e=false",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"token": token, "country": "ID", "state": "Jawa Barat", "ajax": 1},
            timeout=TIMEOUT
        )
        time.sleep(0.5)

        # 🔹 PROSES ORDER / BUAT TAGIHAN
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
            timeout=25,
            allow_redirects=True
        )

        # 🔹 Ambil link invoice & QRIS
        if "viewinvoice.php" in res.text or "viewinvoice.php" in res.url:
            inv = re.search(r'viewinvoice\.php\?id=(\d+)', res.text + res.url)
            if inv:
                hasil["invoice_id"] = inv.group(1)
                hasil["link_invoice"] = f"{BASE_URL}/viewinvoice.php?id={inv.group(1)}"
                hasil["status"] = f"✅ PESANAN BERHASIL DIBUAT | {len(domain_berhasil)} domain"
                hasil["keterangan"] += "\n📌 Pembayaran dilakukan MANUAL lewat link/QRIS di bawah"

                # Ambil kode QRIS
                r_qr = sesi.get(hasil["link_invoice"], timeout=12)
                kode_qr = re.search(r'data-qr="([^"]+)"', r_qr.text)
                if kode_qr:
                    hasil["qris"] = buat_qr_base64(kode_qr.group(1))
            else:
                hasil["status"] = "❌ Gagal dapat nomor invoice"
        else:
            err = re.search(r'<div class="alert[^>]*>(.*?)</div>|<li>(.*?)</li>', res.text, re.S)
            pesan = (err.group(1) or err.group(2) or "Tidak diketahui")[:150]
            hasil["status"] = f"❌ Gagal buat pesanan"
            hasil["keterangan"] += f" | Error: {pesan}"

    except Exception as e:
        hasil["status"] = f"❌ Kesalahan proses akhir"
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
        <p class="text-center text-gray-600 mb-6">✅ Semua masuk keranjang → Langsung buat pesanan → Bayar manual</p>

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
                <label class="block text-sm font-medium text-gray-700 mb-1">Email Akun</label>
                <input type="email" id="email" placeholder="contoh@mail.com" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required>
            </div>

            <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Password Akun</label>
                <input type="text" id="password" placeholder="Minimal 6 karakter" class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" required>
            </div>

            <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 rounded-lg transition">🚀 Proses & Buat Pesanan</button>
        </form>

        <div id="hasil" class="mt-8 hidden"></div>
    </div>

    <script>
        const form = document.getElementById('formInput');
        const hasilDiv = document.getElementById('hasil');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            hasilDiv.innerHTML = '<div class="text-center py-6 text-gray-600">⏳ Memasukkan domain satu per satu...<br>Setelah selesai akan langsung buat tagihan!</div>';
            hasilDiv.classList.remove('hidden');

            const domains = document.getElementById('daftar_domain').value.split('\\n').map(d => d.trim()).filter(d => d);
            const jumlah = parseInt(document.getElementById('jumlah').value);

            if (domains.length !== jumlah) {
                hasilDiv.innerHTML = `<div class="text-red-600 p-4 border rounded-lg">❌ Jumlah domain tidak sesuai!</div>`;
                return;
            }

            if (jumlah < 2 || jumlah > 50) {
                hasilDiv.innerHTML = `<div class="text-red-600 p-4 border rounded-lg">❌ Minimal 2, maksimal 50 domain!</div>`;
                return;
            }

            const data = { domains, email: document.getElementById('email').value.trim(), password: document.getElementById('password').value.trim() };

            try {
                const res = await fetch('/proses', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
                const h = await res.json();

                let html = `<h2 class="text-xl font-semibold text-green-700 mb-4">📄 Ringkasan Pesanan</h2>`;
                html += `<div class="border rounded-lg p-5 ${h.status.includes('✅') ? 'bg-green-50' : 'bg-red-50'}">`;
                html += `<p><strong>Status:</strong> ${h.status}</p>`;
                html += `<p><strong>Jumlah Domain:</strong> ${h.jumlah}</p>`;
                html += `<p><strong>Daftar Domain:</strong><br>• ${h.daftar.join('<br>• ')}</p>`;
                html += `<p class="text-lg font-bold mt-3"><strong>Total Bayar:</strong> ${h.total_harga}</p>`;
                html += `<p><strong>Email Akun:</strong> ${h.email}</p>`;
                html += `<p><strong>Password:</strong> ${h.password}</p>`;

                if (h.invoice_id !== '-') {
                    html += `<hr class="my-3">`;
                    html += `<p><strong>Nomor Invoice:</strong> ${h.invoice_id}</p>`;
                    html += `<p><strong>Link Tagihan:</strong> <a href="${h.link_invoice}" target="_blank" class="text-blue-600 font-medium underline">${h.link_invoice}</a></p>`;
                    if (h.qris) html += `<p class="mt-3"><strong>QRIS Bayar:</strong><br><img src="data:image/png;base64,${h.qris}" class="mt-2 w-40 h-40 border p-1 rounded"></p>`;
                    html += `<p class="mt-2 text-sm text-orange-600 font-medium">💡 Lakukan pembayaran secara manual lewat link atau QRIS di atas</p>`;
                }

                html += `<p class="mt-3 text-sm text-gray-600"><strong>Keterangan:</strong><br>${h.keterangan}</p>`;
                html += `</div>`;

                hasilDiv.innerHTML = html;

            } catch (err) {
                hasilDiv.innerHTML = `<div class="text-red-600 p-4 border rounded-lg">❌ Terjadi kesalahan sistem: ${err}</div>`;
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
    app.run(debug=True)
