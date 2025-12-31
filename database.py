import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

# Default to localhost if not specified, user mentioned Docker so port might be mapped to 3306
# NOTE: User updated port to 3307 in previous content, ensuring we keep it
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+aiomysql://root:phucdai011@localhost:3307/drowsiness_db")

engine = create_async_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)

Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        yield session

async def create_database_if_not_exists():
    # Extract the base URL (without database name) to connect to MySQL server
    # Expected format: mysql+aiomysql://user:password@host:port/dbname
    try:
        if "/drowsiness_db" in DATABASE_URL:
            # Connect to "mysql" system database or just root
            root_url = DATABASE_URL.replace("/drowsiness_db", "/mysql")
        else:
            # Fallback handling if URL format is different
            root_url = DATABASE_URL.rsplit("/", 1)[0] + "/mysql"
            
        # Create a temporary engine to execute CREATE DATABASE
        tmp_engine = create_async_engine(root_url, echo=True)
        async with tmp_engine.begin() as conn:
            await conn.execute(text("CREATE DATABASE IF NOT EXISTS drowsiness_db"))
        await tmp_engine.dispose()
    except Exception as e:
        print(f"Warning: Could not check/create database: {e}")
