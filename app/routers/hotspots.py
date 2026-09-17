from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas import HotspotOut

router = APIRouter(prefix="/hotspots", tags=["hotspots"])

# Groups waste/plastic complaints that are geographically close together using
# PostGIS's DBSCAN clustering, then keeps only clusters with enough reports to
# count as a recurring dumping spot. This is what lets the dashboard say
# "these 7 locations keep getting garbage" instead of just listing complaints.
HOTSPOT_SQL = text(
    """
    WITH clustered AS (
        SELECT
            id, address, ward_id, location,
            ST_ClusterDBSCAN(location::geometry, eps := :eps_degrees, minpoints := :minpoints)
                OVER () AS cluster_id
        FROM complaints
        WHERE type IN ('waste', 'plastic')
          AND status != 'resolved'
          AND location IS NOT NULL
    )
    SELECT
        cluster_id,
        COUNT(*) AS report_count,
        ST_Y(ST_Centroid(ST_Collect(location::geometry))) AS centroid_lat,
        ST_X(ST_Centroid(ST_Collect(location::geometry))) AS centroid_lng,
        (array_agg(address))[1] AS sample_address,
        (array_agg(ward_id))[1] AS ward_id
    FROM clustered
    WHERE cluster_id IS NOT NULL
    GROUP BY cluster_id
    HAVING COUNT(*) >= :minpoints
    ORDER BY report_count DESC
    """
)


@router.get("", response_model=list[HotspotOut])
def list_hotspots(db: Session = Depends(get_db)):
    # ~60m in degrees at this latitude; good enough for a city-scale MVP.
    eps_degrees = settings.hotspot_radius_meters / 111_320
    rows = db.execute(
        HOTSPOT_SQL,
        {"eps_degrees": eps_degrees, "minpoints": settings.hotspot_min_reports},
    ).mappings().all()
    return [dict(r) for r in rows]
