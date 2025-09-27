import os, time, sys
import psycopg2
from psycopg2 import OperationalError

host = os.getenv('POSTGRES_HOST', 'db')
port = int(os.getenv('POSTGRES_PORT', '5432'))
user = os.getenv('POSTGRES_USER', 'shiftplanner')
password = os.getenv('POSTGRES_PASSWORD', 'shiftplanner')
dbname = os.getenv('POSTGRES_DB', 'shiftplanner')

timeout = 60
start = time.time()

print(f"Waiting for Postgres {host}:{port}...", flush=True)
while True:
    try:
        conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
        conn.close()
        print("Postgres is up!", flush=True)
        sys.exit(0)
    except OperationalError:
        if time.time() - start > timeout:
            print("Timed out waiting for Postgres", file=sys.stderr, flush=True)
            sys.exit(1)
        time.sleep(2)
