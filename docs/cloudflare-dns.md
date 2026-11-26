# Cloudflare DNS

We use Cloudflare as the DNS provider for projects on this stack. Cloudflare sits in front of the domain whether or not the app itself is behind Cloudflare — the key features we rely on are **CNAME flattening** for apex domains and **proxied DNS** for DDoS protection and SSL management.

## When to set this up

When provisioning a new project that will use a custom domain (always, for a public site):

1. Register the domain at any registrar (name.com, Porkbun, GoDaddy, etc.).
2. Move DNS to Cloudflare (free plan) following the process below.
3. Add the custom domain to Railway.

## Step-by-step

### 1. Add the site to Cloudflare

1. Log in at [dash.cloudflare.com](https://dash.cloudflare.com/).
2. Click **Add a domain** (or, if you already have domains, the **Add a domain** button on the main Domains page).
3. Enter the apex domain (e.g. `example.com` — no subdomain prefix).
4. Cloudflare scans existing DNS records. Verify them on the next screen.
5. Choose the **Free** plan.
6. Cloudflare displays two nameserver addresses — copy them.

### 2. Disable DNSSEC at your registrar (if enabled)

DNSSEC at the registrar conflicts with Cloudflare's proxy. Before changing nameservers:

- At your registrar, find the **DNSSEC** settings and **disable** them.
- After Cloudflare is active, you can re-enable DNSSEC through Cloudflare (the Cloudflare dashboard handles the DS record publishing).

### 3. Point the domain to Cloudflare

At your registrar, replace the default nameservers with Cloudflare's:

1. Find the **Nameservers** / **DNS** settings for the domain.
2. Switch from the registrar's nameservers to **Custom nameservers**.
3. Enter the two Cloudflare nameservers from step 1 (e.g. `daisy.ns.cloudflare.com` and `amir.ns.cloudflare.com`).
4. Save.

Propagation usually takes 5–30 minutes, occasionally up to an hour.

### 4. Add DNS records in Cloudflare

Once the nameserver change propagates, go to Cloudflare → **DNS** for the domain and add records:

| Type | Name | Value | Proxy |
|------|------|-------|-------|
| **CNAME** | `@` | Railway hostname (e.g. `app.up.railway.app`) | ✅ orange |
| **CNAME** | `www` (optional) | Railway hostname (same target) | ✅ orange |
| **MX** | `@` | Your email provider's MX host | ☐ grey (DNS only) |
| **TXT** | `@` | SPF record for email | ☐ grey |
| **TXT** | `@` | DKIM / DMARC records | ☐ grey |

#### Apex CNAME (orange cloud = CNAME flattening)

Normally you can't use a CNAME at the zone apex (`example.com`). Cloudflare's **CNAME flattening** makes it work when the record is proxied (orange cloud): Cloudflare resolves the CNAME target on its own edge and returns its proxy IPs to clients. This is better than a static A record because Railway's IPs can change.

**Always proxy the Apex CNAME** — the orange cloud is what enables flattening.

#### Email records (grey cloud)

Keep MX and TXT records **DNS only** (grey cloud). Cloudflare's proxy only works for HTTP traffic; mail servers need direct access to the original MX targets.

#### Verifying propagation

```bash
dig @1.1.1.1 example.com A +short
dig @1.1.1.1 www.example.com A +short   # only if www is configured
```

The apex (and `www` too, if configured) should return Cloudflare proxy IPs (two IPs in the `104.16.0.0/12` or `172.64.0.0/13` range).

### 5. Add the domain to Railway

1. In Railway → your project → **Settings** → **Domains**.
2. Add `example.com` (and `www.example.com` if you want `www` to resolve).
3. Railway provisions a Let's Encrypt certificate and shows the status as **Active** once complete.

### 6. Update Django settings

Add the domain to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in your Railway Variables:

```
ALLOWED_HOSTS=example.com,<railway-hostname>.railway.app
CSRF_TRUSTED_ORIGINS=https://example.com
```

Add `www.example.com` and `https://www.example.com` only if you configured `www`.

## Common records for project services

Beyond the web app, you may need records for related services:

| Type | Name | Value | Purpose |
|------|------|-------|---------|
| **CNAME** | `media` | R2 bucket public URL | Serving user-uploaded images (see [cloudflare-r2.md](cloudflare-r2.md)) |
| **CNAME** | `status` | e.g. `statuspage.url` | Status page external to the app |
| **CNAME** | `*` | `example.com` (catch-all) | Only if you want every subdomain to resolve; usually skip |

## Moving a domain to a new registrar

Cloudflare is the DNS provider, not necessarily the registrar. You can transfer the domain registration to Cloudflare Registrar (at-cost pricing, no markup) for convenience, but it's optional. The domain registration and DNS can live in different places:

- **Registrar:** name.com, Porkbun, Cloudflare Registrar, etc. — manages renewal, contact info.
- **DNS:** Cloudflare — manages records, proxy, SSL.

If you transfer the registration, Cloudflare Registrar locks the domain during transfer (~5 days). DNS keeps working throughout.

## Reference files

- `site/config/settings.py` — `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`
- Railway project → Settings → Domains
