# Setting up a custom domain

The reliable, low-effort path: register the domain in Cloudflare, then let Railway and Resend create their own DNS records via their Cloudflare integrations.

## Steps

1. **Buy the domain in Cloudflare.** Use Cloudflare Registrar.

2. **Add the custom domain in Railway and let it manage DNS.**
   Railway → your service → **Settings → Networking → Custom Domain**. Enter the apex domain (and `www` only if you want `www` to resolve), and when prompted, **authorize Railway's Cloudflare integration** so Railway creates the required CNAME records in Cloudflare automatically.

3. **Add the domain in Resend and let it manage DNS.**
   Resend → **Domains → Add Domain**. Connect/authorize the **Cloudflare integration** so Resend writes its own DKIM, SPF, and bounce records into Cloudflare automatically.

## After DNS is live — update the app

Update these in Railway's **Variables**:

- `ALLOWED_HOSTS` → add `example.com` (and `www.example.com` if configured)
- `CSRF_TRUSTED_ORIGINS` → add `https://example.com` (and `https://www.example.com` if configured)
- `SITE_URL` → `https://example.com`
- `DEFAULT_FROM_EMAIL` → an address at the verified domain

## Reference files

- `site/config/settings.py` — `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`
- Railway project → Settings → Domains
