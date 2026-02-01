FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# Default runs the Green Agent demo end-to-end on sample data.
CMD ["python", "scripts/finance_analyzer.py", "data/10k_2020_10_critical_sections/1137091_2020.json"]
