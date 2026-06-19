plugins {
    application
    id("com.gradleup.shadow") version "9.0.0"
}

repositories {
    mavenCentral()
}

dependencies {
    compileOnly(libs.flink.streaming)
    compileOnly(libs.flink.clients)
    compileOnly(libs.flink.connector.base)

    testImplementation(libs.junit.jupiter)
    testImplementation(libs.flink.streaming)
    testImplementation(libs.flink.clients)
    testImplementation("org.apache.flink:flink-test-utils:2.0.0")
    testImplementation("org.apache.flink:flink-streaming-java:2.0.0:tests")
    testImplementation("org.apache.flink:flink-runtime:2.0.0:tests")

    testRuntimeOnly("org.junit.platform:junit-platform-launcher")

    implementation(libs.guava)
    implementation(libs.flink.connector.kafka)
    implementation(libs.protobuf.java)
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}

application {
    mainClass = "com.powerfinance.antifraud.App"
}

sourceSets {
    main {
        java {
            srcDir("../../../libraries/kafka-messages-proto/generated/java")
        }
    }
}

tasks.named<JavaExec>("run") {
    classpath += configurations.compileOnly.get()
}

tasks.named<Test>("test") {
    useJUnitPlatform()
}
