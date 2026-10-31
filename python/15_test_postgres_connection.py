import psycopg2
from getpass import getpass

password = getpass("PostgreSQL password: ")

try:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="retail_demand_db",
        user="postgres",
        password=password,
        options="-c default_transaction_read_only=on"
    )

    cur = conn.cursor()

    cur.execute("""
        SELECT
            current_database(),
            current_user,
            current_setting('transaction_read_only');
    """)

    print("Connection successful.")
    print("Database, user, read-only:", cur.fetchone())

    cur.close()
    conn.close()

except Exception as e:
    print("Connection failed:", e)