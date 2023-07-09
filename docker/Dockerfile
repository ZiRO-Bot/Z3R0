FROM python:3.10.9-slim as base

LABEL org.opencontainers.image.source="https://github.com/ZiRO-Bot/Z3R0"
LABEL org.opencontainers.image.description="A multi-purpose open-source discord bot"
LABEL org.opencontainers.image.licenses=MPL-2.0

# ---
FROM base as builder

WORKDIR /app

ENV PATH="/root/.local/bin:${PATH}" \
    VIRTUAL_ENV="/venv"

# install PDM
RUN pip install -U pip setuptools wheel
RUN pip install pdm

COPY poetry.lock pyproject.toml ./
ADD src/ ./src
RUN mkdir __pypackages__ && pdm sync --prod -G "postgresql,mysql,voice,speedup" --no-editable

# ---
FROM base as final

WORKDIR /app

ENV PATH="/venv/bin:${PATH}" \
    VIRTUAL_ENV="/venv"


# retrieve packages from build stage
ENV PYTHONPATH=/project/pkgs
COPY --from=builder /project/__pypackages__/3.8/lib /project/pkgs

# retrieve executables
COPY --from=builder /project/__pypackages__/3.8/bin/* /bin/

CMD ["python", "-m", "zibot"]
