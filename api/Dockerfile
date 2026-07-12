FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    PYSETUP_PATH="/opt/pysetup" \
    POETRY_HOME="/opt/poetry" \
    POETRY_VERSION=1.8.5

ENV PATH="$POETRY_HOME/bin:$PATH"

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl libpq-dev build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3

WORKDIR /usr/src/app
COPY pyproject.toml .
RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction  --no-root
RUN rm -rf /root/.cache/pypoetry
# PYTHONDONTWRITEBYTECODE empêche l'écriture des .pyc au runtime : précompiler
# les deps ici évite de les recompiler à chaque démarrage (et fait taire les
# SyntaxWarning émis à la compilation de facebook-sdk).
RUN python -m compileall -qq /usr/local/lib/python3.12/site-packages
COPY . .
RUN python manage.py collectstatic --noinput
CMD ["bash", "./docker/runme.sh"]
