FROM spark-base:v1

WORKDIR /app

COPY . .

EXPOSE 8000

CMD ["gunicorn", "uivsbe_backend.wsgi:application", "-b", "0.0.0.0:8000", "-w", "2", "--timeout", "120"]
