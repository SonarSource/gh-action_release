FROM python:3.14-slim@sha256:3955a7dd66ccf92b68d0232f7f86d892eaf75255511dc7e98961bdc990dc6c9b AS build-env
ADD . /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install pipenv
RUN pipenv requirements > requirements.txt
RUN pip install --target=/app -r requirements.txt

FROM python:3.14-slim@sha256:3955a7dd66ccf92b68d0232f7f86d892eaf75255511dc7e98961bdc990dc6c9b
COPY --from=build-env /app /app

ENV PYTHONPATH=/app
ENTRYPOINT ["/usr/local/bin/python"]
CMD ["/app/release/main.py"]
