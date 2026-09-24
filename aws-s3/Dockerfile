FROM amazon/aws-cli:2.36.49@sha256:f42bf088cb1456ba9e179ce71fdeb22cc46ff64ea1e3aeae8251ff81391f5bb1

WORKDIR /
ADD ./ /

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "/entrypoint.sh"]
