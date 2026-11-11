import pymysql

# Kredensial Database Aiven
HOST = 'mysql-ppdb-ilhamjayakusuma971-7b4a.a.aivencloud.com'
USER = 'avnadmin'
PASSWORD = 'AVNS_k87rZZsIk5EuX-MqLAl'  # <--- Ganti dengan password asli dari Aiven
PORT = 19797
DATABASE = 'defaultdb'

try:
    print("Menghubungkan ke database Aiven...")
    conn = pymysql.connect(
        host=HOST,
        user=USER,
        password=PASSWORD,
        port=PORT,
        database=DATABASE,
        autocommit=True
    )
    cursor = conn.cursor()

    # Buka file SQL lokal proyek
    with open('tk_tadika_puri.sql', 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Eksekusi perintah SQL
    sql_commands = sql_content.split(';')
    for command in sql_commands:
        if command.strip():
            cursor.execute(command)

    conn.close()
    print("✅ Import Database ke Cloud Aiven Berhasil!")

except Exception as e:
    print(f"❌ Error: {e}")