FROM amazon/aws-cli:2.32.30@sha256:89ee2f6c98d447b890f211c0c6b58347794fc9d6dd04fe9992d86cbf8779faa9

WORKDIR /
ADD ./ /

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "/entrypoint.sh"]
