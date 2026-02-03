FROM amazon/aws-cli:2.33.14@sha256:b4dad9a6eba9c7b8d076e36552ebacab9932a452ee3a7f137c3b0cc9281ee979

WORKDIR /
ADD ./ /

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "/entrypoint.sh"]
