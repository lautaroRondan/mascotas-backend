from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db
from app.routers import auth, households, pets, vaccines, vet_visits, medications, medication_logs
from app.routers import invitations, members

app = FastAPI(title="App de mascotas")
app.include_router(auth.router)
app.include_router(households.router)
app.include_router(pets.router)
app.include_router(vaccines.router)
app.include_router(vet_visits.router)
app.include_router(medications.router)
app.include_router(medication_logs.router)
app.include_router(invitations.router)
app.include_router(members.router)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}