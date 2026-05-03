FROM python:3.11-slim

WORKDIR /app

ENV PIP_DEFAULT_TIMEOUT=600 \
    PIP_RETRIES=10 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements-inference.txt .
RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install \
      --no-cache-dir \
      --index-url https://download.pytorch.org/whl/cpu \
      --trusted-host download.pytorch.org \
      torch==2.3.0+cpu && \
    python -m pip install \
      --prefer-binary \
      --no-cache-dir \
      --trusted-host pypi.org \
      --trusted-host files.pythonhosted.org \
      -r requirements-inference.txt

COPY . .

CMD ["sh", "-c", "uvicorn service_app:app --host 0.0.0.0 --port ${PORT:-8001}"]
