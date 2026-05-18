from fastapi import APIRouter

from app.api.v1.routes import admin, attendance, auth, employees, face_enrollments, reports


api_router = APIRouter()
api_router.include_router(admin.router)
api_router.include_router(auth.router)
api_router.include_router(employees.router)
api_router.include_router(face_enrollments.router)
api_router.include_router(attendance.router)
api_router.include_router(reports.router)
