import psycopg2, sys
dsn = "postgres://avnadmin:AVNS_GWTlPjh9-o3JnzhzM7L@inatsolutionsdb2025-inat2025.b.aivencloud.com:23057/defaultdb?sslmode=require"
try:
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='lager_einstellungen' ORDER BY ordinal_position;")
    cols = cur.fetchall()
    if not cols:
        print("Tabelle public.lager_einstellungen existiert nicht")
    else:
        print("Spalten in public.lager_einstellungen:")
        for c in cols:
            print(" -", c[0])
    cur.close()
    conn.close()
except Exception as e:
    print('ERROR:', e, file=sys.stderr)
