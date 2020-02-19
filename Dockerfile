FROM python:3-slim AS build-env
ADD . /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install requests

FROM gcr.io/distroless/python3-debian10
COPY --from=build-env /app /app
COPY --from=build-env /usr/local/lib/python3.8/site-packages /usr/local/lib/python3.8/site-packages

WORKDIR /app
ENV PYTHONPATH=/usr/local/lib/python3.8/site-packages
CMD ["main.py"]