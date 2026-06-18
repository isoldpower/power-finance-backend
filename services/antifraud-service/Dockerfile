# syntax=docker/dockerfile:1.7
# See ./README.md → "Build & Docker"

ARG JAVA_VERSION=21

FROM eclipse-temurin:${JAVA_VERSION}-jdk AS builder

WORKDIR /src

# Proto bindings are consumed as a source dir (see app/build.gradle.kts).
COPY libraries/kafka-messages-proto libraries/kafka-messages-proto
COPY services/antifraud-service services/antifraud-service

WORKDIR /src/services/antifraud-service
RUN chmod +x gradlew
RUN --mount=type=cache,target=/root/.gradle \
    ./gradlew --no-daemon clean shadowJar -x test


FROM eclipse-temurin:${JAVA_VERSION}-jre AS runtime

RUN groupadd -r -g 1000 app \
 && useradd -r -u 1000 -g app -s /usr/sbin/nologin app

COPY --from=builder /src/services/antifraud-service/app/build/libs/app-all.jar \
     /usr/local/lib/antifraud-service.jar

USER app

ENTRYPOINT ["java", "-jar", "/usr/local/lib/antifraud-service.jar"]

LABEL org.opencontainers.image.source=https://github.com/isoldpower/power-finance-backend \
      org.opencontainers.image.title="power-finance-antifraud-service" \
      org.opencontainers.image.description="Flink job scoring events.async transactions for fraud."
