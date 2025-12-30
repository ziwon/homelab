FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY prompts /app/prompts

RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir .

CMD ["code-embedder"]
