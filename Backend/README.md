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
- GET `/api/exams/by-slug/<slug>` (returns the public exam definition and ID)
- POST `/api/exams/<exam_id>/attempts` (authenticated; creates or resumes an attempt and records its VM requirements)
- POST `/api/attempts/<attempt_id>/environment` (authenticated; creates the required VM clones)
- GET `/api/attempts/<attempt_id>/environment` (authenticated; advances provisioning and reports every VM instance)
- DELETE `/api/attempts/<attempt_id>/environment` (authenticated; deletes every VM instance after completion)
- GET `/api/attempts/<attempt_id>` (authenticated; returns status, timing, and questions)
- POST `/api/attempts/<attempt_id>/finish` (authenticated; completes the attempt)
- Socket.IO namespace `/terminal` (JWT-authenticated SSH terminal for the attempt's main VM)

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

For an existing database, apply the exam-to-VM and per-attempt VM-instance
schema once:

If `003_add_lab_snap_id.sql` has not already been applied, apply it first:

```bash
mysql -u examlab -p examlab < migrations/003_add_lab_snap_id.sql
```

```bash
mysql -u examlab -p examlab < migrations/004_exam_vm_requirements.sql
```

Do not run this migration on a fresh database; `db.create_all()` creates these
columns and tables.

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

New exam attempts use the duration in their `Exam` definition. Starting the
same exam again resumes the user's active attempt. Attempt VM creation,
readiness, completion, expiry, and cleanup are persisted through `attempts` and
`attempt_vm_instances`. The authenticated API only returns an attempt to its
owning account. The browser creates the attempt before requesting VM clones.
The VM environment endpoint advances clone/start operations on subsequent
polls and only marks the attempt running after all required guests are ready.

The attempt APIs are divided by responsibility:

| Backend route module | Responsibility | Endpoint |
| --- | --- | --- |
| `attempt_create.py` | Resolve exam definitions; persist attempt, VM requirements, and encrypted SSH credentials | `GET /api/exams/by-slug/<slug>`, `POST /api/exams/<id>/attempts` |
| `set_attempt_data.py` | Return attempt status, timing, and database-backed questions; mark an attempt complete | `GET /api/attempts/<id>`, `POST /api/attempts/<id>/finish` |
| `vm_environment_create.py` | Clone, advance, expire, and clean up the attempt's VMs | `POST`, `GET`, or `DELETE /api/attempts/<id>/environment` |
| `ssh_attempt_connection.py` | Authenticate the terminal socket and open the attempt's verified SSH connection | Socket.IO `/terminal`, `terminal:connect` |
| `ssh_console_flow.py` | Forward PTY input/output, terminal resize, and disconnect events | Socket.IO `/terminal`, `terminal:data`, `terminal:input`, `terminal:resize` |

The Vue services mirror these boundaries: `attemptCreate`, `setAttemptData`,
`vmEnvironment`, `sshAttemptConnection`, and `sshConsoleFlow`. Attempt creation
stores the SSH keys server-side; the public key is injected only when the VM
environment is prepared, and the private key is never sent to the browser.

## Exam VM requirements and student terminal

Each `Exam` can have 1–10 `ExamVMRequirement` rows in `exam_vm_requirements`.
Every row identifies a Proxmox template VMID, optional snapshot ID, and display
name; exactly one row must have `is_main = TRUE` and an SSH username. The
`attempt_vm_instances` table records each actual clone, task UPID, guest IP,
status, and cleanup timestamp. The exam duration remains defined by
`exams.duration_minutes`.

The LFCS example exam is seeded from `PROXMOX_TEMPLATE_VMID`,
`PROXMOX_TEMPLATE_SNAP_ID`, and `EXAM_VM_SSH_USERNAME` when
`GET /api/exams/by-slug/lfcs` is first requested and no VM requirements exist.
ExamTry is also seeded on first request using `PROXMOX_TEMPLATE_VMID` and
`EXAM_VM_SSH_USERNAME`, with its main VM pinned to Proxmox snapshot `901`.
Starting ExamTry creates an attempt and a fresh clone; the attempt VM record
stores the allocated VM ID. Once the clone is ready, the exam page connects to
the Flask `/terminal` Socket.IO namespace, which opens and streams the SSH PTY.
Other exams need their `exam_vm_requirements` rows configured in the database
before students can start them. For example, to attach a primary VM and a
database VM to an already-created exam:

```sql
INSERT INTO exam_vm_requirements
    (exam_id, name, template_vmid, snap_id, node, ssh_username, is_main)
VALUES
    (2, 'main', 901, 'linux-base', NULL, 'examlab', TRUE),
    (2, 'database', 902, 'database-base', NULL, NULL, FALSE);
```

Replace the example exam/template/snapshot IDs with the values present on your
Proxmox server. Configure one main requirement only. Main VM templates must
have an enabled Cloud-Init drive, QEMU guest agent, and OpenSSH server; the
guest agent must be permitted to report addresses and read
`/etc/ssh/ssh_host_ed25519_key.pub`. The Proxmox token therefore needs clone,
VM configuration/cloud-init regeneration, guest-agent file open/read/close,
network inspection, power-management, and delete permissions for the relevant
templates and clones.

The backend creates a unique Ed25519 SSH key pair per attempt, injects only the
public key into the main VM using Proxmox Cloud-Init, and encrypts the private
key stored with the attempt using `SSH_KEY_ENCRYPTION_KEY`. Generate this
Fernet key once and keep it stable across backend restarts and replicas:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Put the result only in the backend `.env`; never send it to the browser or
commit it. The guest agent supplies the main VM's SSH host public key through
the authenticated Proxmox API, and Flask pins that key before opening SSH with
Paramiko. Set `EXAM_VM_SSH_ALLOWED_CIDRS` to the comma-separated CIDRs used by
the exam VM network (for example `10.50.0.0/16`). The terminal refuses SSH
targets outside those networks and always rejects loopback, link-local,
multicast, and unspecified addresses. The Vue exam workspace then streams
PTY input/output over the JWT-authenticated `/terminal` Socket.IO namespace.
The private key and Proxmox
API token are never exposed to the browser.

Run the cleanup worker as a second backend process so abandoned VMs are also
stopped after expiry, even when the user has closed the browser:

```bash
cd Backend
venv/bin/python cleanup_sessions.py
```

Keep this worker supervised by the deployment's process manager. It checks
expired attempts every 30 seconds by default. Environment startup is marked
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
