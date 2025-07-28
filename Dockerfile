# ----------------------------------------
# Stage 1: Build Python dependencies
# ----------------------------------------
FROM python:3.10-slim AS builder

# Set environment variables to optimize Python behavior
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Upgrade pip to latest version
RUN pip install --upgrade pip

# Set working directory for build stage
WORKDIR /green_power_backend

# Copy only requirements file to leverage Docker cache for dependency layer
COPY requirements.txt .

# Install dependencies without cache for a smaller image
RUN pip install --no-cache-dir -r requirements.txt

# ----------------------------------------
# Stage 2: Create the final production image
# ----------------------------------------
FROM python:3.10-slim

# Environment variables (redeclared here as this is a new stage)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create non-root user for better security
RUN useradd --create-home --system --shell /bin/bash green_power

# Set working directory inside the container
WORKDIR /green_power_backend

# Copy only installed packages and scripts from builder stage
COPY --from=builder /usr/local/lib/python3.10/site-packages/ /usr/local/lib/python3.10/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy project source code and entrypoint script, with correct ownership
COPY --chown=green_power:green_power . .
COPY entrypoint.sh /usr/local/bin/

# Make the entrypoint script executable
RUN chmod +x /usr/local/bin/entrypoint.sh

# Switch to non-root user
USER green_power

# Default command to run on container start
ENTRYPOINT ["entrypoint.sh"]
