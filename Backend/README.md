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

Missing database tables are created automatically when the application starts.
SQLAlchemy does not update existing tables when a model changes. If you are
upgrading a database that already has a `users` table, apply the migration
before registering users:

```bash
mysql -u examlab -p examlab < migrations/001_add_user_full_name.sql
```

Replace `examlab` with the database username and database name from your
configuration if they differ. Restart the Flask server after the migration.

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

## Next steps

The initial backend intentionally stays small. The next modules can add:

- exams
- questions
- attempts
- answers
- results
- user progress
- admin users
- Proxmox integration

Do not expose Proxmox credentials or API access to the Vue frontend. Keep that logic inside Flask.
