import os, shutil, uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.attachment import RecordAttachment
from app.models.user import EmissionRecord, VendorProfile
from app.core.security import get_current_user
from app.services.audit_service import log_action

router = APIRouter(prefix="/attachments", tags=["attachments"])
UPLOAD_DIR = "/app/uploads"
ALLOWED_MIME = {"application/pdf", "image/jpeg", "image/png", "image/webp",
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
MAX_SIZE_MB = 10


def _can_access_record(record, user, db):
    if user.role == "vendor":
        profile = db.query(VendorProfile).filter(VendorProfile.user_id == user.id).first()
        if not profile or record.vendor_id != profile.id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif user.role == "manager":
        from app.utils.helpers import region_value
        if region_value(record.region) != region_value(user.region):
            raise HTTPException(status_code=403, detail="Access denied")


@router.post("/{record_id}")
async def upload_attachment(
    record_id: int,
    file: UploadFile = File(...),
    description: str = "",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    record = db.query(EmissionRecord).filter(EmissionRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    _can_access_record(record, current_user, db)

    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_SIZE_MB}MB limit")
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=415, detail="File type not allowed. Use PDF, JPG, PNG, or Excel.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "file")[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, stored_name)
    with open(path, "wb") as f:
        f.write(content)

    att = RecordAttachment(
        record_id=record_id,
        uploaded_by=current_user.id,
        filename=file.filename or stored_name,
        file_path=path,
        file_size=len(content),
        mime_type=file.content_type,
        description=description,
    )
    db.add(att)
    log_action(db, current_user.id, "UPLOAD_ATTACHMENT", "record_attachments",
               description=f"Attached {file.filename} to record #{record_id}")
    db.commit()
    db.refresh(att)
    return {"id": att.id, "filename": att.filename, "size": att.file_size, "uploaded_at": att.uploaded_at}


@router.get("/{record_id}")
def list_attachments(record_id: int, db: Session = Depends(get_db),
                     current_user=Depends(get_current_user)):
    record = db.query(EmissionRecord).filter(EmissionRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404)
    _can_access_record(record, current_user, db)
    atts = db.query(RecordAttachment).filter(RecordAttachment.record_id == record_id).all()
    return [{"id": a.id, "filename": a.filename, "size": a.file_size,
             "mime_type": a.mime_type, "description": a.description,
             "uploaded_at": a.uploaded_at} for a in atts]


@router.delete("/{attachment_id}")
def delete_attachment(attachment_id: int, db: Session = Depends(get_db),
                      current_user=Depends(get_current_user)):
    att = db.query(RecordAttachment).filter(RecordAttachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404)
    if current_user.role == "vendor" and att.uploaded_by != current_user.id:
        raise HTTPException(status_code=403)
    if os.path.exists(att.file_path):
        os.remove(att.file_path)
    db.delete(att)
    db.commit()
    return {"message": "Attachment deleted"}
