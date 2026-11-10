from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO
from flask import make_response
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
app = Flask(__name__)
# ================= SECRET KEY =================
app.secret_key = 'secret123'
# ================= DATABASE =================
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'tk_tadika_puri'
mysql = MySQL(app)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT nama, email, password, role FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and user[2] == password:
            session['login'] = True
            session['nama'] = user[0]
            session['email'] = user[1]
            session['role'] = user[3]

            if user[3] == 'admin':
                return redirect('/dashboard')  # 🔥 pakai UI lama
            else:
                return redirect('/dashboard')

        flash("Login gagal!")

    return render_template('login.html')

# ================= REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nama = request.form['nama']
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO users (nama, email, password, role) VALUES (%s, %s, %s, %s)",
            (nama, email, password, 'user')  # ❌ TANPA HASH
        )
        mysql.connection.commit()
        cur.close()

        flash("Register berhasil!")
        return redirect(url_for('login'))

    return render_template('register.html')
# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    if 'login' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT status
        FROM pembayaran
        WHERE email=%s
        ORDER BY id_pembayaran DESC
        LIMIT 1
    """, (session['email'],))

    data = cur.fetchone()
    cur.close()

    status = data[0] if data else "Belum Bayar"

    return render_template('dashboard.html', nama=session['nama'], status=status)

# ================= PENDAFTARAN SISWA =================
from flask import request, render_template, redirect, url_for
import os
from werkzeug.utils import secure_filename
from datetime import datetime

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/pendaftaran', methods=['GET','POST'])
def pendaftaran():
    if request.method == 'POST':
        email = session['email']

        # ================= IDENTITAS SISWA =================
        nama = request.form['nama']
        nama_panggilan = request.form['nama_panggilan']
        alamat = request.form['alamat']
        tgl_lahir = request.form['tgl_lahir']
        umur = request.form['umur']
        jenis_kelamin = request.form['jenis_kelamin']
        agama = request.form['agama']
        tinggi_badan = request.form['tinggi_badan']
        berat_badan = request.form['berat_badan']

        # ================= DATA AYAH =================
        nama_ayah = request.form['nama_ayah']
        pekerjaan_ayah = request.form['pekerjaan_ayah']

        # ================= DATA IBU =================
        nama_ibu = request.form['nama_ibu']
        pekerjaan_ibu = request.form['pekerjaan_ibu']

        # ================= FILE UPLOAD =================
        def save_file(file):
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(path)
                return filename
            return None

        kk = save_file(request.files.get('kk'))
        akta = save_file(request.files.get('akta'))
        foto = save_file(request.files.get('foto'))

        # ================= SIMPAN KE DATABASE =================
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO siswa (
                email,
                nama_siswa,
                nama_panggilan,
                alamat,
                tanggal_lahir,
                umur,
                jenis_kelamin,
                agama,
                tinggi_badan,
                berat_badan,
                nama_ayah,
                pekerjaan_ayah,
                nama_ibu,
                pekerjaan_ibu,
                kk,
                akta,
                foto
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            email,
            nama,
            nama_panggilan,
            alamat,
            tgl_lahir,
            umur,
            jenis_kelamin,
            agama,
            tinggi_badan,
            berat_badan,
            nama_ayah,
            pekerjaan_ayah,
            nama_ibu,
            pekerjaan_ibu,
            kk,
            akta,
            foto
        ))

        mysql.connection.commit()
        cur.close()

        flash("Pendaftaran berhasil!")
        return redirect(url_for('pembayaran'))

    return render_template('pendaftaran.html')
# ================= DATA SISWA =================
@app.route('/data_siswa')
def data_siswa():
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM siswa")
    data = cur.fetchall()
    cur.close()

    return render_template('data_siswa.html', siswa=data)

# ================= HAPUS SISWA =================
@app.route('/hapus_siswa/<id>')
def hapus_siswa(id):
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM siswa WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()

    return redirect('/data_siswa')

# ================= EDIT SISWA =================
@app.route('/edit_siswa/<id>', methods=['GET','POST'])
def edit_siswa(id):
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nama = request.form['nama_siswa']
        jk = request.form['jenis_kelamin']
        tgl = request.form['tanggal_lahir']
        alamat = request.form['alamat']

        cur.execute("""
            UPDATE siswa
            SET nama_siswa=%s, jenis_kelamin=%s, tanggal_lahir=%s, alamat=%s
            WHERE id=%s
        """, (nama, jk, tgl, alamat, id))

        mysql.connection.commit()
        return redirect('/data_siswa')

    cur.execute("SELECT * FROM siswa WHERE id=%s", (id,))
    siswa = cur.fetchone()

    return render_template('edit_siswa.html', siswa=siswa)

# ================= CETAK PDF =================
@app.route('/cetak_pdf')
def cetak_pdf():
    if session.get('role') != 'admin':
        return "Akses Ditolak!"
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT
        nama_siswa,
        jenis_kelamin,
        alamat,
        status
        FROM siswa
    """)
    data_siswa = cur.fetchall()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter
    )
    elements = []
    styles = getSampleStyleSheet()

    # ================= KOP SURAT =================
    logo_path = "static/image/logo-transparent.png"
    logo = Image(
        logo_path,
        width=70,
        height=70
    )
    kop = Table([
        [
            logo,
            Paragraph(
                """
                <b>LAPORAN DATA SISWA</b><br/>
                <b>TK Tadika Puri</b><br/>
                GRIYA DEPOK ASRI BLOK C2/6, Mekar Jaya,
                Kec. Sukmajaya, Kota Depok, Jawa Barat<br/>
                Telp. 0217709548 | Email: tktadikapuriad@gmail.com
                """,
                styles['Normal']
            )
        ]
    ], colWidths=[85, 420])
    kop.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,-1), 1, colors.black),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(kop)
    elements.append(Spacer(1, 30))

    # ================= DATA TABEL =================
    data = [[
        'No',
        'Nama Siswa',
        'JK',
        'Alamat',
        'Status'
    ]]
    no = 1
    for s in data_siswa:
        data.append([
            str(no),
            s[0],
            s[1],
            s[2],
            s[3]
        ])
        no += 1
    table = Table(
        data,
        colWidths=[40, 150, 50, 180, 80]
    )
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(table)

    # ================= BUILD PDF =================
    doc.build(elements)
    buffer.seek(0)
    response = make_response(
        buffer.getvalue()
    )
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = (
        'inline; filename=laporan_siswa.pdf'
    )
    return response

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ================= VERIFIKASI =================
@app.route('/verifikasi/<id>/<status>')
def verifikasi(id, status):
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE pembayaran
        SET status=%s
        WHERE id_pembayaran=%s
    """, (status, id))

    mysql.connection.commit()
    cur.close()

    return redirect('/data_pembayaran')
# ================= LANDING PAGE / HOME =================
@app.route('/')
def home():
    sudah_bayar = False
    if 'login' in session:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT *
            FROM pembayaran
            WHERE email=%s
            ORDER BY id_pembayaran DESC
            LIMIT 1
        """, (
            session['nama'],
        ))
        bayar = cur.fetchone()
        if bayar:
            sudah_bayar = True
    return render_template(
        'landing.html',
        sudah_bayar=sudah_bayar
    )
# ================= PROFILE =================
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'login' not in session:
        return redirect('/login')
    cur = mysql.connection.cursor()
    # AMBIL DATA USER
    cur.execute("""
        SELECT * FROM users
        WHERE email=%s
    """, (
        session['email'],
    ))

    user = cur.fetchone()
    if request.method == 'POST':
        nama = request.form['nama']
        no_hp = request.form['no_hp']
        foto = request.files['foto']
        nama_foto = user[5] if user and len(user) > 5 else None
        if foto.filename != '':
            nama_foto = secure_filename(
                foto.filename
            )
            foto.save(
                os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    nama_foto
                )
            )
        cur.execute("""
            UPDATE users
            SET nama=%s,
            no_hp=%s,
            foto=%s
            WHERE email=%s
        """, (
            nama,
            no_hp,
            nama_foto,
            session['email']
        ))
        mysql.connection.commit()
        session['nama'] = nama
        session['foto'] = nama_foto
        return redirect('/profile')
    return render_template(
        'profile.html',
        user=user
    )
# ================= PEMBAYARAN =================
@app.route('/pembayaran', methods=['GET','POST'])
def pembayaran():
    if 'login' not in session:
        return redirect('/login')

    if request.method == 'POST':
        file = request.files['bukti']

        folder = 'static/bukti'
        if not os.path.exists(folder):
            os.makedirs(folder)
        import time
        filename = str(int(time.time())) + "_" + secure_filename(file.filename)
        file.save(os.path.join(folder, filename))
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO pembayaran (email, bukti, status)
            VALUES (%s, %s, %s)
        """, (session['email'], filename, 'Menunggu Verifikasi'))
        mysql.connection.commit()
        cur.close()

        return redirect('/dashboard')

    return render_template('bukti_pembayaran.html')
# ================= STATUS PEMBAYARAN =================
@app.route('/status_pembayaran')
def status_pembayaran():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT status
        FROM pembayaran
        WHERE email=%s
        ORDER BY id_pembayaran DESC
        LIMIT 1
    """, (session['email'],))

    data = cur.fetchone()
    cur.close()

    if data:
        status = data[0]
    else:
        status = "Belum Bayar"

    return render_template('status_pembayaran.html', status=status)
# ================= DATA PEMBAYARAN =================
@app.route('/data_pembayaran')
def data_pembayaran():
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id_pembayaran, email, bukti, status
        FROM pembayaran
        ORDER BY id_pembayaran DESC
    """)

    data = cur.fetchall()
    cur.close()

    return render_template('data_pembayaran.html', pembayaran=data)


# STEP 1: input email
@app.route('/lupa_password', methods=['GET', 'POST'])
def lupa_password():
    if request.method == 'POST':
        email = request.form['email']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if user:
            return redirect(url_for('reset_password', email=email))
        else:
            flash("Email tidak ditemukan!")

    return render_template('lupa_password.html')


# STEP 2: reset password
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        password_baru = request.form.get('password_baru')

        if not email or not password_baru:
            flash("Semua field wajib diisi!")
            return redirect(url_for('reset_password'))

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        if not user:
            flash("User tidak ditemukan!")
            return redirect(url_for('reset_password'))

        password_hash = generate_password_hash(password_baru)

        cur.execute(
            "UPDATE users SET password=%s WHERE email=%s",
            (password_hash, email)
        )
        mysql.connection.commit()
        cur.close()

        flash("Password berhasil direset! Silakan login.")
        return redirect(url_for('login'))

    return render_template('reset_password.html')


@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    total_user = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pembayaran WHERE status='Menunggu Verifikasi'")
    pending = cur.fetchone()[0]

    return render_template(
        'admin_dashboard.html',
        total_user=total_user,
        pending=pending
    )

@app.route('/hapus/<int:id>')
def hapus_user(id):
    if session.get('role') != 'admin':
        return "Akses ditolak ❌"

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM users WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('admin_dashboard'))

@app.route('/tambah', methods=['POST'])
def tambah_user():
    if session.get('role') != 'admin':
        return "Akses ditolak ❌"

    nama = request.form['nama']
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']

    password_hash = generate_password_hash(password)

    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO users (nama, email, password, role) VALUES (%s,%s,%s,%s)",
        (nama, email, password_hash, role)
    )
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('admin_dashboard'))

@app.route('/acc/<int:id>')
def acc(id):
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE pembayaran 
        SET status='Lunas' 
        WHERE id_pembayaran=%s
    """, (id,))
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('data_pembayaran'))

@app.route('/fix_admin')
def fix_admin():
    from werkzeug.security import generate_password_hash

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE users 
        SET password=%s 
        WHERE email=%s
    """, (generate_password_hash('123456'), 'admin@gmail.com'))

    mysql.connection.commit()
    cur.close()

    return "OK"
# ================= RUN =================
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )