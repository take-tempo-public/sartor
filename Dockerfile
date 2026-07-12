# syntax=docker/dockerfile:1
#
# Sartor container image — Docker- AND Podman-compatible (`docker build` /
# `podman build` both consume this file unchanged).
#
# Bakes in the two heavy runtime downloads so `docker run` needs nothing but an
# Anthropic API key: Chromium (PDF output) + the model2vec vector index (the
# assistant's semantic-recall tier). The app is installed EDITABLE from the copied
# source tree (`pip install -e .`) so Flask resolves templates/ · static/ ·
# personas/ relative to /app. The wheel now ships those same data dirs too
# (templates/ · static/ · personas/bundled/ · docs/wiki/ via package-data,
# `fix/packaging-install`) — this image simply still installs editable from
# source rather than building/installing the wheel; running from /app is
# correct and complete either way.
#
# Security: the app binds 0.0.0.0 INSIDE the container only; run it as
#   docker run -p 127.0.0.1:5000:5000 ...
# to keep Sartor's loopback-only posture on the host (SECURITY.md / PX-19).

FROM python:3.13-slim AS runtime

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
    # Drop privileges. The unprivileged user owns /app (writable db/output/configs)
    # and the browser cache.
    && useradd --create-home --uid 10001 sartor \
    && chown -R sartor:sartor /app /ms-playwright

USER sartor

EXPOSE 5000

# Bind all interfaces INSIDE the container namespace; the host maps it to loopback
# via `-p 127.0.0.1:5000:5000`. Override host/port with `--host`/`--port` if needed.
CMD ["sartor", "--host", "0.0.0.0"]
