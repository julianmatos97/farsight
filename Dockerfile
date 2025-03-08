FROM python:3.13-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry==1.6.1

# Copy poetry configuration files
COPY pyproject.toml poetry.lock* ./

# Configure poetry to not use a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-dev --no-interaction --no-ansi

# Copy the application code
COPY . .

# Create data directories
RUN mkdir -p data/downloads data/processed data/embeddings data/test_suites data/evaluation_results


# Expose the API port
EXPOSE 8000

# Set the entrypoint
ENTRYPOINT ["python", "-m", "farsight2.main"]

# Default command
CMD ["api"] 