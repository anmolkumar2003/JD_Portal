# Development image: includes CV-engine system deps and spaCy model.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libtesseract-dev \
        libmagic1 \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies from pyproject.toml only, so this layer is cached until they change.
COPY pyproject.toml ./
RUN python -c "import tomllib; p = tomllib.load(open('pyproject.toml', 'rb'))['project']; \
print('\n'.join(p['dependencies'] + p['optional-dependencies']['dev']))" > /tmp/requirements.txt \
    && pip install -r /tmp/requirements.txt \
    && python -m spacy download en_core_web_sm \
    && rm /tmp/requirements.txt

RUN useradd --create-home --uid 1000 app
COPY --chown=app:app . .
USER app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
