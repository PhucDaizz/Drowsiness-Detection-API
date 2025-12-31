from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import users, contacts, trips
from database import engine, Base

app = FastAPI(title="Drowsiness Detection API")

# Setup CORS
origins = ["*"] # Allow all for now, restrict in production

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables on startup (For development only, use Alembic for production)
@app.on_event("startup")
async def startup():
    from database import create_database_if_not_exists
    await create_database_if_not_exists()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(users.router)
app.include_router(contacts.router)
app.include_router(trips.router)

from routers import statistics
app.include_router(statistics.router)

@app.get("/")
async def root():
    return {"message": "Drowsiness Detection API is running"}
