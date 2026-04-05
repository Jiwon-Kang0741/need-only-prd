FROM maven:3.9-eclipse-temurin-11 AS builder
WORKDIR /app
COPY pom.xml .
RUN mvn -q dependency:go-offline || true
COPY src ./src
RUN mvn -q -DskipTests package

FROM eclipse-temurin:11-jre
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 8080
CMD ["java", "-jar", "app.jar"]
