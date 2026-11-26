# Cloudflare R2 for user-uploaded images

R2 is Cloudflare's S3-compatible object store. We use it to store user-uploaded images — keeping them off the app server and avoiding bandwidth costs through Railway.

## How it works

In `site/config/settings.py`, the `STORAGES` dict switches based on whether `R2_ACCESS_KEY_ID` is set:

- **R2 configured:** `django.core.files.storage.FileSystemStorage` → `storages.backends.s3.S3Storage` pointed at R2. Uploaded files go to R2.
- **R2 not configured:** Files land on the local filesystem under `site/media/`. Django serves them dynamically in dev.

## Bucket setup

1. In [Cloudflare Dashboard](https://dash.cloudflare.com/) → **R2** → **Create bucket**.
2. Name it something project-specific (e.g. `<project>-media`).
3. Leave the location as **Automatic**.
4. In the bucket → **Settings** → turn on **Public access** if you want to serve files via a custom domain.

## API credentials

1. Cloudflare Dashboard → **R2** → **Manage R2 API Tokens** → **Create API token**.
2. Permissions: **Object Read & Write** on the specific bucket.
3. Save the **Access Key ID** and **Secret Access Key**.

## Env vars

Add these to your `.env` (repo root) and Railway Variables:

```
R2_ACCESS_KEY_ID=<from Cloudflare>
R2_SECRET_ACCESS_KEY=<from Cloudflare>
R2_BUCKET_NAME=<project>-media
R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
R2_PUBLIC_URL=https://media.example.com
```

## Local dev

In local `.env`, leave `R2_ACCESS_KEY_ID` blank. Media saves to `site/media/` on disk and Django serves it at `/media/`. No Cloudflare account needed.

## Reference files

- `site/config/settings.py` — `R2_*` config + `STORAGES` switch
