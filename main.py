from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
import uvicorn
import os
from dotenv import load_dotenv
from app.api.routes.story import router as story_router

# Загружаем переменные окружения
load_dotenv()
load_dotenv(override=True)  # Добавляем override=True

app = FastAPI(title="Interactive Book Generator")

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Настраиваем шаблоны
templates = Jinja2Templates(directory="templates")

# Подключаем роуты
app.include_router(story_router, prefix="")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("book.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("RELOAD", "True").lower() == "true"
    )
