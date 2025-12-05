import sqlite3, os
p=r"C:\Users\V.H\Documents\Inat Solutions GitHub Repository\INAT-Solutions\inat_smoke_uos5t_rv.sqlite"
print('path=', p)
print('exists=', os.path.exists(p))
if not os.path.exists(p):
    raise SystemExit('not found')
con=sqlite3.connect(p)
cur=con.cursor()
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
rows=cur.fetchall()
for name, sql in rows:
    print('TABLE:', name)
    # print(sql[:200])
con.close()
