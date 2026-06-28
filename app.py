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
TIMEOUT = 20
MIN_DOMAIN = 1
MAX_DOMAIN = 3  # Tetap maks 3 per email
JEDA_ANTAR = [1.8, 2.2, 2.7]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 14; SM-A556E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Redmi Note 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1"
]

# ==============================================
# 🛠️ FUNGSI
# ==============================================
def get_token(sesi):
    try:
        r = sesi.get(f"{BASE_URL}/cart.php?a=add&domain=register", timeout=TIMEOUT)
        token = re.search(r'name="token" value="([a-f0-9]{32,})"', r.text)
        return token.group(1) if token else None
    except:
        return None

def cek_keranjang(sesi):
    try:
        r = sesi.get(f"{BASE_URL}/cart.php?a=view", timeout=TIMEOUT)
        return "Keranjang Belanja" in r.text
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
# 🚀 PROSES SATU KELOMPOK (1-3 domain + 1 email)
# ==============================================
def proses_satu_kelompok(daftar_domain, email, password):
    sesi = requests.Session()
    sesi.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1"
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

    # Cek batas
    if not (MIN_DOMAIN <= len(daftar_domain) <= MAX_DOMAIN):
        hasil["status"] = f"❌ Harus {MIN_DOMAIN}-{MAX_DOMAIN} domain"
        return hasil

    token = get_token(sesi)
    if not token:
        hasil["status"] = "❌ Gagal dapat token"
        return hasil

    total = 0
    domain_berhasil = []

    for domain in daftar_domain:
        try:
            cek = sesi.post(
                f"{BASE_URL}/index.php?rp=/domain/check",
                headers={"Content-Type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest", "Referer": f"{BASE_URL}/cart.php?a=add&domain=register"},
                data={"token": token, "a": "checkDomain", "domain": domain, "type": "domain"},
                timeout=TIMEOUT
            )

            if "available" not in cek.text.lower():
                hasil["keterangan"] += f"❌ {domain} tidak tersedia | "
                time.sleep(random.choice(JEDA_ANTAR))
                continue

            hrg = re.search(r'Rp\s*(\d+)', cek.text)
            if hrg:
                total += int(hrg.group(1))

            sesi.post(
                f"{BASE_URL}/cart.php",
                headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": f"{BASE_URL}/cart.php?a=add&domain=register"},
                data={"a": "addToCart", "domain": domain, "token": token, "years": 1, "idprotection": 0, "dnsmanagement": 0, "emailforwarding": 0, "whois": 0},
                timeout=TIMEOUT
            )

            domain_berhasil.append(domain)
            hasil["keterangan"] += f"✅ {domain} masuk | "
            time.sleep(random.choice(JEDA_ANTAR))

        except Exception as e:
            hasil["keterangan"] += f"⚠️ {domain} gagal: {str(e)[:25]} | "
            continue

    if not domain_berhasil:
        hasil["status"] = "❌ Tidak ada domain masuk"
        return hasil

    hasil["total_harga"] = f"Rp {total:,}"

    if not cek_keranjang(sesi):
        hasil["status"] = "❌ Keranjang kosong"
        return hasil

    try:
        sesi.post(
            f"{BASE_URL}/cart.php?a=confdomains",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"token": token, "update": "true", "domainns1": "kiki.bunny.net", "domainns2": "coco.bunny.net"},
            timeout=TIMEOUT
        )
        time.sleep(2)

        sesi.post(
            f"{BASE_URL}/cart.php?a=setstateandcountry&e=false",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"token": token, "country": "ID", "state": "Jawa Barat", "ajax": 1},
            timeout=TIMEOUT
        )
        time.sleep(2)

        res = sesi.post(
            f"{BASE_URL}/cart.php?a=checkout",
            headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": BASE_URL, "Referer": f"{BASE_URL}/cart.php?a=confdomains"},
            data={
                "token": token, "checkout": "true", "custtype": "new",
                "firstname": "Budi", "lastname": "Santoso", "email": email,
                "emailoptin": "0", "phonenumber": "628123456789",
                "address1": "Jl. Mawar No.1", "city": "Sukabumi", "state": "Jawa Barat",
                "postcode": "43111", "country": "ID", "password": password,
                "password2": password, "securityqid": "0", "securityans": "",
                "paymentmethod": "duitkupop", "accepttos": "on", "marketingoptin": "0"
            },
            timeout=30, allow_redirects=True
        )

        if "viewinvoice.php" in res.text or "viewinvoice.php" in res.url:
            inv = re.search(r'viewinvoice\.php\?id=(\d+)', res.text + res.url)
            if inv:
                hasil["invoice_id"] = inv.group(1)
                hasil["link_invoice"] = f"{BASE_URL}/viewinvoice.php?id={inv.group(1)}"
                hasil["status"] = f"✅ Berhasil | {len(domain_berhasil)} domain"
                r_qr = sesi.get(hasil["link_invoice"], timeout=15)
                kode_qr = re.search(r'data-qr="([^"]+)"', r_qr.text)
                hasil["qris"] = buat_qr_base64(kode_qr.group(1)) if kode_qr else ""
        else:
            err = re.search(r'<div class="alert[^>]*>(.*?)</div>|<li>(.*?)</li>', res.text, re.S)
            pesan = (err.group(1) or err.group(2) or "Dibatalkan")[:180]
            hasil["status"] = "❌ Gagal"
            hasil["keterangan"] += f" | Alasan: {pesan}"

    except Exception as e:
        hasil["status"] = "❌ Kesalahan"
        hasil["keterangan"] += f" | {str(e)[:50]}"

    return hasil

# ==============================================
# 🚀 PROSES SEMUA KELOMPOK
# ==============================================
@app.route('/proses', methods=['POST'])
def jalankan_proses():
    daftar_kelompok = request.get_json().get("kelompok", [])
    hasil_akhir = []

    for kelompok in daftar_kelompok:
        domains = kelompok.get("domains", [])
        email = kelompok.get("email", "").strip()
        password = kelompok.get("password", "").strip()
        if domains and email and password:
            hasil_akhir.append(proses_satu_kelompok(domains, email, password))
            time.sleep(3)  # Jeda antar kelompok

    return jsonify({"hasil": hasil_akhir})

# ==============================================
# 🎨 HALAMAN WEB DENGAN TOMBOL + TAMBAH
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
    <div class="max-w-4xl mx-auto bg-white rounded-xl shadow-lg p-6">
        <h1 class="text-2xl font-bold text-center text-indigo-700 mb-2">📝 Beli Banyak Domain</h1>
        <p class="text-center text-gray-600 mb-4">✅ Maks 3 domain per email | Klik <b>+ Tambah Baris</b> kalau mau lebih banyak</p>

        <div id="daftarBaris" class="space-y-6 mb-6">
            <!-- Baris Pertama -->
            <div class="baris p-4 border rounded-lg bg-gray-50">
                <h3 class="font-semibold mb-2">Kelompok 1</h3>
                <div class="grid md:grid-cols-3 gap-3 mb-3">
                    <div>
                        <label class="text-sm text-gray-700">Jumlah (1-3)</label>
                        <input type="number" class="jumlah w-full px-2 py-1 border rounded" min="1" max="3" value="2" required>
                    </div>
                    <div>
                        <label class="text-sm text-gray-700">Email</label>
                        <input type="email" class="email w-full px-2 py-1 border rounded" placeholder="email@baru.com" required>
                    </div>
                    <div>
                        <label class="text-sm text-gray-700">Password</label>
                        <input type="text" class="password w-full px-2 py-1 border rounded" placeholder="Min 6 karakter" required>
                    </div>
                </div>
                <div>
                    <label class="text-sm text-gray-700">Daftar Domain</label>
                    <textarea class="domains w-full px-2 py-1 border rounded" rows="2" placeholder="domain1.biz.id&#10;domain2.biz.id" required></textarea>
                </div>
            </div>
        </div>

        <div class="flex gap-3 mb-6">
            <button type="button" onclick="tambahBaris()" class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg">+ Tambah Baris</button>
            <button type="button" onclick="hapusBaris()" class="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg">Hapus Baris Terakhir</button>
        </div>

        <button onclick="prosesSemua()" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 rounded-lg">🚀 Proses Semua Kelompok</button>

        <div id="hasil" class="mt-8 hidden space-y-4"></div>
    </div>

    <script>
        let nomorBaris = 1;

        function tambahBaris() {
            nomorBaris++;
            const html = `
            <div class="baris p-4 border rounded-lg bg-gray-50">
                <h3 class="font-semibold mb-2">Kelompok ${nomorBaris}</h3>
                <div class="grid md:grid-cols-3 gap-3 mb-3">
                    <div>
                        <label class="text-sm text-gray-700">Jumlah (1-3)</label>
                        <input type="number" class="jumlah w-full px-2 py-1 border rounded" min="1" max="3" value="2" required>
                    </div>
                    <div>
                        <label class="text-sm text-gray-700">Email</label>
                        <input type="email" class="email w-full px-2 py-1 border rounded" placeholder="email@baru.com" required>
                    </div>
                    <div>
                        <label class="text-sm text-gray-700">Password</label>
                        <input type="text" class="password w-full px-2 py-1 border rounded" placeholder="Min 6 karakter" required>
                    </div>
                </div>
                <div>
                    <label class="text-sm text-gray-700">Daftar Domain</label>
                    <textarea class="domains w-full px-2 py-1 border rounded" rows="2" placeholder="domain1.biz.id&#10;domain2.biz.id" required></textarea>
                </div>
            </div>`;
            document.getElementById("daftarBaris").insertAdjacentHTML("beforeend", html);
        }

        function hapusBaris() {
            const semua = document.querySelectorAll(".baris");
            if (semua.length > 1) {
                semua[semua.length - 1].remove();
                nomorBaris--;
            }
        }

        async function prosesSemua() {
            const hasilDiv = document.getElementById("hasil");
            hasilDiv.innerHTML = '<div class="text-center py-6 text-gray-600">⏳ Memproses semua kelompok... Jangan tutup halaman!</div>';
            hasilDiv.classList.remove("hidden");

            const kelompok = [];
            const semuaBaris = document.querySelectorAll(".baris");

            for (const baris of semuaBaris) {
                const jml = parseInt(baris.querySelector(".jumlah").value);
                const email = baris.querySelector(".email").value.trim();
                const pass = baris.querySelector(".password").value.trim();
                const list = baris.querySelector(".domains").value.split("\n").map(d => d.trim()).filter(d => d);

                if (list.length !== jml || jml < 1 || jml > 3) {
                    hasilDiv.innerHTML = `<div class="text-red-600 p-4 rounded-lg">❌ Ada baris yang salah: jumlah harus 1-3!</div>`;
                    return;
                }
                kelompok.push({domains: list, email: email, password: pass});
            }

            try {
                const res = await fetch("/proses", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({kelompok: kelompok})
                });
                const data = await res.json();
                let html = `<h2 class="text-xl font-semibold mb-4">📋 Hasil Semua Kelompok</h2>`;

                data.hasil.forEach((h, i) => {
                    html += `
                    <div class="p-4 rounded-lg border mb-3 ${h.status.includes('✅') ? 'bg-green-50' : 'bg-red-50'}">
                        <h4 class="font-bold mb-2">Kelompok ${i+1}</h4>
                        <p><strong>Status:</strong> ${h.status}</p>
                        <p><strong>Domain:</strong> ${h.daftar.join(', ')}</p>
                        <p><strong>Email:</strong> ${h.email}</p>
                        <p><strong>Total:</strong> ${h.total_harga}</p>`;
                    if (h.invoice_id !== '-') {
                        html += `<p><strong>Invoice:</strong> ${h.invoice_id}</p>
                        <p><strong>Link:</strong> <a href="${h.link_invoice}" target="_blank" class="text-blue-600 underline">Buka Tagihan</a></p>`;
                        if (h.qris) html += `<p class="mt-2"><strong>QRIS:</strong><br><img src="data:image/png;base64,${h.qris}" class="w-32 h-32 mt-1 border p-1 rounded"></p>`;
                    }
                    html += `<p class="text-sm text-gray-700 mt-2">${h.keterangan.replaceAll('|', '<br>')}</p>
                    </div>`;
                });

                hasilDiv.innerHTML = html;

            } catch (err) {
                hasilDiv.innerHTML = `<div class="text-red-600 p-4 rounded-lg">❌ Error: ${err}</div>`;
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def halaman_utama():
    return render_template_string(HALAMAN_HTML)

if __name__ == '__main__':
    app.run(debug=True)
