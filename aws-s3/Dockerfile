FROM amazon/aws-cli:2.36.2@sha256:964336bffb17b82d2e84a2526b0672e70a2c881544e1a281acaca1d9aa41b536

WORKDIR /
ADD ./ /

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "/entrypoint.sh"]
