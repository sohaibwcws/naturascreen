# NaturaScreen backend (shared by the `api` and `worker` services).
# Base deps only. Scientific adapter extras (docking/neoantigen/response) are added
# in Phase 5 via the INSTALL_EXTRAS build arg; until then their absence yields an
# explicit `unavailable` status from the API rather than a fabricated result.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# uv: fast, reproducible installer.
RUN pip install --no-cache-dir uv==0.11.16

WORKDIR /app

# Dependency layer first (cache-friendly): install from the manifest before source.
COPY pyproject.toml ./
COPY naturascreen/__init__.py ./naturascreen/__init__.py
RUN uv pip install --system --no-cache -e ".[test]"

# Source.
COPY . .

# Frame/object storage volume, owned by the non-root runtime user.
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data \
    && chown -R app:app /app /data
USER app

EXPOSE 8000
CMD ["uvicorn", "naturascreen.main:app", "--host", "0.0.0.0", "--port", "8000"]
