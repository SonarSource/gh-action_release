FROM amazon/aws-cli:2.31.13@sha256:e14216fb361cce909ce199616711ad103182d5937f851cda9bebf25867d7180a

WORKDIR /
ADD ./ /

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "/entrypoint.sh"]
