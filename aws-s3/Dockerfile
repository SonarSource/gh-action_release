FROM amazon/aws-cli:2.32.9@sha256:734684f3fc98bbac0e7796c34f44c375c01f05febac52a10649a55eef1e96c24

WORKDIR /
ADD ./ /

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "/entrypoint.sh"]
