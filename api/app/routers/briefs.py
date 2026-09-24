"""District PDF brief endpoint: serves the precomputed one-page brief."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from api.app.data_store import data_store
from api.app.schemas import Crop, Season
from api.app.settings import get_settings

router = APIRouter()


@router.get("/briefs/{code}.pdf")
def get_brief(
    code: int,
    crop: Annotated[
        Crop | None,
        Query(description="Accepted for API-shape compatibility. Has no effect, see docstring."),
    ] = None,
    season: Annotated[
        Season | None,
        Query(description="Accepted for API-shape compatibility. Has no effect, see docstring."),
    ] = None,
) -> FileResponse:
    """Serves the precomputed one-page district brief PDF from data/public/briefs/.

    `crop` and `season` are accepted, per api/CLAUDE.md's documented
    `?crop&season` signature, but have no effect: src/agritwin/export/briefs.py builds
    one brief per district covering all 4 MVP crops on one page, not one per
    district x crop x season (see docs/decisions.md 2026-09-24), so there is nothing
    to filter to. Same pattern as DriverRow/BacktestRow's unused `season` parameter.
    """
    if data_store.district_name(code) is None:
        raise HTTPException(status_code=404, detail=f"Unknown district_code {code}")

    path = get_settings().DATA_DIR / "public" / "briefs" / f"{code}.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No brief available for district {code}")

    cache_seconds = get_settings().CACHE_SECONDS
    return FileResponse(
        path,
        media_type="application/pdf",
        headers={"Cache-Control": f"public, max-age={cache_seconds}"},
    )
