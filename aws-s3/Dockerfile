FROM amazon/aws-cli:2.32.29@sha256:2b9488b700f14f5898e6d9b0119de7ba53848b344a23c279b48886e99493582e

WORKDIR /
ADD ./ /

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "/entrypoint.sh"]
