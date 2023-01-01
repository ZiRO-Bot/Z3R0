FROM python:3.10.9-slim AS base

LABEL org.opencontainers.image.source="https://github.com/ZiRO-Bot/Z3R0"
LABEL org.opencontainers.image.description="A multi-purpose open-source discord bot"
LABEL org.opencontainers.image.licenses=MPL-2.0

WORKDIR /app

FROM base as builder

ARG STAGE

ENV STAGE=${STAGE} \
    PATH="/root/.local/bin:/venv/bin:${PATH}" \
    VIRTUAL_ENV="/venv"

RUN apt-get update && apt-get upgrade -y \
    && apt-get install --no-install-recommends -y \
        bash \
        brotli \
        build-essential \
        curl \
        gettext \
        git \
        libpq-dev \
    && curl -sSL 'https://install.python-poetry.org' | python - \
    && poetry --version \
    && python -m venv /venv

COPY poetry.lock pyproject.toml ./
COPY src/ ./src
RUN poetry run pip install -U pip \
    && poetry install $(test "$STAGE" = production && echo "--no-dev") --no-interaction --no-ansi --no-root

FROM base as final

COPY --from=builder /venv /venv
CMD ["poetry", "run", "bot"]
