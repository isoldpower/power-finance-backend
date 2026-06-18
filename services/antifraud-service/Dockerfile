# syntax=docker/dockerfile:1.7
# See ./README.md → "Build & Docker"

ARG JAVA_VERSION=21
ARG FLINK_VERSION=2.0.0

FROM eclipse-temurin:${JAVA_VERSION}-jdk AS builder

WORKDIR /src

# Proto bindings are consumed as a source dir (see app/build.gradle.kts).
COPY libraries/kafka-messages-proto libraries/kafka-messages-proto
COPY services/antifraud-service services/antifraud-service

WORKDIR /src/services/antifraud-service
RUN chmod +x gradlew
RUN --mount=type=cache,target=/root/.gradle \
    ./gradlew --no-daemon clean shadowJar -x test


# Flink provides the runtime; the slim job jar (Flink core excluded) goes in
# usrlib so the standalone-job entrypoint deploys it in Application Mode.
FROM flink:${FLINK_VERSION}-java${JAVA_VERSION} AS runtime

COPY --from=builder /src/services/antifraud-service/app/build/libs/app-all.jar \
     /opt/flink/usrlib/antifraud-service.jar

LABEL org.opencontainers.image.source=https://github.com/isoldpower/power-finance-backend \
      org.opencontainers.image.title="power-finance-antifraud-service" \
      org.opencontainers.image.description="Flink job scoring events.async transactions for fraud."
