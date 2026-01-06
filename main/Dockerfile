FROM python:3.13-slim@sha256:1f3781f578e17958f55ada96c0a827bf279a11e10d6a458ecb8bde667afbb669 AS build-env
ADD . /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install pipenv
RUN pipenv requirements > requirements.txt
RUN pip install --target=/app -r requirements.txt

FROM python:3.13-slim@sha256:1f3781f578e17958f55ada96c0a827bf279a11e10d6a458ecb8bde667afbb669
COPY --from=build-env /app /app

ENV PYTHONPATH=/app
ENTRYPOINT ["/usr/local/bin/python"]
CMD ["/app/release/main.py"]
