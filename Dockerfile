# Pinned by digest so a rebuild gets the same base; Dependabot proposes newer digests.
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir '.[grade]' \
    && useradd --create-home --uid 10001 evaluator \
    && mkdir -p /app/runs \
    && chown evaluator:evaluator /app/runs

USER evaluator
ENTRYPOINT ["agent-eval"]
CMD ["--help"]
