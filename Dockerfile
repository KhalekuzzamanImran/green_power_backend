# ---------- Build Stage ----------
FROM python:3.10-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt

# Copy project source code
COPY . .

# ---------- Runtime Stage ----------
FROM python:3.10-slim AS runtime

# Environment setup
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.10/site-packages"

# Create app user and group early to cache
RUN addgroup --system green_power && \
    adduser --system --ingroup green_power green_power

# Working directory
WORKDIR /app

# Install only runtime system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages and app files from builder
COPY --from=builder /install /install
COPY --from=builder /app /app

# Copy and configure entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh && chown green_power:green_power /app/entrypoint.sh

# Adjust ownership and switch to non-root user
RUN chown -R green_power:green_power /app
USER green_power

# Use entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
