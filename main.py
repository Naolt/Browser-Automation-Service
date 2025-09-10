import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from routes.task_routes import router as task_router, task_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await task_service.start()
    logger.info("Application started")
    yield
    # Shutdown
    await task_service.stop()
    logger.info("Application shutdown")

app = FastAPI(
    title="Browser Use API",
    description="API for managing browser automation tasks",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(task_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
