# Stage 1: Builder
FROM python:3.12-slim AS builder
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Stage 2: Final image
FROM python:3.12-slim
WORKDIR /app

# Copy installed packages and app code from builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app /app

# Ensure Python can find user-installed packages
ENV PATH=/root/.local/bin:$PATH

EXPOSE 5000
CMD ["python", "app.py"]
