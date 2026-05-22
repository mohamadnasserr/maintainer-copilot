from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, health, nlp, widget
from app.api.errors import install_exception_handlers
from app.infra.config import get_settings
from app.infra.logging import configure_logging
from app.infra.vault import require_vault, verify_required_demo_secret
from app.api.middleware import RequestContextMiddleware

def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    require_vault(settings)
    verify_required_demo_secret()

    app = FastAPI(title="Maintainers Copilot", version="0.1.0-week7")
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        allow_origin_regex=None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(chat.router)
    app.include_router(nlp.router)
    app.include_router(widget.router, tags=["widget"])
    return app


app = create_app()

