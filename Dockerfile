# Multi-stage build for minimal image size
FROM python:3.13-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    curl \
    unzip \
    gcc \
    musl-dev \
    libffi-dev

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.13-alpine

# Install runtime dependencies and ADB
RUN apk add --no-cache bash \
    android-tools --repository=http://dl-cdn.alpinelinux.org/alpine/edge/testing

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app directory and copy code
WORKDIR /app
COPY adb_metrics/ ./adb_metrics/

# Create non-root user
RUN addgroup -g 1001 appgroup && \
    adduser -D -u 1001 -G appgroup appuser && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Verify installations
RUN python --version && adb version

# Default command
ENTRYPOINT ["python", "-m", "adb_metrics.main"]
CMD ["--help"]
