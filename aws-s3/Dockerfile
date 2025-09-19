FROM amazon/aws-cli:2.28.9@sha256:37e982a117d0da3f662166e82d15cfe747fc7622b9ea72ac3698ee4e9615221b

WORKDIR /
ADD ./ /

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "/entrypoint.sh"]
