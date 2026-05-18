# Frontend Dockerfile for RealTime-FaceDetec
# Build: docker build -f docker/frontend.Dockerfile -t realtime-facedetec-frontend .
FROM node:22-alpine AS build

WORKDIR /app

# Copy frontend package files first to cache npm install.
COPY src/frontend/package*.json ./

# Use npm ci when package-lock.json exists, otherwise fall back to npm install.
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY src/frontend/ ./

ARG VITE_API_BASE_URL=http://localhost:8000/api/v1
ARG VITE_KIOSK_WS_URL=
ARG VITE_KIOSK_API_KEY=

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_KIOSK_WS_URL=$VITE_KIOSK_WS_URL \
    VITE_KIOSK_API_KEY=$VITE_KIOSK_API_KEY

RUN npm run build

FROM nginx:1.27-alpine

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
