# syntax=docker/dockerfile:1.7

ARG JAVA_VERSION=21
ARG FLINK_VERSION=2.0.0

FROM eclipse-temurin:${JAVA_VERSION}-jdk AS builder

WORKDIR /src

COPY libraries/kafka-messages-proto libraries/kafka-messages-proto
COPY services/antifraud-service services/antifraud-service

WORKDIR /src/services/antifraud-service
RUN chmod +x gradlew
RUN --mount=type=cache,target=/root/.gradle \
    ./gradlew --no-daemon clean shadowJar -x test


FROM flink:${FLINK_VERSION}-java${JAVA_VERSION} AS runtime

COPY --from=builder /src/services/antifraud-service/app/build/libs/app-all.jar \
     /opt/flink/usrlib/antifraud-service.jar

LABEL org.opencontainers.image.source=https://github.com/isoldpower/power-finance-backend \
      org.opencontainers.image.title="power-finance-antifraud-service" \
      org.opencontainers.image.description="Flink job scoring events.async transactions for fraud."
