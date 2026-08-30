FROM amazon/aws-cli:2.36.31@sha256:f0dcd994da5c36ab09becf4259bba4c45ed4ecfd03d51c701912f4d8425b2d49

WORKDIR /
ADD ./ /

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "/entrypoint.sh"]
