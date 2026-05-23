from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from app.repositories.memory_repository import MemoryRepository
from app.api.auth import require_admin
from app.services.widget_service import widget_service

router = APIRouter(tags=["widget"])

audit_repository = MemoryRepository()

class WidgetConfigUpdateRequest(BaseModel):
    allowed_origins: list[str] = Field(default_factory=list)
    theme: dict[str, Any] = Field(default_factory=dict)
    greeting: str = Field(..., min_length=1)
    enabled_tools: list[str] = Field(default_factory=list)


def _origin_allowed(origin: str | None, allowed_origins: list[str]) -> bool:
    """
    Allow requests with no Origin header for local CLI/server-side testing.
    Browser widget requests should include Origin and must be checked.
    """
    if origin is None:
        return True

    return origin in allowed_origins


def _frame_ancestors_value(allowed_origins: list[str]) -> str:
    if not allowed_origins:
        return "'none'"

    return " ".join(allowed_origins)


@router.get("/widget/{widget_id}/config")
def config(
    widget_id: str,
    response: Response,
    origin: str | None = Header(default=None),
) -> dict[str, Any]:
    config_data = widget_service.get_config(widget_id)
    allowed_origins = config_data.get("allowed_origins", [])

    if not isinstance(allowed_origins, list):
        allowed_origins = []

    if not _origin_allowed(origin, allowed_origins):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "origin_not_allowed",
                "message": "This origin is not allowed to load the widget config.",
                "origin": origin,
            },
        )

    response.headers["Content-Security-Policy"] = (
        f"frame-ancestors {_frame_ancestors_value(allowed_origins)}"
    )

    return config_data


@router.put("/admin/widget/{widget_id}/config")
def update_widget_config(
    widget_id: str,
    payload: WidgetConfigUpdateRequest,
    current_user: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    updated = widget_service.upsert_config(
        widget_id=widget_id,
        allowed_origins=payload.allowed_origins,
        theme=payload.theme,
        greeting=payload.greeting,
        enabled_tools=payload.enabled_tools,
    )
    audit_id = audit_repository.write_audit_log(
    actor=current_user["email"],
    action="widget_config_update",
    target=f"widget:{widget_id}",
    metadata={
        "widget_id": widget_id,
        "allowed_origins": payload.allowed_origins,
        "theme": payload.theme,
        "enabled_tools": payload.enabled_tools,
    },
)

    return {
        "status": "updated",
        "updated_by": current_user["email"],
        "audit_id": audit_id,
        "config": updated,
    }


@router.get("/widget.js", response_class=PlainTextResponse)
def widget_loader(
    response: Response,
) -> str:
    response.headers["Cache-Control"] = "public, max-age=300"
    response.headers["Content-Security-Policy"] = "script-src 'self'; object-src 'none'"

    return """
(function () {
  const currentScript = document.currentScript;
  const widgetId = currentScript && currentScript.dataset.widgetId
    ? currentScript.dataset.widgetId
    : "local-pandas";

  window.__MAINTAINERS_COPILOT_WIDGET_ID__ = widgetId;

  const iframe = document.createElement("iframe");
  iframe.src = "http://localhost:5173/";
  iframe.title = "Maintainers Copilot";
  iframe.style.position = "fixed";
  iframe.style.right = "24px";
  iframe.style.bottom = "24px";
  iframe.style.width = "420px";
  iframe.style.height = "560px";
  iframe.style.border = "0";
  iframe.style.zIndex = "999999";

  window.addEventListener("message", function (event) {
    if (!event.data || event.data.type !== "maintainers-copilot:resize") {
      return;
    }

    if (event.data.height) {
      iframe.style.height = event.data.height + "px";
    }
  });

  document.body.appendChild(iframe);
})();
""".strip()