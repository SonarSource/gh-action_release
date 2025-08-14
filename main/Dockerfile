FROM python:3.13-slim@sha256:201e1ab0af068a569a6b10fe680cb7532c17105e2e68d50aa33176350ab17c36 AS build-env
ADD . /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install pipenv
RUN pipenv requirements > requirements.txt
RUN pip install --target=/app -r requirements.txt

FROM python:3.13-slim@sha256:201e1ab0af068a569a6b10fe680cb7532c17105e2e68d50aa33176350ab17c36
COPY --from=build-env /app /app

ENV PYTHONPATH=/app
ENTRYPOINT ["/usr/local/bin/python"]
CMD ["/app/release/main.py"]
