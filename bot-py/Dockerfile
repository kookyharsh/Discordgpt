FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Pre-fetch the Needle inference engine so the first query is instant.
# Never fail the build if the model hub is unreachable; the engine
# downloads lazily on first Needle() use instead.
RUN NEEDLE_TELEMETRY=0 needle fetch || true

COPY . .

EXPOSE 8000

CMD ["python", "-m", "src.main"]
