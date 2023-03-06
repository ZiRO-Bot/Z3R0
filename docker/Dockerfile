FROM python:3.10.9-slim as base

LABEL org.opencontainers.image.source="https://github.com/ZiRO-Bot/Z3R0"
LABEL org.opencontainers.image.description="A multi-purpose open-source discord bot"
LABEL org.opencontainers.image.licenses=MPL-2.0

# ---
FROM base as builder

WORKDIR /app

ARG STAGE

ENV STAGE=${STAGE} \
    PATH="/root/.local/bin:${PATH}" \
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
ADD src/ ./src
RUN poetry run pip install -U pip \
    && poetry install $(test "$STAGE" = production && echo "--no-dev") \
    --no-root -E postgresql -E mysql -E voice -E speedup

# ---
FROM base as final

WORKDIR /app

ENV PATH="/venv/bin:${PATH}" \
    VIRTUAL_ENV="/venv"

COPY --from=builder /venv /venv
COPY --from=builder /app/src/ /app/src
COPY assets/ /app/assets
COPY docker/__main__.py ./

CMD ["python", "."]
