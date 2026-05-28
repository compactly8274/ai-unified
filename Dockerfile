# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies if a requirements.txt exists
COPY requirements.txt .
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy the rest of the repository
COPY . .

# Install the package (editable mode)
RUN pip install -e .

# Default command (override as needed)
CMD ["python"]
