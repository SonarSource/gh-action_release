FROM python:3.10-slim@sha256:e7a12cb51c3c52dd1385202633439671efc0c6ba4258436c81dad37f67816608 AS build-env
ADD . /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install pipenv
RUN pipenv requirements > requirements.txt
RUN pip install --target=/app -r requirements.txt

FROM python:3.10-slim@sha256:e7a12cb51c3c52dd1385202633439671efc0c6ba4258436c81dad37f67816608
COPY --from=build-env /app /app

ENV PYTHONPATH=/app
ENTRYPOINT ["/usr/local/bin/python"]
CMD ["/app/release/main.py"]
