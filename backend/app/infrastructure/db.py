from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def init_db():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            pass
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create optimized indexes for faster queries
    async with engine.begin() as conn:
        indexes = [
            # Water records indexes
            "CREATE INDEX IF NOT EXISTS idx_water_records_timestamp ON water_records(timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_water_records_sensor_id ON water_records(sensor_id)",
            "CREATE INDEX IF NOT EXISTS idx_water_records_anomaly ON water_records(is_anomaly) WHERE is_anomaly = true",
            "CREATE INDEX IF NOT EXISTS idx_water_records_sensor_timestamp ON water_records(sensor_id, timestamp DESC)",
            
            # Consumptions indexes
            "CREATE INDEX IF NOT EXISTS idx_consumptions_location_id ON consumptions(location_id)",
            "CREATE INDEX IF NOT EXISTS idx_consumptions_period ON consumptions(period_start, period_end)",
            "CREATE INDEX IF NOT EXISTS idx_consumptions_location_period ON consumptions(location_id, period_start DESC)",
            
            # Sensors indexes
            "CREATE INDEX IF NOT EXISTS idx_sensors_location_id ON sensors(location_id)",
            "CREATE INDEX IF NOT EXISTS idx_sensors_type ON sensors(sensor_type)",
            
            # Locations indexes
            "CREATE INDEX IF NOT EXISTS idx_locations_region ON locations(region)",
            "CREATE INDEX IF NOT EXISTS idx_locations_province ON locations(province)",
        ]
        
        for index_sql in indexes:
            try:
                await conn.execute(text(index_sql))
            except Exception as e:
                # Index might already exist or table not created yet
                pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
