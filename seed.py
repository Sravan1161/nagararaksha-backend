"""Run with: python seed.py
Populates demo wards so the frontend has something to select from.
Replace these names/contacts with GWMC's real ward list before going live.
"""

from app.database import Base, SessionLocal, engine
from app.models import Ward

Base.metadata.create_all(bind=engine)

db = SessionLocal()
existing = {w.name for w in db.query(Ward).all()}

demo_wards = [f"Ward {i}" for i in range(1, 11)]
for name in demo_wards:
    if name not in existing:
        db.add(Ward(name=name))

db.commit()
print(f"Seeded {len(demo_wards)} wards (skipped any that already existed).")
