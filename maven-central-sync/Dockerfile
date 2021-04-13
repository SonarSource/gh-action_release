FROM maven:3-jdk-11-slim

#hack to cache
#RUN mvn org.sonatype.plugins:nexus-staging-maven-plugin:1.6.7:rc-list || exit 0

COPY settings.xml $MAVEN_CONFIG/settings.xml

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]