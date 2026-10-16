# syntax=docker/dockerfile:1
#
# Sartor container image — Docker- AND Podman-compatible (`docker build` /
# `podman build` both consume this file unchanged).
#
# Bakes in Chromium (PDF output) so `docker run` needs nothing but an Anthropic API
# key. The model2vec vector-index step (the assistant's semantic-recall tier) is
# best-effort and, observed 2026-10-16, does NOT complete in this image: `git` is not
# installed in the base image and no `.git` is in the build context (item 145 dossier
# O12), so recall runs on its lexical tiers until that is fixed. The app is installed EDITABLE from the copied
# source tree (`pip install -e .`) so Flask resolves templates/ · static/ ·
# personas/ relative to /app. The wheel now ships those same data dirs too
# (templates/ · static/ · personas/bundled/ · docs/wiki/ via package-data,
# `fix/packaging-install`) — this image simply still installs editable from
# source rather than building/installing the wheel; running from /app is
# correct and complete either way.
#
# Security: the app binds 0.0.0.0 INSIDE the container only; run it as
#   docker run -p 127.0.0.1:5000:5000 -v sartor-data:/data ...
# to keep Sartor's loopback-only posture on the host (SECURITY.md / PX-19).
#
# Data: everything the user owns (the SQLite DB, the LLM log, the API key, configs,
# résumés, output, uploaded personas) lives under /data, which is SARTOR_HOME. Mount ONE
# named volume there. /app is code and is replaced wholesale by an image update, so nothing
# in it is user data (item 145; `sartor_home.py`).

# Pinned by digest, not by tag (OpenSSF Scorecard Pinned-Dependencies): a mutable
# tag like `python:3.13-slim` can resolve to a different image on any rebuild. The
# trailing tag comment keeps it readable and lets Dependabot bump the digest.
FROM python:3.13-slim@sha256:eb43ff125d8d58d7449dcba7d336c23bcac412f526d861db493b9994d8010280 AS runtime

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_DEBUG=0 \
    SARTOR_NO_BROWSER=1 \
    # Install + read Playwright's Chromium from ONE shared path so the browser
    # installed as root at build time is found by the non-root runtime user.
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# .dockerignore keeps tests/, evals/, .git, and the PII data dirs out of the image.
COPY . /app

RUN python -m pip install --upgrade pip \
    # Editable install: deps + the `sartor` console script; source stays under /app
    # so Flask finds templates/static/personas relative to app.py.
    && pip install -e . \
    # Chromium + the exact OS libs it needs (apt, as root). Core PDF feature.
    && python -m playwright install --with-deps chromium \
    # Bake the semantic-recall vector index (~30 MB model). Best-effort: a network
    # flake must not fail the whole image — recall degrades to its lexical/wiki
    # tiers without it.
    && (python -m scripts.build_vector_index \
        || echo "WARN: vector index not baked; assistant recall will be lexical-only") \
    # Drop privileges. The unprivileged user owns /app and the browser cache, and /data,
    # the data root. /data is created AND chowned here, before `VOLUME`: a named volume
    # copies the image's /data content and ownership in on first use, and any change to
    # the path after `VOLUME` is discarded.
    && useradd --create-home --uid 10001 sartor \
    && mkdir -p /data \
    && chown -R sartor:sartor /app /ms-playwright /data

# Set AFTER the build steps above, so nothing at build time resolves a data path into /data.
ENV SARTOR_HOME=/data

VOLUME ["/data"]

USER sartor

EXPOSE 5000

# Python as PID 1 has no SIGTERM handler, so the default stop signal is ignored and the engine waits
# out its grace period before SIGKILL. Measured (rootful Podman, 2026-10-16): `podman stop` took
# 11.0 s and 11.2 s with the default, 1.3 s with SIGINT, which Werkzeug turns into a normal exit.
STOPSIGNAL SIGINT

# `/healthz` answers only loopback-Host requests and is exempt from idle tracking, so
# polling it never keeps an `--idle-timeout` instance alive. Stdlib only: the image needs
# no curl. urlopen raises on a refused connection or a non-2xx, and the traceback exits 1.
# The URL assumes the default port; if you override `--port`, override this check too.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:5000/healthz', timeout=3)"]

# Bind all interfaces INSIDE the container namespace; the host maps it to loopback
# via `-p 127.0.0.1:5000:5000`. Override host/port with `--host`/`--port` if needed.
CMD ["sartor", "--host", "0.0.0.0"]
