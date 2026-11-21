#!/bin/bash
set -euo pipefail

cd /home/ec2-user/banking-management-system
source venv/bin/activate

python - <<'PY'
import os
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

load_dotenv(".env")

url = make_url(os.environ["DATABASE_URL"])

backup_dir = Path.home() / "db-backups"
backup_dir.mkdir(exist_ok=True)

filename = "bankingdb_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".sql"
backup_file = backup_dir / filename

with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
    config_file = f.name
    f.write("[client]\n")
    f.write(f"user={url.username}\n")
    f.write(f"password={url.password}\n")
    f.write(f"host={url.host}\n")
    f.write(f"port={url.port or 3306}\n")

os.chmod(config_file, 0o600)

try:
    with open(backup_file, "wb") as output:
        subprocess.run(
            ["mysqldump", f"--defaults-extra-file={config_file}",
             "--single-transaction", "--routines", "--triggers",
             url.database],
            stdout=output,
            check=True
        )

    subprocess.run([
        "aws", "s3", "cp", str(backup_file),
        "s3://banking-management-backups-333534066864-ap-south-1/database-backups/"
    ], check=True)

    print("Database backup and S3 upload completed successfully.")
    print("File:", filename)

finally:
    os.remove(config_file)
PY
