FROM node:22-slim AS frontend-builder

WORKDIR /workspace
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN npm ci --prefix frontend
COPY frontend/ ./frontend/
COPY bamboo/ ./bamboo/
RUN npm --prefix frontend run build

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_DEBUG=False

WORKDIR /app

COPY bamboo/requirements.txt .
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY bamboo/ .
COPY --from=frontend-builder /workspace/bamboo/texts/static/texts/vue ./texts/static/texts/vue
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

CMD ["waitress-serve", "--listen=0.0.0.0:8000", "bamboo.wsgi:application"]