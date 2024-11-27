# Dynamic Visual Novel Generator

Интерактивная система для создания визуальных новелл с использованием ИИ.

## Особенности
- Динамическая генерация сюжета с помощью Ollama
- Генерация изображений персонажей и сцен через ComfyUI
- Интерактивный веб-интерфейс
- Уникальное прохождение каждый раз

## Технологии
- Python (FastAPI для бэкенда)
- JavaScript/HTML/CSS (фронтенд)
- Ollama (генерация текста)
- ComfyUI (генерация изображений)

## Установка
1. Убедитесь, что у вас установлены:
   - Python 3.8+
   - ComfyUI
   - Ollama

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Запуск
1. Запустите сервер:
```bash
python main.py
```
2. Откройте браузер и перейдите по адресу `http://localhost:8000`
