from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine, Base, SessionLocal
from app.db.seed import run_all_seeds

# Import all models so Base.metadata.create_all picks them up
from app.models import user as _user_models          # noqa
from app.models import notification as _notif_models  # noqa
from app.models import attachment as _att_models      # noqa

from app.api.routes.auth          import router as auth_router
from app.api.routes.users         import router as users_router
from app.api.routes.emissions     import router as emissions_router
from app.api.routes.dashboard     import router as dashboard_router
from app.api.routes.reports       import router as reports_router
from app.api.routes.notifications import router as notif_router
from app.api.routes.profile       import router as profile_router
from app.api.routes.targets       import router as targets_router
from app.api.routes.attachments   import router as attach_router
from app.api.routes.vendor_tools  import router as vendor_router
from app.api.routes.misc          import ef_router, audit_router, period_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Scope 3 Emissions Platform API",
    description="GHG Protocol Scope 3 emissions calculation and reporting platform",
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(emissions_router)
app.include_router(dashboard_router)
app.include_router(reports_router)
app.include_router(notif_router)
app.include_router(profile_router)
app.include_router(targets_router)
app.include_router(attach_router)
app.include_router(vendor_router)
app.include_router(ef_router)
app.include_router(audit_router)
app.include_router(period_router)


@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        run_all_seeds(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.2.0"}
