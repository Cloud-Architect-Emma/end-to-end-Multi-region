FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies without caching to reduce image size
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure Python can find user-installed packages
ENV PATH=/root/.local/bin:$PATH

# Expose service port
EXPOSE 5001

# Run the application
CMD ["python", "app.py"]
