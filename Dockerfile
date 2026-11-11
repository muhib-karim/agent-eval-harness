# Pinned by digest so a rebuild gets the same base; Dependabot proposes newer digests.
FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

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
