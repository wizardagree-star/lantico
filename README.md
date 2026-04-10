# Лантико — Деплой на Render.com

## Что в этой папке

Полностью готовый к деплою проект. Один сервер Django отдаёт и сайт, и API. 
Node.js не нужен. Установка Python не нужна. Всё происходит в облаке.

---

## Пошаговая инструкция (≈10 минут)

### Шаг 1. Создайте аккаунт на GitHub (если нет)

Перейдите на **https://github.com** → кнопка **Sign up** → зарегистрируйтесь.

### Шаг 2. Создайте новый репозиторий

1. Нажмите **+** (правый верхний угол) → **New repository**
2. Имя: `lantico`
3. Видимость: **Private** (или Public — неважно)
4. **НЕ** ставьте галочки на README, .gitignore и т.д.
5. Нажмите **Create repository**

### Шаг 3. Загрузите файлы проекта

На странице пустого репозитория:
1. Нажмите ссылку **uploading an existing file**
2. Перетащите **ВСЕ файлы и папки** из скачанной папки `lantico/` в окно загрузки
   (папки `lantico/`, `test_app/`, `templates/`, `static/`, а также файлы 
   `manage.py`, `build.sh`, `render.yaml`, `requirements.txt`, `.gitignore`)
3. Нажмите **Commit changes**

⚠️ Убедитесь, что файл `manage.py` лежит в корне репозитория, а НЕ внутри ещё 
одной вложенной папки. Структура должна быть:

```
lantico/          ← папка настроек Django
  settings.py
  urls.py
  wsgi.py
test_app/         ← приложение
  models.py
  views.py
  ...
templates/        ← HTML-страницы
  base.html
  landing.html
  test.html
  result.html
static/
manage.py         ← в КОРНЕ репозитория
build.sh
render.yaml
requirements.txt
```

### Шаг 4. Создайте аккаунт на Render.com

1. Перейдите на **https://render.com**
2. Нажмите **Get Started for Free**
3. Выберите **Sign in with GitHub** (проще всего)

### Шаг 5. Создайте сервис

1. На дашборде Render нажмите **New +** → **Web Service**
2. Выберите **Build and deploy from a Git repository** → **Next**
3. Подключите ваш GitHub-репозиторий `lantico` → **Connect**
4. Render автоматически подхватит настройки из `render.yaml`. Если нет:
   - **Name:** `lantico`
   - **Runtime:** `Python`
   - **Build Command:** `chmod +x build.sh && ./build.sh`
   - **Start Command:** `gunicorn lantico.wsgi:application --bind 0.0.0.0:$PORT`
   - **Plan:** Free
5. В секции **Environment Variables** добавьте:
   - Key: `DJANGO_SECRET_KEY`, Value: любая длинная строка (например `my-super-secret-key-12345`)
   - Key: `PYTHON_VERSION`, Value: `3.11.11`
6. Нажмите **Create Web Service**

### Шаг 6. Подождите 2-3 минуты

Render скачает код, установит зависимости, применит миграции и загрузит вопросы.
Когда статус станет **Live**, нажмите на ссылку вида:

> **https://lantico.onrender.com**

🎉 Сайт работает!

---

## Важно знать

- **Бесплатный тир Render** усыпляет сервис после 15 минут бездействия. 
  Первый заход после «сна» занимает ~30 секунд. Это нормально.
- **SQLite** — база данных хранится на диске сервера. На бесплатном тире Render 
  диск сбрасывается при каждом редеплое. Для MVP это ок (результаты тестов — 
  одноразовые). Для продакшна переходите на PostgreSQL.
- **PDF-скачивание** работает из коробки благодаря reportlab.

---

## Если что-то пошло не так

1. На дашборде Render → ваш сервис → вкладка **Logs** — там будут ошибки.
2. Самая частая проблема: файлы загружены в GitHub с лишней вложенной папкой. 
   `manage.py` должен быть в корне, не в `lantico/lantico/manage.py`.
