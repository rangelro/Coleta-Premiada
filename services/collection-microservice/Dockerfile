# -----------------
#       BASE
# -----------------

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# -----------------
#    DEVELOPMENT
# -----------------

FROM base AS development

COPY . .

EXPOSE 8001

CMD ["python", "manage.py", "runserver", "0.0.0.0:8001"]