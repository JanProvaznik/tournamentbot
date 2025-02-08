FROM python:3.11-slim

WORKDIR /app

# Install poetry
RUN pip install poetry==1.7.1

# Copy files
COPY pyproject.toml poetry.lock .env ./
COPY src ./src

# Install without virtualenv
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi && \
    pip install aiohttp

# Start server
CMD ["python", "-m", "src.tournamentbot.server"]