FROM amazon/aws-cli:2.33.13@sha256:38a997fda6ecdb9acaafa9ebf9fdb21ef34b5b57ac896f3b3bd88a847e69b111

WORKDIR /
ADD ./ /

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "/entrypoint.sh"]
