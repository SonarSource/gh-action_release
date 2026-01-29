FROM python:3.14-slim@sha256:caa9622dab9a2b41c988cda23de8d13d52c328df79d9c341c36ff2e81728a828 AS build-env
ADD . /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install pipenv
RUN pipenv requirements > requirements.txt
RUN pip install --target=/app -r requirements.txt

FROM python:3.14-slim@sha256:caa9622dab9a2b41c988cda23de8d13d52c328df79d9c341c36ff2e81728a828
COPY --from=build-env /app /app

ENV PYTHONPATH=/app
ENTRYPOINT ["/usr/local/bin/python"]
CMD ["/app/release/main.py"]
