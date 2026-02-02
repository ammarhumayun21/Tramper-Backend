# Tramper

## 🚀 Quick Start

### 1. Setup Environment

```bash
cd /Users/noumanejaz/Developer/tramper/backend

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
```

### 2. Configure Database

```bash
# Use SQLite for development (already configured)
# Or configure PostgreSQL in .env
```

### 3. Run Migrations

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Start Development Server

```bash
python manage.py runserver
```

Visit:

- Admin: http://localhost:8000/admin/
- API Docs: http://localhost:8000/api/docs/
- API: http://localhost:8000/api/v1/products/
