# Go-live runbook: app.reportkitchen.com + auth.reportkitchen.com

Apache vhosts are STAGED AND ENABLED on this box (`:80` only) and verified by
Host-header curl: `app.` proxies to RK3 (:8300), `auth.` to ZITADEL (:9800).
The rk3 service already trusts proxy headers from localhost, so cookies turn
Secure automatically once TLS terminates at Apache. What remains is DNS, certs,
and the ZITADEL domain cutover — in that order.

## 1. DNS (registrar/DNS host)

```
app.reportkitchen.com    A    44.210.25.113
auth.reportkitchen.com   A    44.210.25.113
```

(`www.` stays wherever WordPress lives.) Wait for resolution.

## 2. TLS (on this box; requires port 80 reachable from the internet)

```bash
sudo certbot --apache -d app.reportkitchen.com    # choose "redirect"
sudo certbot --apache -d auth.reportkitchen.com   # choose "redirect"
```

Certbot clones each staged :80 vhost into a TLS vhost, proxy directives and
all, and installs auto-renewal. After this, https://app.reportkitchen.com is
live (still AUTH_MODE=dev until step 4).

## 3. ZITADEL domain cutover

ZITADEL validates requests against its ExternalDomain (currently `localhost` —
it literally refuses the auth. hostname until this changes, verified).
Edit `development/zitadel/zitadel-config.yaml`:

```yaml
ExternalDomain: auth.reportkitchen.com
ExternalPort: 443
ExternalSecure: true
```

Then `sudo systemctl restart zitadel`. If the instance rejects the domain
change (older instances can pin their created domain), the whole instance is
scripted and disposable — reinit with the production domain and re-run the
bootstrap (project/app/SMTP steps are in the execution plan + shell history;
~10 minutes).

Update the OIDC app + RK3 (PAT = development/zitadel/bootstrap.pat):

- Add `https://app.reportkitchen.com/api/auth/callback` to the app's
  redirect URIs (management API, same PUT used before) and turn OFF devMode.
- `.env`: `RK3_OIDC_ISSUER=https://auth.reportkitchen.com`,
  `RK3_OIDC_REDIRECT_URL=https://app.reportkitchen.com/api/auth/callback`.

## 4. Flip the app to real login

```
RK3_AUTH_MODE=oidc     # in .env
sudo systemctl restart rk3
```

## WordPress (www.) buttons

- Log in →  https://app.reportkitchen.com/api/auth/login
- Sign up → https://app.reportkitchen.com/api/auth/login?signup=1
- Email-capture form (email only!) →
  https://app.reportkitchen.com/api/auth/login?signup=1&login_hint=<email>

Never a password form on www — credentials are typed only on auth.

## Also pending for real signups

- SES: verify the reportkitchen.com domain + request production access
  (ZITADEL SMTP is already configured/activated; blocked only on this).
