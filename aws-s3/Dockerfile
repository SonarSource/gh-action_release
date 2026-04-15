FROM amazon/aws-cli:2.34.28@sha256:d342da23236133bce0b638d1fa7a8ead91e016c61ad007035ef6ca08ea87fa67

WORKDIR /
ADD ./ /

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["sh", "/entrypoint.sh"]
