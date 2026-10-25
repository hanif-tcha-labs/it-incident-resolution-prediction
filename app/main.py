"""Main FastAPI application entry point with lifespan, routing, and error handlers."""
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import config
from app.routes import (
    eda,
    evaluation,
    health,
    models,
    monitoring,
    predict,
    project,
    simulation,
    views,
)
from app.services.model import ModelService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model pipeline and ensure SQLite tables on startup."""
    print("Loading ML model and artifacts...")
    ModelService.get_instance().load()
    print("Model service initialized successfully.")
    yield
    print("Shutting down application...")


app = FastAPI(
    title="HTVEX AI Incident Resolution Forecasting",
    description=(
        "IT incident resolution time estimates based on ticket information available at opening."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Custom error handler for validation errors (specifically data leakage protection)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    details = []

    for err in errors:
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "")
        err_type = err.get("type", "")

        if "extra_forbidden" in err_type:
            field_name = err.get("loc", ["unknown"])[-1]
            details.append({
                "field": field_name,
                "message": (
                    f"Field '{field_name}' is forbidden: it is only known after incident opening "
                    "(e.g., resolved_at, closed_at, reassignment_count, active, state) or not part of "
                    "the authorized initial feature set. Including it would cause temporal data leakage."
                ),
                "type": "leakage_protection_error",
            })
        else:
            details.append({
                "field": loc,
                "message": msg,
                "type": err_type,
            })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": details,
        },
    )


# Register API routers
app.include_router(health.router)
app.include_router(project.router)
app.include_router(eda.router)
app.include_router(models.router)
app.include_router(evaluation.router)
app.include_router(predict.router)
app.include_router(simulation.router)
app.include_router(monitoring.router)
app.include_router(views.router)

# Mount static files and templates directory
config.STATIC_DIR.mkdir(parents=True, exist_ok=True)
config.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(config.TEMPLATES_DIR))


@app.get("/", include_in_schema=False)
def root_redirect():
    """Redirect root to ticket simulator."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/predict")
