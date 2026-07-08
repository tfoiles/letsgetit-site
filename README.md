# letsgetit-site

Single-page placeholder site for the band **Let's Get It**, served by GitHub Pages
on the apex domain **letsgetitband.com**.

- `index.html` — the whole site (self-contained: inline CSS, no JS, no build step)
- `CNAME` — tells GitHub Pages the custom domain (contents: `letsgetitband.com`)

## Enable GitHub Pages

1. Go to the repo on GitHub → **Settings** → **Pages** (left sidebar).
2. Under **Build and deployment → Source**, choose **Deploy from a branch**.
3. Set **Branch** = `main`, **Folder** = `/ (root)`, then click **Save**.
4. Under **Custom domain**, enter `letsgetitband.com` and click **Save**.
   (This is also what the committed `CNAME` file sets.)
5. Wait for the DNS check to pass and the TLS certificate to provision, then tick
   **Enforce HTTPS**. This checkbox is greyed out until the certificate is ready —
   it can take a little while after DNS resolves.

## DNS records to add at your registrar

Add these at whoever manages DNS for `letsgetitband.com`. Apex IPs verified against
GitHub's docs on 2026-07-07.

### A records (apex / root domain) — IPv4

| Type | Host / Name | Value           |
|------|-------------|-----------------|
| A    | @           | 185.199.108.153 |
| A    | @           | 185.199.109.153 |
| A    | @           | 185.199.110.153 |
| A    | @           | 185.199.111.153 |

### AAAA records (apex / root domain) — IPv6

| Type | Host / Name | Value               |
|------|-------------|---------------------|
| AAAA | @           | 2606:50c0:8000::153 |
| AAAA | @           | 2606:50c0:8001::153 |
| AAAA | @           | 2606:50c0:8002::153 |
| AAAA | @           | 2606:50c0:8003::153 |

### CNAME record (www subdomain)

| Type  | Host / Name | Value              |
|-------|-------------|--------------------|
| CNAME | www         | tfoiles.github.io  |

> Some registrars want the host as `@` for the root and `www` for the subdomain;
> others want the full domain. Use whatever your registrar's UI expects for
> "root/apex" and "www".

## Notes

- DNS changes can take **24–48 hours** to fully propagate.
- **HTTPS** (the TLS certificate + the "Enforce HTTPS" option) only becomes
  available **after** DNS resolves to GitHub, so expect a gap between "site loads"
  and "HTTPS works."
- `og.png` is referenced by the Open Graph / Twitter tags but not yet added — drop a
  1200×630 image at the repo root as `og.png` to enable rich link previews.
- The Instagram / YouTube / TikTok links are placeholders (`href="#"`); replace them
  in `index.html` when the real profile URLs exist.
