FROM amazon/aws-cli:2.36.43@sha256:d948ee299a7ffcaec0d6052a00b9f4c513c61cacfaedfe68b098c85808394441

WORKDIR /
ADD ./ /

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "/entrypoint.sh"]
