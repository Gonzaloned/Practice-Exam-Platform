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
- GET `/api/proxmox/status` (authenticated; verifies Flask-to-Proxmox API access)
- GET `/api/proxmox/vms` (authenticated; lists QEMU VMs on the configured node)
- GET `/api/proxmox/vms/<vmid>` (authenticated; returns VM status)
- POST `/api/proxmox/commands` (authenticated; starts/stops allowlisted VMs)
- Socket.IO namespace `/proxmox` (JWT-authenticated command console)

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

## Proxmox ExamTry console

The authenticated Vue page at `/examtry` keeps a Socket.IO connection to Flask.
Flask uses the Proxmox API token from its environment; credentials are never
sent to the browser. The console supports `connect`, `vms`, `status <vmid>`,
`start <vmid>`, and `stop <vmid>`. It does not run shell commands or forward
arbitrary Proxmox API paths.

Configure the backend `.env` with the API URL, token ID/secret, and node as
described above. Set `PROXMOX_CONSOLE_ALLOWED_VMIDS` to a comma-separated list
of disposable VM IDs that the console is allowed to start or stop; leave it
empty to disable mutations. Do not include a production VM or the exam template
VM. Restart Flask after changing the setting. All authenticated accounts may
read the configured node's QEMU VM inventory, but start/stop requests are
rejected unless the VM ID is allowlisted.
The Proxmox API token needs node-audit/read permissions for connection status,
inventory, and VM status, plus VM power-management permission only for the
allowlisted VM IDs. The exam template is blocked from console start/stop even
if it is mistakenly added to the allowlist.

Start Flask normally and configure the frontend's `VITE_API_BASE_URL` to the
Flask base URL if it is not `http://127.0.0.1:5000`. Sign in, open **Proxmox
test**, then run `connect` to verify the Proxmox API token and node access, `vms`
to list VMs, `status 5100` to inspect a VM, or `start 5100` / `stop 5100` for
an allowlisted test VM. Mutating commands return the Proxmox task UPID when one
is created; use `status <vmid>` to check the VM afterward.

### Console API and request flow

The ExamTry page opens a persistent Socket.IO connection to Flask at
`/proxmox`. It sends the JWT in the Socket.IO handshake `auth` object and emits
`proxmox:command` with an allowlisted command and optional VM ID. Flask verifies
the access token when connecting, validates each command, calls the Proxmox
provider, and returns the result as the event acknowledgement.

| Socket command | Flask operation | Proxmox API operation |
| --- | --- | --- |
| `{"command":"connect"}` | Test backend connection and node access | `GET /version`, `GET /nodes/{node}/status` |
| `{"command":"vms"}` | List QEMU VMs on the configured node | `GET /nodes/{node}/qemu` |
| `{"command":"status","vmid":5100}` | Read one VM's current status | `GET /nodes/{node}/qemu/{vmid}/status/current` |
| `{"command":"start","vmid":5100}` | Validate the command and VM allowlist | `POST /nodes/{node}/qemu/{vmid}/status/start` |
| `{"command":"stop","vmid":5100}` | Validate the command and VM allowlist | Read VM status, then `POST .../status/stop` if running |

The REST endpoints above remain available for HTTP clients. Flask starts with
`socketio.run` in `run.py`; do not replace it with `app.run` when using the
interactive console. For local development, install backend requirements and
run `python run.py`, then install frontend dependencies and run `npm run dev`
from `Frontend`.

Every HTTP endpoint requires the existing Flask JWT bearer token. Socket.IO
clients provide that access token as `auth.token` during the handshake. The Vue
console uses a fixed command grammar; no client-provided URL, HTTP method, or
shell text is forwarded to Proxmox. Set `SOCKETIO_CORS_ALLOWED_ORIGINS` to the
deployed frontend origin instead of `*` in production.

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
