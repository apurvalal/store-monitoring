from fastapi import APIRouter, HTTPException
from services.report_services import generate, trigger, fetch_report
from pydantic import BaseModel

router = APIRouter()

class ReportRequest(BaseModel):
    report_id: str

@router.get("/trigger_report")
def trigger_report():
    try:
        report_id = trigger()
        return {"report_id": report_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/get_report")
def get_report(request: ReportRequest):
    report_id = request.report_id
    try:
        csv_url = fetch_report(report_id)
        if csv_url:
            return {"status": "COMPLETE", "url": csv_url}
        else:
            return {"status": "RUNNING"}    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
