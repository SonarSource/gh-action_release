FROM amazon/aws-cli:2.4.23@sha256:769137bc715840ec70782bc54bbb9e9acec503207998f616545c4fa7f59657ce

WORKDIR /
ADD ./ /

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "/entrypoint.sh"]
