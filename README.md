# Bot de Telegram — Seguimiento de Proyectos

Bot para gestionar **proyectos y tareas** desde Telegram, con FastAPI + SQLAlchemy (async) + Alembic + MySQL.

## Stack
- **aiogram 3** — framework del bot (asíncrono, con FSM para flujos de conversación)
- **FastAPI** — sirve el webhook del bot y una pequeña API REST opcional
- **SQLAlchemy 2.0 (async)** — ORM, motor `aiomysql`
- **Alembic** — migraciones (usa una conexión síncrona con `pymysql`)
- **MySQL** — base de datos

## Estructura
```
app/
  config.py       # variables de entorno (pydantic-settings)
  database.py     # engine async + sesión
  models.py       # User, Project, ProjectMember, Task
  crud.py         # funciones de acceso a datos
  schemas.py       # Pydantic (API REST)
  main.py          # FastAPI: webhook + API REST + arranque del bot
  bot/
    bot.py         # instancia Bot/Dispatcher de aiogram
    handlers.py    # todos los comandos y callbacks del bot
    keyboards.py   # teclados inline
    states.py      # estados FSM (crear proyecto/tarea, asignar)
alembic/           # migraciones
```

## 1. Instalación

```bash
python -m venv venv
source venv/bin/activate   # en Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configuración

Crea la base de datos en MySQL:

```sql
CREATE DATABASE project_tracker CHARACTER SET utf8mb4;
```

Copia `.env.example` a `.env` y completa los valores:

```bash
cp .env.example .env
```

- `BOT_TOKEN`: pídelo a [@BotFather](https://t.me/BotFather)
- `DATABASE_URL`: cadena async (`mysql+aiomysql://username:password@host:3306/project_tracker`)
- `DATABASE_URL_SYNC`: cadena síncrona, misma DB (`mysql+pymysql://username:password@host:3306/project_tracker`) — la usa solo Alembic
- `BOT_MODE`: `polling` para desarrollo local, `webhook` para producción

## 3. Migraciones

```bash
alembic upgrade head
```

Esto crea las tablas `users`, `projects`, `project_members` y `tasks`.

Si más adelante cambias los modelos en `app/models.py`, genera una nueva revisión con:

```bash
alembic revision --autogenerate -m "descripcion del cambio"
alembic upgrade head
```

## 4. Ejecutar

### Modo polling (desarrollo, no necesitas dominio ni HTTPS)
Con `BOT_MODE=polling` en `.env`:

```bash
uvicorn app.main:app --reload
```

El bot empieza a recibir mensajes inmediatamente (FastAPI corre la API REST en paralelo, aunque no es indispensable en este modo).

### Modo webhook (producción)
Con `BOT_MODE=webhook`, `WEBHOOK_BASE_URL` apuntando a tu dominio HTTPS público y `WEBHOOK_SECRET` definido:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Al arrancar, la app configura automáticamente el webhook en Telegram apuntando a `WEBHOOK_BASE_URL + WEBHOOK_PATH`.

## 5. Uso del bot

| Comando | Descripción |
|---|---|
| `/start` | Registra al usuario |
| `/proyectos` | Lista tus proyectos (botones) |
| `/nuevoproyecto` | Crea un proyecto (te pregunta nombre y descripción) |
| `/ayuda` | Muestra la ayuda |

Dentro de cada proyecto (por botones):
- **Ver tareas** → lista con estado (🟥 pendiente, 🟨 en progreso, ✅ hecha)
- **Nueva tarea** → título, descripción y fecha límite opcional
- **Invitar miembro** → por `@usuario` de Telegram (debe haber hablado antes con el bot)
- Dentro de una tarea: cambiar estado, asignar a un miembro, o eliminarla