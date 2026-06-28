FROM amazon/aws-cli:2.35.11@sha256:749bfaf91d690b9a1768083822d620f96c19defdf9ca2dc227eb3695281fda5b

WORKDIR /
ADD ./ /

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "/entrypoint.sh"]
