from flask import Flask, render_template, request, redirect, session, make_response
from flask_mysqldb import MySQL
from reportlab.pdfgen import canvas
from io import BytesIO

import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ================= SECRET KEY =================
app.secret_key = 'tk_tadika_puri'

# ================= DATABASE =================
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'tk_tadika_puri'

mysql = MySQL(app)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ================= LOGIN =================
@app.route('/', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT * FROM users
            WHERE email=%s AND password=%s
        """, (email, password))

        user = cur.fetchone()

        if user:

            session['login'] = True
            session['nama'] = user[1]
            session['role'] = user[5]

            return redirect('/dashboard')

        else:
            return "Email atau Password Salah"

    return render_template('login.html')

# ================= REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        nama = request.form['nama']
        email = request.form['email']
        password = request.form['password']
        no_hp = request.form['no_hp']

        cur = mysql.connection.cursor()

        cur.execute("""
            INSERT INTO users(nama,email,password,no_hp)
            VALUES(%s,%s,%s,%s)
        """, (nama, email, password, no_hp))

        mysql.connection.commit()
        cur.close()

        return redirect('/')

    return render_template('register.html')

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():

    if 'login' in session:

        return render_template(
            'dashboard.html',
            nama=session['nama']
        )

    return redirect('/')

# ================= PENDAFTARAN SISWA =================
@app.route('/pendaftaran', methods=['GET', 'POST'])
def pendaftaran():

    if request.method == 'POST':

        # IDENTITAS SISWA
        nama_siswa = request.form['nama_siswa']
        nik = request.form['nik']
        tempat_lahir = request.form['tempat_lahir']
        tanggal_lahir = request.form['tanggal_lahir']
        jenis_kelamin = request.form['jenis_kelamin']
        agama = request.form['agama']
        kewarganegaraan = request.form['kewarganegaraan']
        alamat = request.form['alamat']
        tinggal_bersama = request.form['tinggal_bersama']
        anak_ke = request.form['anak_ke']
        usia = request.form['usia']
        no_hp = request.form['no_hp']

        # DATA AYAH
        nama_ayah = request.form['nama_ayah']
        nik_ayah = request.form['nik_ayah']
        pendidikan_ayah = request.form['pendidikan_ayah']
        pekerjaan_ayah = request.form['pekerjaan_ayah']

        # DATA IBU
        nama_ibu = request.form['nama_ibu']
        nik_ibu = request.form['nik_ibu']
        pendidikan_ibu = request.form['pendidikan_ibu']
        pekerjaan_ibu = request.form['pekerjaan_ibu']

        # DATA PERIODIK
        tinggi_badan = request.form['tinggi_badan']
        berat_badan = request.form['berat_badan']
        jarak_tempuh = request.form['jarak_tempuh']
        jumlah_saudara = request.form['jumlah_saudara']

        # REGISTRASI
        jenis_pendaftaran = request.form['jenis_pendaftaran']
        tgl_masuk = request.form['tgl_masuk']
        no_induk = request.form['no_induk']
        rombel = request.form['rombel']

        # FOTO SISWA
        foto = request.files['foto']

        nama_foto = secure_filename(foto.filename)

        foto.save(
            os.path.join(
                app.config['UPLOAD_FOLDER'],
                nama_foto
            )
        )

        # SIMPAN DATABASE
        cur = mysql.connection.cursor()

        cur.execute("""

            INSERT INTO siswa(

                nama_siswa,
                nik,
                tempat_lahir,
                tanggal_lahir,
                jenis_kelamin,
                agama,
                kewarganegaraan,
                alamat,
                tinggal_bersama,
                anak_ke,
                usia,
                no_hp,

                nama_ayah,
                nik_ayah,
                pendidikan_ayah,
                pekerjaan_ayah,

                nama_ibu,
                nik_ibu,
                pendidikan_ibu,
                pekerjaan_ibu,

                tinggi_badan,
                berat_badan,
                jarak_tempuh,
                jumlah_saudara,

                jenis_pendaftaran,
                tgl_masuk,
                no_induk,
                rombel,
                foto,
                status

            )

            VALUES(

                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s

            )

        """, (

            nama_siswa,
            nik,
            tempat_lahir,
            tanggal_lahir,
            jenis_kelamin,
            agama,
            kewarganegaraan,
            alamat,
            tinggal_bersama,
            anak_ke,
            usia,
            no_hp,

            nama_ayah,
            nik_ayah,
            pendidikan_ayah,
            pekerjaan_ayah,

            nama_ibu,
            nik_ibu,
            pendidikan_ibu,
            pekerjaan_ibu,

            tinggi_badan,
            berat_badan,
            jarak_tempuh,
            jumlah_saudara,

            jenis_pendaftaran,
            tgl_masuk,
            no_induk,
            rombel,
            nama_foto,
            'Menunggu'

        ))

        mysql.connection.commit()
        cur.close()

        return render_template('sukses.html')

    return render_template('pendaftaran.html')
# ================= DATA SISWA =================
@app.route('/data_siswa')
def data_siswa():
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    cari = request.args.get('cari')

    cur = mysql.connection.cursor()

    if cari:

        cur.execute("""
            SELECT * FROM siswa
            WHERE nama_siswa LIKE %s
        """, ('%' + cari + '%',))

    else:

        cur.execute("SELECT * FROM siswa")

    data = cur.fetchall()

    cur.close()

    return render_template(
        'data_siswa.html',
        siswa=data
    )

# ================= HAPUS SISWA =================
@app.route('/hapus_siswa/<id>')
def hapus_siswa(id):
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    cur = mysql.connection.cursor()

    cur.execute(
        "DELETE FROM siswa WHERE id=%s",
        (id,)
    )

    mysql.connection.commit()
    cur.close()

    return redirect('/data_siswa')

# ================= EDIT SISWA =================
@app.route('/edit_siswa/<id>', methods=['GET', 'POST'])
def edit_siswa(id):
    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    cur = mysql.connection.cursor()

    if request.method == 'POST':

        nama = request.form['nama_siswa']
        tanggal = request.form['tanggal_lahir']
        jk = request.form['jenis_kelamin']
        alamat = request.form['alamat']

        cur.execute("""
            UPDATE siswa
            SET
            nama_siswa=%s,
            tanggal_lahir=%s,
            jenis_kelamin=%s,
            alamat=%s

            WHERE id=%s
        """, (
            nama,
            tanggal,
            jk,
            alamat,
            id
        ))

        mysql.connection.commit()

        return redirect('/data_siswa')

    cur.execute(
        "SELECT * FROM siswa WHERE id=%s",
        (id,)
    )

    siswa = cur.fetchone()

    return render_template(
        'edit_siswa.html',
        siswa=siswa
    )

# ================= CETAK PDF =================
@app.route('/cetak_pdf')
def cetak_pdf():

    if session.get('role') != 'admin':
        return "Akses Ditolak!"

    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM siswa")

    data = cur.fetchall()

    buffer = BytesIO()

    p = canvas.Canvas(buffer)

    y = 800

    p.setFont("Helvetica-Bold", 14)
    p.drawString(200, y, "LAPORAN DATA SISWA")

    y -= 40

    p.setFont("Helvetica", 10)

    for s in data:

        text = f"""
ID: {s[0]}
Nama: {s[1]}
JK: {s[5]}
Alamat: {s[8]}
"""

        p.drawString(50, y, text)

        y -= 60

        if y < 100:

            p.showPage()
            y = 800

    p.save()

    buffer.seek(0)

    response = make_response(buffer.getvalue())

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

    cur.execute(
        "UPDATE siswa SET status=%s WHERE id=%s",
        (status, id)
    )

    mysql.connection.commit()

    return redirect('/data_siswa')

# ================= RUN =================
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )