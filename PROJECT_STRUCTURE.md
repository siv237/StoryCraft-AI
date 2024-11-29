# Структура проекта StoryCraft AI

## Основные директории и файлы

```
comfyuigen/
├── app/                                # Основной код приложения
│   ├── api/                           # API endpoints
│   │   └── routes/                    # Маршруты FastAPI
│   ├── services/                      # Сервисные модули
│   │   ├── ollama/                    # Сервис генерации текста
│   │   │   ├── prompts/              # Промпты для разных задач
│   │   │   └── story_generator.py     # Основной генератор историй
│   │   └── comfy/                     # Сервис генерации изображений
│   └── websocket/                     # WebSocket обработчики
│
├── config/                            # Конфигурационные файлы
│   ├── ollama_config.py              # Настройки Ollama
│   └── comfy_config.py               # Настройки ComfyUI
│
├── static/                           # Статические файлы
│   ├── css/                         # Стили
│   └── js/                          # JavaScript файлы
│       ├── main.js                  # Основной клиентский код
│       └── websocket/               # WebSocket клиент
│
├── templates/                        # HTML шаблоны
│   └── index.html                   # Основной интерфейс
│
├── tests/                           # Тесты
│   ├── unit/                        # Модульные тесты
│   └── integration/                 # Интеграционные тесты
│
├── requirements/                     # Зависимости проекта
│   ├── base.txt                     # Базовые зависимости
│   ├── dev.txt                      # Зависимости для разработки
│   └── test.txt                     # Зависимости для тестирования
│
├── .env.example                     # Пример конфигурации окружения
├── .gitignore                       # Игнорируемые Git файлы
├── ALGORITHM.md                     # Описание алгоритма работы
├── LICENSE                          # Лицензия проекта
├── PROJECT_STRUCTURE.md             # Этот файл
├── README.md                        # Основная документация
└── main.py                          # Точка входа приложения
```

## Описание ключевых компонентов

### Сервисы (app/services/)
- **ollama/** - Генерация текста историй
  - *story_generator.py* - Основной генератор сюжета
  - *prompts/* - Промпты для разных частей истории
- **comfy/** - Генерация изображений
  - *image_generator.py* - Создание иллюстраций

### Конфигурация (config/)
- **ollama_config.py** - Параметры для текстовой генерации
- **comfy_config.py** - Настройки для генерации изображений

### Клиентская часть
- **static/js/main.js** - Основной клиентский код
- **static/js/websocket/** - Работа с WebSocket
- **templates/index.html** - Пользовательский интерфейс

### Документация
- **ALGORITHM.md** - Подробное описание алгоритма работы
- **README.md** - Общая информация и инструкции
- **PROJECT_STRUCTURE.md** - Структура проекта (этот файл)

### Зависимости
- **requirements/base.txt** - Основные пакеты
- **requirements/dev.txt** - Инструменты разработки
- **requirements/test.txt** - Зависимости для тестирования
