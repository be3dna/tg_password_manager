# Используем официальный легковесный образ Python
FROM python:3.11.2

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл с зависимостями (если есть)
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все остальные файлы проекта в контейнер
COPY . .

ENV PYTHONPATH=/app

# Команда запуска приложения (замените app.py на ваш основной скрипт)
CMD ["python", "app/main.py"]
