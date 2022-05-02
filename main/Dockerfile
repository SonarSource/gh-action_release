FROM python:3.7-slim AS build-env
ADD . /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install pipenv
RUN pipenv requirements > requirements.txt
RUN pip install --target=/app -r requirements.txt

FROM python:3.7-slim
COPY --from=build-env /app /app

COPY bin/ /usr/local/bin

RUN apt-get update && apt-get install -y gpg && rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/app
CMD ["/usr/local/bin/entrypoint.sh"]
