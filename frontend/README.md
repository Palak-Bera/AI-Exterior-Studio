# AI Exterior Studio - Frontend (Next.js)

Next.js (App Router, TypeScript, Tailwind) UI for the studio.

## MVC-style structure

```
app/            # Views (routes): upload page + studio page
components/      # Views (presentational): canvas, category panel, material picker, before/after
lib/            # Model + Controller: typed API client, types, config
```

## Setup

```powershell
npm install
copy .env.local.example .env.local   # point NEXT_PUBLIC_API_BASE at the backend
npm run dev
```

Open http://localhost:3000 (backend must be running on http://localhost:8000).

## Docker

```powershell
# Build & run just the frontend (point it at a reachable backend)
docker build --build-arg NEXT_PUBLIC_API_BASE=http://localhost:8000 -t ai-exterior-studio-frontend .
docker run -p 3000:3000 ai-exterior-studio-frontend
```

`NEXT_PUBLIC_API_BASE` is inlined at build time, so it must be set as a build arg.

## Run both with Docker Compose

From the project root (`AI Exterior Studio/`):

```powershell
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend:  http://localhost:8000/docs

## Flow

1. **Upload** (`/`) - drag a house photo; the Ingestion Engine validates it.
2. **Studio** (`/studio/[projectId]`)
   - Click **Auto-detect elements** to run the Segmentation Engine.
   - Pick a detected element (walls, balconies, rooftop, gate, ...).
   - Choose a material (paint color or texture) for that element.
   - Click **Apply materials & render** to run the Rendering Engine, then
     compare with the before/after slider.
