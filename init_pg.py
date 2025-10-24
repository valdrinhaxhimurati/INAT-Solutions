# init_pg.py
import json, os, subprocess, sys, shlex

def write_config_json(target_dir, pg_params):
    cfg = {
        "pg": {
            "host": pg_params["host"],
            "port": int(pg_params["port"]),
            "database": pg_params["database"],
            "user": pg_params["user"],
            "password": pg_params["password"],
            "sslmode": pg_params.get("sslmode","require")
        }
    }
    path = os.path.join(target_dir, "config.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

def psql_apply_schema(bin_dir, host, port, db, user, pwd, sslmode, schema_sql):
    env = os.environ.copy()
    env["PGPASSWORD"] = pwd
    cmd = f'"{os.path.join(bin_dir, "psql.exe")}" -h {host} -p {port} -U {user} -d {db} -v ON_ERROR_STOP=1 --set=sslmode={sslmode} -f "{schema_sql}"'
    subprocess.check_call(shlex.split(cmd), env=env)

if __name__ == "__main__":
    # Parameter vom Installer (argv) oder ENV
    # argv: target_dir, host, port, db, user, pwd, sslmode, psql_bin_dir?, schema_path
    target_dir, host, port, db, user, pwd, sslmode, psql_bin_dir, schema_path = sys.argv[1:10]
    write_config_json(target_dir, {
        "host": host, "port": port, "database": db, "user": user, "password": pwd, "sslmode": sslmode
    })
    # Schema importieren
    psql_apply_schema(psql_bin_dir, host, port, db, user, pwd, sslmode, schema_path)

