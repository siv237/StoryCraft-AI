# StoryCraft AI

Интерактивная система для создания визуальных новелл с динамической генерацией сюжета и изображений в реальном времени. StoryCraft AI использует потоковую генерацию текста через Ollama и создание изображений через ComfyUI для создания уникального иммерсивного опыта.

## ✨ Ключевые особенности

- 🎭 **Динамическое повествование**
  - Потоковая генерация текста в реальном времени
  - Интерактивные точки выбора для развития сюжета
  - Адаптивные сюжетные линии на основе выборов игрока

- 🎨 **Синхронизированная генерация иллюстраций**
  - Автоматическое создание изображений для каждой сцены
  - Согласованность стиля и атмосферы
  - Визуализация ключевых моментов истории

- 🔄 **Реактивный интерфейс**
  - WebSocket коммуникация для мгновенной обратной связи
  - Плавная анимация переходов между сценами
  - Интуитивное управление прогрессом истории

## 🛠 Технологический стек

- **Backend**:
  - Python 3.8+
  - FastAPI (асинхронный веб-фреймворк)
  - WebSocket для real-time коммуникации

- **AI-сервисы**:
  - Ollama: потоковая генерация текста
  - ComfyUI: создание изображений

- **Frontend**:
  - JavaScript (Vanilla)
  - HTML5/CSS3
  - WebSocket API

## 📋 Требования

- Python 3.8 или выше
- [Ollama](https://ollama.ai/)
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- Современный веб-браузер с поддержкой WebSocket

## 🚀 Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/comfyuigen.git
cd comfyuigen
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
.\venv\Scripts\activate  # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements/dev.txt
```

4. Настройте конфигурацию:
```bash
cp .env.example .env
# Отредактируйте .env под ваши нужды
```

5. Запустите приложение:
```bash
python main.py
```

6. Откройте браузер и перейдите по адресу `http://localhost:8000`

## 🎮 Запуск

1. Убедитесь, что запущены сервисы Ollama и ComfyUI

2. Запустите сервер разработки:
```bash
python main.py
```

3. Откройте браузер и перейдите по адресу `http://localhost:8000`

## 📚 Документация

В проекте доступна подробная документация:

- **[ALGORITHM.md](ALGORITHM.md)** - Алгоритм работы системы:
  - Процесс генерации историй
  - Механизм выбора сюжетных линий
  - Интеграция с генерацией изображений
  - Обработка ошибок и fallback стратегии

- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Архитектура проекта:
  - Организация директорий и модулей
  - Компоненты системы и их взаимодействие
  - Конфигурация сервисов
  - Клиентская часть

- **Конфигурационные файлы**:
  - `config/ollama_config.py` - настройки генерации текста
  - `config/comfy_config.py` - параметры генерации изображений

- **Ключевые компоненты**:
  - `app/services/ollama/prompts/` - шаблоны для генерации текста
  - `app/services/ollama/story_generator.py` - ядро генерации историй
  - `app/services/comfy/` - интеграция с ComfyUI
  - `app/websocket/` - real-time коммуникация

## 🤝 Участие в разработке

Мы приветствуем вклад в развитие StoryCraft AI! 

### Как начать:

1. Форкните репозиторий
2. Создайте ветку для ваших изменений
3. Внесите изменения и протестируйте их
4. Создайте pull request с описанием изменений

### Области для улучшений:

- Оптимизация производительности генерации
- Улучшение качество промптов
- Расширение возможностей пользовательского интерфейса
- Добавление новых форматов историй
- Улучшение документации

## 📝 Лицензия

MIT License - см. [LICENSE](LICENSE) для деталей.

## 🙏 Благодарности

- [Ollama](https://ollama.ai/) - за мощный инструмент генерации текста
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - за гибкий фреймворк генерации изображений
- Всем контрибьюторам проекта
