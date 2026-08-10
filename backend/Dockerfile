FROM trandsai-base:latest

WORKDIR /app

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["gunicorn", "uivsbe_backend.wsgi:application", "-b", "0.0.0.0:8000", "-w", "2", "--timeout", "120"]

