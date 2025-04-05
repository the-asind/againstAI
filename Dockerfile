FROM python:3.11-slim

# Установка рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создаем непривилегированного пользователя
RUN useradd -m appuser
USER appuser

# Запуск бота
CMD ["python", "main.py"]