# Docs site deploy — self-hosting the Fumadocs static export

> **Purpose:** the runbook for standing up the hosted docs site
> (`sartor-docs.taketempo.com`) on a shared webhost and wiring the CI deploy
> workflow to push new builds there automatically.
> **Audience:** `dev` — whoever (owner or agent) sets up the webhost + the
> GitHub repo secrets.
> **Authoritative for:** DNS, webhost upload paths (SFTP/SSH auto-push +
> manual fallback), and the SFTP secret names the CI workflow reads. Defers
> to [`documentation-architecture.md`](documentation-architecture.md) for
> *what* gets published (the L1 -> MDX projection, merge=publish) and to
> [`.github/workflows/docs-deploy.yml`](../../.github/workflows/docs-deploy.yml)
> for the exact build + deploy steps.

---

## What this covers

`docs-deploy.yml` builds a **static export** (`docs-site/out/`, plain HTML/CSS/JS —
no server process, no SSR) on every push to `main` and publishes it as a
downloadable artifact on every run. Getting that artifact onto
`sartor-docs.taketempo.com` is a **webhost** job: a shared host serves the
files and terminates TLS — there is no nginx server block or certificate to
manage on "your box," because there is no box. Two paths, not mutually
exclusive:

1. **Automated — SFTP/SSH push** (primary, once configured). The workflow
   uploads `out/` straight to the webhost's SFTP endpoint on every merge.
2. **Manual — download + upload.** Every run also publishes `out/` as a
   plain zip artifact (Actions -> the workflow run -> Artifacts), which
   works with **any** webhost via its own cPanel / File Manager / FTP
   client — no CI secrets required at all. This is the fallback if the
   host doesn't offer SFTP, or while the automated path is still being set
   up.

**Self-hosting via SFTP/SSH does not require the GitHub repo to be public.**
The workflow runs on pushes to `main` regardless of repo visibility, and a
private repo's Actions can still push over SFTP to a webhost you control —
the site can go live on its own schedule, decoupled from the v1.1.0 public
repo flip (see [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4.9).

---

## 1. DNS

Point `sartor-docs.taketempo.com` at the webhost per its own instructions —
almost always an **A record** (or a CNAME, if the host issues one) added in
whatever DNS provider manages `taketempo.com`. The webhost's control panel
will state which; there is no product-specific config on this side beyond
the record itself. TLS (HTTPS) is the webhost's job too — shared hosts
either auto-provision a certificate for the domain once DNS resolves
(cPanel's AutoSSL and most host onboarding flows do this automatically) or
give you a one-click "enable HTTPS" toggle; there is nothing to install or
renew manually.

## 2. Primary path — SFTP/SSH auto-push

The `Deploy over SFTP/SSH` step in `docs-deploy.yml` is **guarded**: it runs
only when all of `SFTP_HOST` / `SFTP_USER` / (`SFTP_KEY` or
`SFTP_PASSWORD`) are set. Until then it logs "not configured" and exits
cleanly — the workflow still succeeds, it just skips the auto-push (the
manual-download artifact from §3 still publishes every run).

**Setup:**

1. **Get SFTP credentials from the webhost.** Most shared hosts provision
   an SFTP account (hostname, username, password) alongside the regular
   hosting account — check the host's control panel (often under
   "FTP Accounts" / "SFTP" / "SSH Access"). Note the **target directory**
   the account can write to (often something like `public_html/` or a
   subdomain-specific folder for `sartor-docs.taketempo.com` if the host
   supports subdomain document roots) — this becomes `SFTP_REMOTE_PATH`.
2. **Prefer key-based auth if the host supports it.** Generate a dedicated
   deploy keypair (don't reuse a personal key):
   ```bash
   ssh-keygen -t ed25519 -f sartor-docs-deploy -C "sartor-docs-deploy" -N ""
   ```
   Add the **public** key (`sartor-docs-deploy.pub`) to the webhost account
   (its control panel's "SSH Keys" / "Authorized Keys" section — exact UI
   varies by host); keep the **private** key (`sartor-docs-deploy`, no
   passphrase, or set `SFTP_PASSPHRASE` too if the host requires one) for
   the GitHub secret below. If the host only offers password-based SFTP,
   use `SFTP_PASSWORD` instead — no key needed.
3. **Add the secrets** — GitHub repo -> Settings -> Secrets and variables ->
   Actions -> New repository secret:

   | Secret | Required | Value |
   |---|---|---|
   | `SFTP_HOST` | yes | the webhost's SFTP hostname |
   | `SFTP_USER` | yes | the SFTP username |
   | `SFTP_KEY` | one of `SFTP_KEY` / `SFTP_PASSWORD` | the private key file's full contents |
   | `SFTP_PASSWORD` | one of `SFTP_KEY` / `SFTP_PASSWORD` | the SFTP account password |
   | `SFTP_REMOTE_PATH` | optional (defaults to `/`) | the target directory noted in step 1 |
   | `SFTP_PORT` | optional (defaults to `22`) | only if the host uses a non-standard SFTP port |

4. **Push to `main`.** The next run's "Deploy over SFTP/SSH" step flips from
   skipped to active; check the Actions run log to confirm the upload
   succeeded, then load `https://sartor-docs.taketempo.com`.

## 3. Fallback / verification path — manual upload

Every workflow run (configured or not) uploads the static export as an
artifact named `docs-site-out`:

1. GitHub repo -> **Actions** -> the latest `Docs site deploy` run ->
   **Artifacts** -> download `docs-site-out.zip`.
2. Unzip it — the contents are plain static files (`index.html`, `docs/`,
   `_next/`, …), ready to serve as-is.
3. Upload via whatever the webhost offers: its **cPanel File Manager**
   (upload the zip, extract in place), a plain **FTP/FTPS client**
   (FileZilla, etc.) pointed at the same account, or drag-and-drop if the
   host has a web-based uploader. Same target directory as `SFTP_REMOTE_PATH`
   above (the site's document root).

This path needs no GitHub secrets at all — useful for a first manual
publish while confirming the domain + hosting account before wiring up
step 2's automation.

## 4. Verifying a deploy

- `docs-site/out/index.html` exists locally after `npm run build` (the CI
  workflow asserts this too — see `docs-deploy.yml` "Verify static export
  was produced").
- After upload, `https://sartor-docs.taketempo.com` should load the
  projected README home page, and `https://sartor-docs.taketempo.com/docs`
  should list the full nav (`meta.json`'s ICP-ladder order — see
  [`documentation-architecture.md`](documentation-architecture.md)).
- The site is a **pure function of `main` HEAD** — if a page looks stale,
  confirm the latest `main` push actually triggered a workflow run (Actions
  tab) before suspecting the upload step.
