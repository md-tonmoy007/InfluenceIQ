# InfluenceIQ Frontend

Next.js App Router frontend for the InfluenceIQ monorepo. The app currently ships the visual prototype routes and local interaction flows under `frontend/`.

## Development

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Validation

```bash
npm run lint
npm run build
```

## Environment

Copy `.env.example` when local backend endpoints are available:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_WS_BASE_URL=ws://localhost:8000
```

## Integration Status

This PR ships the frontend prototype, route structure, Docker runtime, and type/API placeholders needed for backend integration. Live API submission, influencer retrieval, and WebSocket workflow streaming remain pending backend contract finalization.

The placeholder helpers in `src/lib/api.ts` and `src/lib/websocket.ts` intentionally throw until endpoint behavior and event replay semantics are confirmed and tested.
