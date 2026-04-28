"""
Notification Service
====================
Creates in-app notifications. Caller commits the DB session.
Usage:
    notify(db, user_id=mgr.id, type=NotificationType.record_submitted,
           title="New record submitted", message="...", link="/emissions")
"""
from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.notification import Notification, NotificationType


def notify(
    db: Session,
    user_id: int,
    type: NotificationType,
    title: str,
    message: str,
    link: Optional[str] = None,
):
    n = Notification(user_id=user_id, type=type, title=title,
                     message=message, link=link)
    db.add(n)


def notify_many(
    db: Session,
    user_ids: List[int],
    type: NotificationType,
    title: str,
    message: str,
    link: Optional[str] = None,
):
    for uid in user_ids:
        notify(db, uid, type, title, message, link)
