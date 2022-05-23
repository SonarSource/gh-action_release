FROM python:3.7-slim AS build-env
ADD . /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install pipenv
RUN pipenv lock --requirements > requirements.txt
RUN pip install --target=/app -r requirements.txt

FROM gcr.io/distroless/python3-debian10
COPY --from=build-env /app /app

ENV PYTHONPATH=/app
CMD ["/app/main.py"]
