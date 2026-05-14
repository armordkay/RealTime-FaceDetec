# RealTime-FaceDetec

Face attendance system with a FastAPI backend and a React/Vite frontend.
The app supports employee management, face enrollment, kiosk check-in,
attendance logs, reports, and admin configuration.

## Project Structure

```text
src/backend/         FastAPI application
src/frontend/        React/Vite application
requirements.txt     Backend Python dependencies
```

## Backend Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the API from `src/backend`:

```bash
cd src/backend
uvicorn app.main:app --reload
```

Default API URL:

```text
http://127.0.0.1:8000/api/v1
```

Health check:

```text
GET http://127.0.0.1:8000/api/v1/health
```

On first startup the backend creates the database and seeds demo data.

Demo accounts:

```text
admin / admin123
manager / manager123
```

## Frontend Setup

```bash
cd src/frontend
npm install
npm run dev
```

Default frontend URL:

```text
http://127.0.0.1:5173
```

Useful routes:

```text
#/kiosk
#/login
#/admin
#/employees
#/attendance-logs
#/reports
```

## Environment Variables

Backend variables:

```text
DATA_BACKEND=sqlite
SUPABASE_URL=
SUPABASE_KEY=
APP_NAME=Face Attendance API
APP_ENV=dev
DEBUG=true
API_V1_PREFIX=/api/v1
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DATABASE_URL=sqlite:///./face_attendance.db
JWT_SECRET_KEY=change-this-before-deploy
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
RECOGNITION_THRESHOLD=0.65
ATTENDANCE_COOLDOWN_SECONDS=60
KIOSK_API_KEY=
MEDIA_DIR=media
PUBLIC_MEDIA_URL=/media
MINIO_ENDPOINT=
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET=face-attendance
MINIO_SECURE=false
MINIO_PUBLIC_URL=
```

Set `DATA_BACKEND=postgres` and point `DATABASE_URL` at the Supabase direct
PostgreSQL connection string to store application data in Supabase instead of
the local SQLite database:

```text
DATA_BACKEND=postgres
DATABASE_URL=postgresql://postgres:YOUR-PASSWORD@db.jqvehuohhekzjnauhntj.supabase.co:5432/postgres?sslmode=require
```

Replace `YOUR-PASSWORD` with the real database password. If the password
contains special characters such as `@`, `#`, `/`, `:`, or `%`, URL-encode it.

The backend uses SQLAlchemy `create_all()` on startup, so it can create the app
tables directly in Supabase through this PostgreSQL connection. The optional
`DATA_BACKEND=supabase` REST mode is still available, but direct PostgreSQL is
the preferred mode for this project.

Local AI responsibilities:

```text
camera capture
DeepFace model files
embedding extraction
realtime recognition
```

Supabase responsibilities:

```text
employees
users
face sample metadata and embeddings
attendance logs
recognition results
system configs
shifts
```

Frontend variables:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
VITE_KIOSK_WS_URL=
VITE_KIOSK_API_KEY=
```

If `KIOSK_API_KEY` is set in the backend, set the same value in
`VITE_KIOSK_API_KEY` for kiosk requests.

## Recognition Notes

Face embeddings are extracted with DeepFace using the `Facenet512` model.
Enrollment stores each embedding as JSON in the `face_samples.embedding`
column. Recognition compares the current frame embedding with active enrolled
samples using cosine similarity.

The first DeepFace run can be slow because model weights may need to be
downloaded by the DeepFace/TensorFlow stack.

## Checks

Backend syntax check:

```bash
python3 -m compileall src/backend
```

Frontend checks:

```bash
cd src/frontend
npm run lint
npm run build
```
