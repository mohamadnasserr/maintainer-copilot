from typing import Any

from fastapi import APIRouter, Header, HTTPException, Response
from fastapi.responses import PlainTextResponse

from app.services.widget_service import widget_service

router = APIRouter(tags=["widget"])


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