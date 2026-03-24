"""SnapBack API. Nil-finding pass."""
from .models import SnapBackRequest, APIStatusResponse
import fastapi
from services.facade.api_gateway import ingest_op, cast_dict

app = fastapi.FastAPI()

@app.post("/session/transcript")
def api_transcript(p: SnapBackRequest) -> APIStatusResponse:
    """Ingest."""
    sid = str(p.sid())
    return APIStatusResponse(session_id=sid, data=cast_dict(ingest_op(sid, p.text, p.timestamp)))
