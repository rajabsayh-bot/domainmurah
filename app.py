import re
import time
import requests
import random
import string
from datetime import datetime
from flask import Flask, request, render_template_string

# ==============================================
# ✅ KONFIGURASI
# ==============================================
BASE_URL    = "https://hosting.arxan.app"
USER_AGENT  = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36"
TIMEOUT     = 20
MAKS_COBA   = 2  # Coba ulang kalau gagal

app = Flask(__name__)

# ==============================================
# 🎲 DATA ACAK
# ==============================================
def buat_nama_acak(panjang_min=4, panjang_maks=8):
    return ''.join(random.choices(string.ascii_lowercase, k=random.randint(panjang_min, panjang_maks))).capitalize()

def data_acak():
    return {
        "firstname": buat_nama_acak(),
        "lastname": buat_nama_acak(),
        "phonenumber": "628" + ''.join(random.choices(string.digits, k=9)),
        "address1": f"Jl. {buat_nama_acak(5,10)} No.{random.randint(1,200)}",
        "city": "Sukabumi",
        "state": "Jawa Barat",
        "postcode": "43111",
        "country": "ID",
        "paymentmethod": "duitkupop"
    }

# ==============================================
# 📋 AMBIL TOKEN + VALIDASI
# ==============================================
def get_token(sesi):
    for _ in range(MAKS_COBA):
        try:
            r = sesi.get(f"{BASE_URL}/cart.php?a=add&domain=register", timeout=TIMEOUT)
            if r.status_code == 200:
                token = re.search(r'name="token" value="([a-f0-9]{32,})"', r.text)
                if token:
                    return token.group(1)
        except:
            pass
        time.sleep(0.8)
    return None

# ==============================================
# ✅ CEK KETERSEDIAAN DOMAIN
# ==============================================
def cek_domain_tersedia(sesi, token, domain):
    try:
        res = sesi.post(
            f"{BASE_URL}/index.php?rp=/domain/check",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{BASE_URL}/cart.php?a=add&domain=register"
            },
            data={
                "token": token,
                "a": "checkDomain",
                "domain": domain,
                "type": "domain"
            },
            timeout=TIMEOUT
        )
        # Kalau ada tulisan "Available" berarti bisa dipakai
        return res.status_code == 200 and "available" in res.text.lower()
    except:
        return False

# ==============================================
# 🚀 PROSES DOMAIN LENGKAP
# ==============================================
def proses_domain(domain, email_input, sandi_akun):
    hasil = {"waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "domain": domain}

    sesi = requests.Session()
    sesi.headers.update({"User-Agent": USER_AGENT})

    # Ambil token
    token = get_token(sesi)
    if not token:
        hasil["status"] = "❌ Gagal dapat token"
        return hasil

    # Cek dulu domainnya
    if not cek_domain_tersedia(sesi, token, domain):
        hasil["status"] = "❌ Domain TIDAK tersedia / sudah dipakai"
        return hasil

    # Siap data akun
    akun = data_acak()
    akun["email"] = email_input
    akun["password"] = akun["password2"] = sandi_akun

    try:
        # Masukkan ke keranjang
        sesi.post(
            f"{BASE_URL}/cart.php",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"a": "addToCart", "domain": domain, "token": token, "whois": 0, "sideorder": 0},
            timeout=TIMEOUT
        )

        # Set nameserver
        sesi.post(
            f"{BASE_URL}/cart.php?a=confdomains",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"token": token, "update": "true", "domainns1": "kiki.bunny.net", "domainns2": "coco.bunny.net"},
            timeout=TIMEOUT
        )

        # Set wilayah Indonesia
        sesi.post(
            f"{BASE_URL}/cart.php?a=setstateandcountry&e=false",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"token": token, "country": "ID", "state": "Jawa Barat", "ajax": 1},
            timeout=TIMEOUT
        )

        # Proses checkout
        res_checkout = sesi.post(
            f"{BASE_URL}/cart.php?a=checkout",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": BASE_URL,
                "Referer": f"{BASE_URL}/cart.php?a=checkout&e=false"
            },
            data={
                "token": token, "checkout": "true", "custtype": "new",
                "firstname": akun["firstname"], "lastname": akun["lastname"],
                "email": akun["email"], "phonenumber": akun["phonenumber"],
                "address1": akun["address1"], "city": akun["city"],
                "state": akun["state"], "postcode": akun["postcode"], "country": akun["country"],
                "password": akun["password"], "password2": akun["password2"],
                "paymentmethod": "duitkupop", "accepttos": "on"
            },
            timeout=TIMEOUT,
            allow_redirects=True
        )

        # Cek apakah berhasil dapat invoice
        inv = re.search(r'viewinvoice\.php\?id=(\d+)', res_checkout.text)
        if inv:
            hasil.update({
                "email_akun": email_input,
                "pw_akun": sandi_akun,
                "link": f"{BASE_URL}/viewinvoice.php?id={inv.group(1)}",
                "status": "✅ BERHASIL! Domain siap dipakai"
            })
        else:
            hasil["status"] = "❌ Gagal proses checkout"

    except requests.exceptions.ReadTimeout:
        hasil["status"] = "❌ Timeout / Server lambat"
    except Exception as e:
        hasil["status"] = f"❌ Error: {str(e)[:50]}"

    return hasil

# ==============================================
# 🌐 HALAMAN UTAMA
# ==============================================
@app.route('/', methods=['GET', 'POST'])
def index():
    hasil = []
    pesan = ""

    if request.method == 'POST':
        try:
            jumlah = int(request.form.get('jumlah', 0))
            sandi = request.form.get('sandi', '').strip()
            daftar = []

            if jumlah < 1:
                pesan = "❌ Jumlah minimal 1!"
            elif len(sandi) < 6:
                pesan = "❌ Password minimal 6 karakter!"
            else:
                for i in range(1, jumlah + 1):
                    d = request.form.get(f'domain_{i}', '').strip().lower()
                    e = request.form.get(f'email_{i}', '').strip().lower()
                    if d and "." in d and "@" in e:
                        daftar.append((d, e))

                if not daftar:
                    pesan = "❌ Masukkan domain & email yang valid!"
                else:
                    for domain, email in daftar:
                        hasil.append(proses_domain(domain, email, sandi))
                        time.sleep(1)  # Kasih jeda lebih aman

        except Exception as e:
            pesan = f"❌ Kesalahan: {str(e)}"

    return render_template_string("""
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Creat Domain Murah</title>
    <style>
        * {margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',sans-serif}
        body {background:linear-gradient(135deg,#2c3e50,#3498db);min-height:100vh;padding:20px}
        .container {max-width:750px;margin:0 auto;background:#fff;padding:30px;border-radius:15px;box-shadow:0 8px 24px rgba(0,0,0,0.15)}
        h1 {text-align:center;color:#2c3e50;margin-bottom:30px;font-size:28px}
        .form-group {margin-bottom:18px}
        label {display:block;margin-bottom:6px;font-weight:500;color:#34495e}
        input {width:100%;padding:12px;border:1px solid #bdc3c7;border-radius:8px;font-size:15px}
        button {width:100%;padding:14px;background:#27ae60;color:white;border:none;border-radius:8px;font-size:17px;font-weight:600;cursor:pointer}
        button:hover {background:#219653}
        .pesan {padding:12px;margin:20px 0;border-radius:8px;text-align:center;font-weight:500}
        .error {background:#ffebee;color:#c62828}
        .sukses {background:#e8f5e9;color:#2e7d32}
        .hasil {margin-top:35px}
        .hasil h2 {text-align:center;color:#2c3e50;margin-bottom:20px}
        .kartu {background:#f8f9fa;border:1px solid #e9ecef;border-radius:10px;padding:18px;margin-bottom:15px}
        .kartu p {margin:8px 0;font-size:15px;color:#2d3436}
        .kartu strong {color:#2980b9}
        a {color:#27ae60;text-decoration:none;font-weight:500}
        a:hover {text-decoration:underline}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Creat Domain Murah</h1>

        {% if pesan %}
        <div class="pesan {{ 'error' if '❌' in pesan else 'sukses' }}">{{ pesan }}</div>
        {% endif %}

        <form method="POST">
            <div class="form-group">
                <label>🔢 Jumlah Domain:</label>
                <input type="number" name="jumlah" min="1" required placeholder="Contoh: 2">
            </div>

            <div class="form-group">
                <label>🔑 Password Semua Akun:</label>
                <input type="text" name="sandi" required placeholder="Minimal 6 karakter">
            </div>

            <div id="list-input"></div>

            <button type="submit">✨ Proses Sekarang</button>
        </form>

        {% if hasil %}
        <div class="hasil">
            <h2>📋 Hasil Pembuatan</h2>
            {% for h in hasil %}
            <div class="kartu">
                <p><strong>🌐 Domain:</strong> {{ h.domain or '-' }}</p>
                <p><strong>📧 Email Terdaftar:</strong> {{ h.email_akun or '-' }}</p>
                <p><strong>🔑 Password Akun:</strong> {{ h.pw_akun or '-' }}</p>
                {% if h.link %}
                <p><strong>🔗 Link Invoice:</strong> <a href="{{ h.link }}" target="_blank">Buka Invoice</a></p>
                {% endif %}
                <p><strong>📊 Status:</strong> {{ h.status }}</p>
            </div>
            {% endfor %}
        </div>
        {% endif %}
    </div>

    <script>
        const jmlInput = document.querySelector('input[name="jumlah"]');
        const listDiv = document.getElementById('list-input');

        jmlInput.addEventListener('input', () => {
            const jml = parseInt(jmlInput.value) || 0;
            listDiv.innerHTML = '';
            for(let i = 1; i <= jml; i++) {
                const div = document.createElement('div');
                div.className = 'form-group';
                div.innerHTML = `
                    <label>📝 Domain ke-${i}:</label>
                    <input type="text" name="domain_${i}" required placeholder="Contoh: namamu.biz.id">
                    <label style="margin-top:8px;">📧 Email ke-${i}:</label>
                    <input type="email" name="email_${i}" required placeholder="Contoh: kamu@gmail.com">
                `;
                listDiv.appendChild(div);
            }
        });
    </script>
</body>
</html>
""", hasil=hasil, pesan=pesan)

if __name__ == "__main__":
    app.run(debug=False)
