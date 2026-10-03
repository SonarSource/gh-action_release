FROM amazon/aws-cli:2.37.5@sha256:fb7ccfc7b4e3a05017e6c9ded4ba959b99af622130e211fb976c68c2f4d3f224

WORKDIR /
ADD ./ /

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "/entrypoint.sh"]
