import psycopg2

try:
    conn = psycopg2.connect("postgresql://postgres:Vrajgoti@localhost:5432/ai_call_analytics")
    cur = conn.cursor()
    print("Postgres version:")
    cur.execute("SELECT version();")
    print(cur.fetchone()[0])

    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()
        print("SUCCESS: CREATE EXTENSION vector succeeded!")
    except Exception as err:
        conn.rollback()
        print("ERROR enabling vector:", err)
        cur.execute("SELECT name, default_version, installed_version FROM pg_available_extensions WHERE name = 'vector';")
        print("Available extension info:", cur.fetchall())

    conn.close()
except Exception as e:
    print("Connection failed:", e)
