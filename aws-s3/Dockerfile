FROM amazon/aws-cli:2.36.34@sha256:cf1f5e5741c33f3fee383296ba8045b96b9eb93c3de017be6688fb00356352d7

WORKDIR /
ADD ./ /

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "/entrypoint.sh"]
