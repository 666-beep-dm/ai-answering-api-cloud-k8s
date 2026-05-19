# Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        Client (Browser / SDK)                    │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTPS
                   ┌─────────▼──────────┐
                   │   FastAPI API GW    │
                   │  /api/v1/files/*   │
                   └──┬──────────────┬──┘
                      │              │
          ┌───────────▼──┐    ┌──────▼────────────┐
          │   Router     │    │  Background Tasks  │
          │  (HTTP layer)│    │  (post-processing) │
          └───────┬──────┘    └────────────────────┘
                  │
          ┌───────▼──────────┐
          │   FileService    │  ← Business Logic
          └──┬────────────┬──┘
             │            │
   ┌─────────▼──┐   ┌─────▼────────────┐
   │FileRepository│  │   S3Storage      │
   │(PostgreSQL) │   │ (aioboto3 +      │
   └─────────────┘   │  retry logic)    │
                      └──────┬───────────┘
                             │
                    ┌────────▼────────┐
                    │  S3 / MinIO     │
                    │  Object Store   │
                    └─────────────────┘
```

## Presigned URL flows

### Server-side upload
`POST /api/v1/files/upload` → API reads bytes → validates → S3.put_object → DB record

### Presigned upload (recommended for large files)
`POST /api/v1/files/upload/presigned` → API returns presigned PUT URL → client PUTs directly to S3 → client confirms

### Download
`GET /api/v1/files/{id}/download` → API returns presigned GET URL → client fetches from S3 directly
