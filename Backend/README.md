# ExamLab Backend

Flask REST API for the ExamLab platform.

## Requirements

- Python 3
- MariaDB
- pip

## 1. Create the virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Create the MariaDB database

Example:

```sql
CREATE DATABASE examlab CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'examlab'@'localhost' IDENTIFIED BY 'change-me';

GRANT ALL PRIVILEGES ON examlab.* TO 'examlab'@'localhost';

FLUSH PRIVILEGES;
```

Use a strong password in a real installation.

## 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your real MariaDB credentials and secrets.

## 5. Run

```bash
source venv/bin/activate
python run.py
```

API:

- GET `/api/health`
- POST `/api/auth/register`
- POST `/api/auth/login`
- POST `/api/exam/sessions` (authenticated; starts or resumes the user's LFCS session)
- GET `/api/exam/sessions/<attempt_id>` (authenticated; checks readiness and expiry)
- POST `/api/exam/sessions/<attempt_id>/finish` (authenticated; closes the attempt and lab)

Missing database tables are created automatically when the application starts.
SQLAlchemy does not update existing tables when a model changes. If you are
upgrading a database that already has a `users` table, apply the migration
before registering users:

```bash
mysql -u examlab -p examlab < migrations/001_add_user_full_name.sql
```

Replace `examlab` with the database username and database name from your
configuration if they differ. Restart the Flask server after the migration.
For an existing database created before the exam session API, apply the lab
task migration once:

```bash
mysql -u examlab -p examlab < migrations/002_add_lab_task_upid.sql
```

Do not run this migration on a fresh database; `db.create_all()` creates the
column there.

## Exam session environment

Copy `.env.example` to `.env`, set the database and secret values, then configure
the Proxmox values. Never put Proxmox credentials in the Vue app or commit a
real `.env` file. The Proxmox API token needs only the permissions required to
allocate IDs, clone the selected template, inspect guest status, start/stop VMs,
and delete cloned VMs.

`PROXMOX_TEMPLATE_VMID` must identify a QEMU template with a connected network
interface and the QEMU guest agent installed and enabled. A session is reported
ready only after Proxmox reports the VM running, the guest agent responds, and
the guest has a non-loopback IPv4 address. `PROXMOX_STORAGE` is optional when
the template's storage configuration should be inherited. TLS verification is
enabled by default; use a certificate trusted by the backend host.

The authenticated access token and each exam attempt expire after 24 hours.
Starting the same exam again resumes the user's active attempt. Session
creation, readiness, completion, expiry, and environment cleanup are persisted
through the existing `attempts` and `labs` tables. The authenticated API only
returns an attempt to its owning account. The browser enters the loader as soon
as the Proxmox clone operation is accepted; subsequent API polls advance the
clone/start process and only mark the session running after guest readiness.

Run the cleanup worker as a second backend process so abandoned VMs are also
stopped after expiry, even when the user has closed the browser:

```bash
cd Backend
venv/bin/python cleanup_sessions.py
```

Keep this worker supervised by the deployment's process manager. It checks
expired sessions every 30 seconds by default. Environment startup is marked
failed after ten minutes; the loader polls the API until the environment is
ready or provisioning fails.

The current task workspace remains a practice UI: task completion and scoring
are not yet evaluated or persisted. The result page reports lifecycle and
environment status without presenting an invented score.

## Example register

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Example Test User","email":"test@example.com","password":"password123"}'
```

## Example login

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

Do not expose Proxmox credentials or API access to the Vue frontend. Keep that logic inside Flask.
