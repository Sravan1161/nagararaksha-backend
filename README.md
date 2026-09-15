# NagaraRaksha backend

FastAPI + PostgreSQL/PostGIS backend for the Hanamkonda civic reporting app
(waste, plastic and noise reports; hotspot detection; cleanup verification;
Claude-powered photo triage).

This replaces the `window.storage` calls used in the React prototype with a
real database, real spatial hotspot detection, and AI photo classification.

## Run it locally

You need Docker, or a local Postgres with the PostGIS extension available.

**With Docker (recommended):**

```bash
cp .env.example .env          # fill in ANTHROPIC_API_KEY if you want AI triage
docker compose up --build
python seed.py                 # in a second terminal, once the API is up — seeds 10 demo wards
```

The API is now at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`.

**Without Docker**, install Postgres 15+ with PostGIS, create a database and
user matching `.env`, then:

```bash
pip install -r requirements.txt --break-system-packages
python seed.py
uvicorn app.main:app --reload
```

## What's real here vs. still a placeholder

| Piece | Status |
|---|---|
| Complaints CRUD, filtering, statuses | Real, backed by Postgres |
| Spatial hotspot clustering | Real — uses PostGIS `ST_ClusterDBSCAN` to group nearby reports, not just exact address string matches |
| Photo storage | Real, but saves to local disk (`app/services/storage.py`). Swap `save_photo()` for an S3/Cloudinary/Firebase call before shipping — nothing else needs to change |
| AI photo classification | Real, calls Claude vision if `ANTHROPIC_API_KEY` is set. Falls back silently (officer sets severity manually) if the key is missing or the call fails |
| Auth | Minimal — an anonymous `device_uuid` per installed app identifies a citizen, no login. Fine for a pilot; add real auth (phone OTP is standard for Indian civic apps) before a public launch |
| Volunteer cap, community cleanup | Real, enforced server-side (5 volunteers per complaint, matching the frontend) |

## Wiring up the React frontend

The citizen/admin prototype currently uses `window.storage`. To point it at
this backend instead:

- Replace `window.storage.set('complaints:...', ..., true)` with
  `POST /complaints` (multipart form: `device_uuid`, `type`, `address`,
  `latitude`, `longitude`, `ward_id`, `community_open`, `noise_source`,
  `loudness`, `photo`).
- Replace the `window.storage.list('complaints:', true)` + per-key `get` loop
  with a single `GET /complaints?type=&status=&ward_id=&device_uuid=`.
- Replace the admin "save" action with `PATCH /complaints/{id}` for
  severity/assignment, and `POST /complaints/{id}/resolve` (multipart,
  `after_photo` required) when marking something resolved.
- Replace "join cleanup" with `POST /complaints/{id}/volunteers`.
- Use the same `reporter-id` value the app already generates and stores in
  personal (non-shared) `window.storage` as `device_uuid`.

## API summary

```
GET    /wards
POST   /complaints                        (multipart: photo + fields)
GET    /complaints?type=&status=&ward_id=&device_uuid=
GET    /complaints/{id}
PATCH  /complaints/{id}                    {"status": "...", "severity": "..."}
POST   /complaints/{id}/resolve            (multipart: after_photo)
POST   /complaints/{id}/volunteers         (form: device_uuid)
GET    /hotspots
GET    /health
```

## Before this goes anywhere near production

- Add real authentication (phone OTP is the norm for Indian civic apps).
- Move photo storage off local disk.
- Add rate limiting on `POST /complaints` so the AI classification cost and
  the hotspot detector aren't easy to abuse.
- Add Alembic migrations instead of `Base.metadata.create_all` before your
  schema needs to change without dropping data.
- Get GWMC's real ward boundaries and officer contacts instead of the
  `Ward 1`–`Ward 10` placeholders in `seed.py`.
