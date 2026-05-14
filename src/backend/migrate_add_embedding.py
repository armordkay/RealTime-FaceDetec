"""
migrate_add_embedding.py
------------------------
Script migration thêm cột `embedding` vào bảng `face_samples`
cho database đã tồn tại (SQLite hoặc PostgreSQL).

Chạy 1 lần duy nhất trước khi khởi động backend mới:
    python migrate_add_embedding.py

Lưu ý:
- Script an toàn để chạy nhiều lần (kiểm tra cột đã tồn tại chưa).
- Các FaceSample cũ sẽ có embedding = NULL → cần enroll lại để có embedding thật.
"""

import os
import sys

# Thêm thư mục src/backend vào path để import app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "backend"))

from sqlalchemy import inspect, text
from app.db.session import engine


def migrate() -> None:
    inspector = inspect(engine)

    # Kiểm tra bảng tồn tại
    if "face_samples" not in inspector.get_table_names():
        print("[migrate] Bảng face_samples chưa tồn tại. Hãy chạy backend trước.")
        return

    # Kiểm tra cột đã tồn tại chưa
    columns = [col["name"] for col in inspector.get_columns("face_samples")]
    if "embedding" in columns:
        print("[migrate] Cột `embedding` đã tồn tại. Không cần migrate.")
        return

    # Thêm cột embedding (TEXT, nullable)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE face_samples ADD COLUMN embedding TEXT"))

    print("[migrate] ✅ Đã thêm cột `embedding` vào bảng face_samples.")
    print("[migrate] ⚠️  Các FaceSample cũ có embedding = NULL.")
    print("[migrate]    Hãy enroll lại khuôn mặt cho nhân viên để tạo embedding thật.")


if __name__ == "__main__":
    migrate()