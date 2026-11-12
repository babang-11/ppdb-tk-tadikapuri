import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import time
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

# ================= SECRET KEY =================
app.secret_key = 'secret123'

# ================= KONFIGURASI SQLITE DATABASE =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'ppdb.db')

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static/uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Tabel Users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            foto TEXT,
            no_hp TEXT
        )
    """)

    # Tabel Siswa
    cur.execute("""
        CREATE TABLE IF NOT EXISTS siswa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_siswa TEXT,
            nama_panggilan TEXT,
            tempat_lahir TEXT,
            tanggal_lahir TEXT,
            jenis_kelamin TEXT,
            agama TEXT,
            alamat TEXT,
            tinggi_badan TEXT,
            berat_badan TEXT,
            nama_ayah TEXT,
            pekerjaan_ayah TEXT,
            nama_ibu TEXT,
            pekerjaan_ibu TEXT,
            file_kk TEXT,
            file_akta TEXT,
            foto TEXT,
            status TEXT DEFAULT 'Belum Verifikasi'
        )
    """)

    # Tabel Pembayaran
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pembayaran (
            id_pembayaran INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            bukti TEXT,
            status TEXT DEFAULT 'Menunggu Verifikasi'
        )
    """)

    # Buat akun admin default jika belum ada
    cur.execute("SELECT * FROM users WHERE role='admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (nama, email, password, role) VALUES (?, ?, ?, ?)",
            ('Admin TK Tadika Puri', 'admin@tadikapuri.com', 'admin123', 'admin')
        )

    conn.commit()
    conn.close()

# Jalankan inisialisasi tabel saat aplikasi dimuat
init_db()

# ================= LANDING PAGE / HOME =================
@app.route('/')
def home():
    sudah_bayar = False
    if 'login' in session:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT *
            FROM pembayaran
            WHERE email=?
            ORDER BY id_pembayaran DESC
            LIMIT 1
        """, (session['email'],))
        bayar = cur.fetchone()
        conn.close()
        if bayar:
            sudah_bayar = True

    return render_template('landing.html', sudah_bayar=sudah_bayar)

# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT nama, email, password, role, foto FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        conn.close()

        # Mendukung pengecekan password plain text maupun password hasil reset (hash)
        is_valid = False
        if user:
            if user[2] == password or check_password_hash(user[2], password):
                is_valid = True

        if is_valid:
            session['login'] = True
            session['nama'] = user[0]
            session['email'] = user[1]
            session['role'] = user[3]
            if user[4]:
                session['foto'] = user[4]

            if user[3] == 'admin':
                return redirect('/admin_dashboard')
            else:
                return redirect('/dashboard')

        flash("Login gagal! Email atau password salah.")

    return render_template('login.html')

# ================= DASHBOARD USER =================
@app.route('/dashboard')
def dashboard():
    if 'login' not in session:
        return redirect('/login')

    if session.get('role') == 'admin':
        return redirect('/admin_dashboard')

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT status
        FROM pembayaran
        WHERE email=?
        ORDER BY id_pembayaran DESC
        LIMIT 1
    """, (session['email'],))

    data = cur.fetchone()
    conn.close()

    status = data[0] if data else "Belum Bayar"

    return render_template('dashboard.html', nama=session['nama'], status=status)

# ================= REGISTER (LANGKAH 1) =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nama = request.form['nama']
        email = request.form['email']
        password = request.form['password']
        no_hp = request.form.get('no_hp', '')

        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM users WHERE email=?", (email,))
        if cur.fetchone():
            conn.close()
            flash("Email sudah terdaftar! Silakan login atau gunakan email lain.")
            return redirect('/login')

        cur.execute(
            "INSERT INTO users (nama, email, password, role, no_hp) VALUES (?, ?, ?, ?, ?)",
            (nama, email, password, 'user', no_hp)
        )
        conn.commit()
        conn.close()

        session['login'] = True
        session['nama'] = nama
        session['email'] = email
        session['role'] = 'user'

        return redirect(url_for('pendaftaran'))

    return render_template('register.html')

# ================= PENDAFTARAN FORMAL (LANGKAH 2) =================
@app.route('/pendaftaran', methods=['GET', 'POST'])
def pendaftaran():
    if 'login' not in session:
        return redirect('/login')

    if request.method == 'POST':
        nama = request.form['nama']
        nama_panggilan = request.form['nama_panggilan']
        alamat = request.form['alamat']
        tgl_lahir = request.form['tgl_lahir']
        jenis_kelamin = request.form['jenis_kelamin']
        agama = request.form['agama']
        tinggi_badan = request.form['tinggi_badan']
        berat_badan = request.form['berat_badan']

        nama_ayah = request.form['nama_ayah']
        pekerjaan_ayah = request.form['pekerjaan_ayah']
        nama_ibu = request.form['nama_ibu']
        pekerjaan_ibu = request.form['pekerjaan_ibu']

        def save_file(file):
            if file and file.filename != '':
                filename = str(int(time.time())) + "_" + secure_filename(file.filename)
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'])
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(path)
                return filename
            return None

        kk = save_file(request.files.get('kk'))
        akta = save_file(request.files.get('akta'))
        foto = save_file(request.files.get('foto'))

        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO siswa (
                nama_siswa, nama_panggilan, tempat_lahir, tanggal_lahir,
                jenis_kelamin, agama, alamat, tinggi_badan, berat_badan,
                nama_ayah, pekerjaan_ayah, nama_ibu, pekerjaan_ibu,
                file_kk, file_akta, foto, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nama, nama_panggilan, 'Depok', tgl_lahir,
            jenis_kelamin, agama, alamat, tinggi_badan, berat_badan,
            nama_ayah, pekerjaan_ayah, nama_ibu, pekerjaan_ibu,
            kk, akta, foto, 'Belum Verifikasi'
        ))

        conn.commit()
        conn.close()

        return redirect(url_for('pembayaran'))

    return render_template('pendaftaran.html')

# ================= PEMBAYARAN & PENINJAUAN (LANGKAH 3) =================
@app.route('/pembayaran', methods=['GET', 'POST'])
def pembayaran():
    if 'login' not in session:
        return redirect('/login')

    if request.method == 'POST':
        file = request.files['bukti']

        folder = os.path.join(BASE_DIR, 'static/bukti')
        if not os.path.exists(folder):
            os.makedirs(folder)

        filename = str(int(time.time())) + "_" + secure_filename(file.filename)
        file.save(os.path.join(folder, filename))

        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pembayaran (email, bukti, status)
            VALUES (?, ?, ?)
        """, (session['email'], filename, 'Menunggu Verifikasi'))
        conn.commit()
        conn.close()

        return render_template('terima_kasih.html')

    return render_template('bukti_pembayaran.html')

# ================= STATUS PEMBAYARAN USER =================
@app.route('/status_pembayaran')
def status_pembayaran():
    if 'login' not in session:
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT status 
        FROM pembayaran 
        WHERE email=? 
        ORDER BY id_pembayaran DESC 
        LIMIT 1
    """, (session['email'],))
    data_bayar = cur.fetchone()

    cur.execute("SELECT id FROM siswa WHERE nama_siswa LIKE ? ORDER BY id DESC LIMIT 1", ('%' + session['nama'] + '%',))
    data_siswa = cur.fetchone()
    
    if not data_siswa:
        cur.execute("SELECT id FROM siswa ORDER BY id DESC LIMIT 1")
        data_siswa = cur.fetchone()
        
    conn.close()

    status = data_bayar[0] if data_bayar else "Belum Bayar"
    id_siswa = data_siswa[0] if data_siswa else None

    return render_template('status_pembayaran.html', status=status, id_siswa=id_siswa)

# ================= DOWNLOAD SURAT PENERIMAAN UNTUK USER =================
@app.route('/download_bukti_user/<id>')
def download_bukti_user(id):
    if 'login' not in session:
        return redirect('/login')

    return cetak_bukti(id)

# ================= PROFILE USER =================
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'login' not in session:
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email=?", (session['email'],))
    user = cur.fetchone()

    if request.method == 'POST':
        nama = request.form['nama']
        no_hp = request.form['no_hp']
        foto = request.files.get('foto')
        nama_foto = user['foto'] if user and user['foto'] else None

        if foto and foto.filename != '':
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            nama_foto = secure_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], nama_foto))

        cur.execute("""
            UPDATE users
            SET nama=?, no_hp=?, foto=?
            WHERE email=?
        """, (nama, no_hp, nama_foto, session['email']))

        conn.commit()
        session['nama'] = nama
        session['foto'] = nama_foto
        conn.close()
        return redirect('/profile')

    conn.close()
    return render_template('profile.html', user=user)

# ================= DASHBOARD ADMIN =================
@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total_user = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pembayaran WHERE status='Menunggu Verifikasi'")
    pending = cur.fetchone()[0]
    conn.close()

    return render_template('admin_dashboard.html', total_user=total_user, pending=pending)

# ================= DATA SISWA (ADMIN) =================
@app.route('/data_siswa')
def data_siswa():
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM siswa")
    data = cur.fetchall()
    conn.close()

    return render_template('data_siswa.html', siswa=data)

# ================= DETAIL SISWA (ADMIN) =================
@app.route('/detail_siswa/<id>')
def detail_siswa(id):
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM siswa WHERE id=?", (id,))
    siswa = cur.fetchone()
    conn.close()

    if not siswa:
        return "Data siswa tidak ditemukan!"

    return render_template('detail_siswa.html', siswa=siswa)

# ================= EDIT SISWA (ADMIN) =================
@app.route('/edit_siswa/<id>', methods=['GET', 'POST'])
def edit_siswa(id):
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        nama = request.form['nama_siswa']
        jk = request.form['jenis_kelamin']
        tgl = request.form['tanggal_lahir']
        alamat = request.form['alamat']

        cur.execute("""
            UPDATE siswa
            SET nama_siswa=?, jenis_kelamin=?, tanggal_lahir=?, alamat=?
            WHERE id=?
        """, (nama, jk, tgl, alamat, id))

        conn.commit()
        conn.close()
        return redirect('/data_siswa')

    cur.execute("SELECT * FROM siswa WHERE id=?", (id,))
    siswa = cur.fetchone()
    conn.close()

    return render_template('edit_siswa.html', siswa=siswa)

# ================= HAPUS SISWA (ADMIN) =================
@app.route('/hapus_siswa/<id>')
def hapus_siswa(id):
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM siswa WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect('/data_siswa')

# ================= DATA PEMBAYARAN (ADMIN) =================
@app.route('/data_pembayaran')
def data_pembayaran():
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id_pembayaran, email, bukti, status
        FROM pembayaran
        ORDER BY id_pembayaran DESC
    """)
    data = cur.fetchall()
    conn.close()

    return render_template('data_pembayaran.html', pembayaran=data)

# ================= VERIFIKASI PEMBAYARAN (ADMIN) =================
@app.route('/verifikasi/<id>/<status>')
def verifikasi(id, status):
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE pembayaran
        SET status=?
        WHERE id_pembayaran=?
    """, (status, id))

    conn.commit()
    conn.close()

    return redirect('/data_pembayaran')

@app.route('/acc/<int:id>')
def acc(id):
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE pembayaran 
        SET status='Lunas' 
        WHERE id_pembayaran=?
    """, (id,))
    conn.commit()
    conn.close()

    return redirect(url_for('data_pembayaran'))

# ================= MANAGEMENT USER (ADMIN) =================
@app.route('/tambah', methods=['POST'])
def tambah_user():
    if session.get('role') != 'admin':
        return "Akses ditolak ❌"

    nama = request.form['nama']
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']

    password_hash = generate_password_hash(password)

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (nama, email, password, role) VALUES (?, ?, ?, ?)",
        (nama, email, password_hash, role)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard'))

@app.route('/hapus/<int:id>')
def hapus_user(id):
    if session.get('role') != 'admin':
        return "Akses ditolak ❌"

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard'))

# ================= 1. REKAPITULASI DATA SISWA TAHUN AJARAN BARU =================
@app.route('/cetak_pdf')
def cetak_pdf():
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.nama_siswa, s.jenis_kelamin, s.alamat, p.status 
        FROM siswa s
        LEFT JOIN pembayaran p ON s.nama_siswa = p.email OR p.status IN ('Lunas', 'Disetujui', 'Diterima')
        GROUP BY s.id
    """)
    data_siswa = cur.fetchall()
    conn.close()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    logo_path = os.path.join(BASE_DIR, "static/image/logo-transparent.png")
    logo = Image(logo_path, width=65, height=65) if os.path.exists(logo_path) else Paragraph("", styles['Normal'])
    
    header_text = Paragraph(
        """
        <font size="14" color="#01579b"><b>PANITIA PENERIMAAN PESERTA DIDIK BARU (PPDB)</b></font><br/>
        <font size="12" color="#0288d1"><b>TK TADIKA PURI DEPOK</b></font><br/>
        <font size="8" color="#475569">Griya Depok Asri Blok C2/6, Mekar Jaya, Kec. Sukmajaya, Kota Depok, Jawa Barat<br/>
        Telp: (021) 7709548 | Email: tktadikapuriad@gmail.com</font>
        """,
        styles['Normal']
    )

    kop_table = Table([[logo, header_text]], colWidths=[75, 465])
    kop_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,-1), 2, colors.HexColor('#01579b')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(kop_table)
    elements.append(Spacer(1, 15))

    title = Paragraph("<font size='12' color='#01579b'><b>REKAPITULASI DATA SISWA (TAHUN AJARAN BARU)</b></font>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 15))

    table_data = [[
        Paragraph('<b>No</b>', styles['Normal']),
        Paragraph('<b>Nama Lengkap Siswa</b>', styles['Normal']),
        Paragraph('<b>L/P</b>', styles['Normal']),
        Paragraph('<b>Alamat Domisili</b>', styles['Normal']),
        Paragraph('<b>Status</b>', styles['Normal'])
    ]]

    no = 1
    for s in data_siswa:
        table_data.append([
            str(no),
            Paragraph(s[0] if s[0] else '-', styles['Normal']),
            'L' if s[1] == 'Laki-laki' else 'P',
            Paragraph(s[2] if s[2] else '-', styles['Normal']),
            'Diterima'
        ])
        no += 1

    tabel_laporan = Table(table_data, colWidths=[30, 160, 45, 215, 90])
    tabel_laporan.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#01579b')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('ALIGN', (2,0), (2,-1), 'CENTER'),
        ('ALIGN', (4,0), (4,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    elements.append(tabel_laporan)
    elements.append(Spacer(1, 25))

    ttd_data = [
        ['', 'Depok, ' + time.strftime('%d %B %Y')],
        ['', 'Kepala Sekolah TK Tadika Puri'],
        ['', ''],
        ['', '( Hj. Nurhayati, S.Pd. )']
    ]
    ttd_table = Table(ttd_data, colWidths=[320, 220])
    ttd_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ('FONTNAME', (1,3), (1,3), 'Helvetica-Bold')
    ]))
    elements.append(ttd_table)

    doc.build(elements)
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=rekapitulasi_siswa_tahun_ajaran_baru.pdf'
    return response

# ================= SURAT PENERIMAAN INDIVIDUAL PER SISWA (PDF REPORTLAB) =================
@app.route('/cetak_bukti/<id>')
def cetak_bukti(id):
    if 'login' not in session:
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT nama_siswa, nama_panggilan, tempat_lahir, tanggal_lahir, 
               jenis_kelamin, agama, alamat, nama_ayah, nama_ibu
        FROM siswa 
        WHERE id=?
    """, (id,))
    siswa = cur.fetchone()
    conn.close()

    if not siswa:
        return "Data siswa tidak ditemukan!"

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    styles = getSampleStyleSheet()

    logo_path = os.path.join(BASE_DIR, "static/image/logo-transparent.png")
    logo = Image(logo_path, width=65, height=65) if os.path.exists(logo_path) else Paragraph("", styles['Normal'])

    header_text = Paragraph(
        """
        <font size="14" color="#01579b"><b>PANITIA PENERIMAAN PESERTA DIDIK BARU (PPDB)</b></font><br/>
        <font size="12" color="#0288d1"><b>TK TADIKA PURI DEPOK</b></font><br/>
        <font size="8" color="#475569">Griya Depok Asri Blok C2/6, Mekar Jaya, Kec. Sukmajaya, Kota Depok, Jawa Barat<br/>
        Telp: (021) 7709548 | Email: tktadikapuriad@gmail.com</font>
        """,
        styles['Normal']
    )

    kop_table = Table([[logo, header_text]], colWidths=[75, 455])
    kop_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,-1), 2, colors.HexColor('#01579b')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(kop_table)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("<font size='13' color='#01579b'><b><u>SURAT KETERANGAN PENERIMAAN SISWA BARU</u></b></font>", styles['Normal']))
    elements.append(Spacer(1, 15))

    pesan = Paragraph(
        "Selamat! Berdasarkan hasil verifikasi berkas dan pembayaran administrasi PPDB TK Tadika Puri, dengan ini menyatakan bahwa calon siswa di bawah ini <b>RESMI DITERIMA</b> sebagai siswa baru:",
        styles['Normal']
    )
    elements.append(pesan)
    elements.append(Spacer(1, 15))

    nama_ayah = siswa[7] if siswa[7] else '-'
    nama_ibu = siswa[8] if siswa[8] else '-'

    detail_data = [
        ['Nama Lengkap', ':', siswa[0]],
        ['Nama Panggilan', ':', siswa[1] if siswa[1] else '-'],
        ['Tempat, Tgl Lahir', ':', f"{siswa[2]}, {siswa[3]}"],
        ['Jenis Kelamin', ':', siswa[4]],
        ['Agama', ':', siswa[5] if siswa[5] else '-'],
        ['Alamat Domisili', ':', siswa[6] if siswa[6] else '-'],
        ['Nama Orang Tua', ':', f"Ayah: {nama_ayah} | Ibu: {nama_ibu}"],
        ['Status Pendaftaran', ':', 'DITERIMA / LUNAS']
    ]

    tabel_biodata = Table(detail_data, colWidths=[130, 20, 380])
    tabel_biodata.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 6),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
    ]))
    elements.append(tabel_biodata)
    elements.append(Spacer(1, 20))

    pesan_penutup = Paragraph(
        "Demikian surat keterangan ini diterbitkan untuk dipergunakan sebagaimana mestinya. Silakan simpan surat ini sebagai bukti pendaftaran resmi.",
        styles['Normal']
    )
    elements.append(pesan_penutup)
    elements.append(Spacer(1, 30))

    ttd_data = [
        ['', 'Depok, ' + time.strftime('%d %B %Y')],
        ['', 'Kepala Sekolah TK Tadika Puri'],
        ['', ''],
        ['', '( Hj. Nurhayati, S.Pd. )']
    ]
    ttd_table = Table(ttd_data, colWidths=[310, 220])
    ttd_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ('FONTNAME', (1,3), (1,3), 'Helvetica-Bold')
    ]))
    elements.append(ttd_table)

    doc.build(elements)
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=Surat_Penerimaan_{siswa[0]}.pdf'
    return response

# ================= LUPA & RESET PASSWORD =================
@app.route('/lupa_password', methods=['GET', 'POST'])
def lupa_password():
    if request.method == 'POST':
        email = request.form['email']

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        conn.close()

        if user:
            return redirect(url_for('reset_password', email=email))
        else:
            flash("Email tidak ditemukan!")

    return render_template('lupa_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        password_baru = request.form.get('password_baru')

        if not email or not password_baru:
            flash("Semua field wajib diisi!")
            return redirect(url_for('reset_password'))

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cur.fetchone()

        if not user:
            conn.close()
            flash("User tidak ditemukan!")
            return redirect(url_for('reset_password'))

        password_hash = generate_password_hash(password_baru)
        cur.execute("UPDATE users SET password=? WHERE email=?", (password_hash, email))
        conn.commit()
        conn.close()

        flash("Password berhasil direset! Silakan login.")
        return redirect(url_for('login'))

    return render_template('reset_password.html')

# ================= LOGOUT =================
@app.route('/logout')
def logout():       
    session.clear()
    return redirect('/')

# ================= RUN =================
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )