FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=shiftplanner.settings
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD /bin/sh -c "python wait_for_db.py && python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn shiftplanner.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120 --log-file -"
