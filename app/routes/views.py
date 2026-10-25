"""HTML View routes serving Jinja2 templates."""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app import config

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(config.TEMPLATES_DIR))


@router.get("/overview")
def view_overview(request: Request):
    return templates.TemplateResponse(request=request, name="pages/overview.html", context={"active_page": "overview"})


@router.get("/quality")
def view_quality(request: Request):
    return templates.TemplateResponse(request=request, name="pages/quality.html", context={"active_page": "quality"})


@router.get("/eda")
def view_eda(request: Request):
    return templates.TemplateResponse(request=request, name="pages/eda.html", context={"active_page": "eda"})


@router.get("/features")
def view_features(request: Request):
    return templates.TemplateResponse(request=request, name="pages/features.html", context={"active_page": "features"})


@router.get("/validation")
def view_validation(request: Request):
    return templates.TemplateResponse(request=request, name="pages/validation.html", context={"active_page": "validation"})


@router.get("/models")
def view_models(request: Request):
    return templates.TemplateResponse(request=request, name="pages/models.html", context={"active_page": "models"})


@router.get("/results")
def view_results(request: Request):
    return templates.TemplateResponse(request=request, name="pages/results.html", context={"active_page": "results"})


@router.get("/interpretation")
def view_interpretation(request: Request):
    return templates.TemplateResponse(request=request, name="pages/interpretation.html", context={"active_page": "interpretation"})


@router.get("/predict")
def view_predict(request: Request):
    return templates.TemplateResponse(request=request, name="pages/predict.html", context={"active_page": "predict"})


@router.get("/replay")
def view_replay(request: Request):
    return templates.TemplateResponse(request=request, name="pages/replay.html", context={"active_page": "replay"})


@router.get("/monitoring")
def view_monitoring(request: Request):
    return templates.TemplateResponse(request=request, name="pages/monitoring.html", context={"active_page": "monitoring"})


@router.get("/limits")
def view_limits(request: Request):
    return templates.TemplateResponse(request=request, name="pages/limits.html", context={"active_page": "limits"})
