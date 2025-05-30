FROM python:3.12-alpine
RUN apk add --no-cache gcc musl-dev
RUN pip install --no-cache-dir pipenv

WORKDIR /app

COPY Pipfile .
COPY Pipfile.lock .
RUN pipenv install --system --deploy

COPY main.py . 
COPY siamqtt.toml /etc/siamqtt.toml
ENV CONFIG_FILE /etc/siamqtt.toml
ENV PYTHONUNBUFFERED 1
EXPOSE 1234

ENTRYPOINT [ "python", "/app/main.py" ]
