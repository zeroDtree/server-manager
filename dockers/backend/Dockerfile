# Stage 1: build
FROM maven:3.9-eclipse-temurin-21-alpine AS build
WORKDIR /workspace

# Cache dependencies separately from source code
COPY backend/gsad/pom.xml .
RUN mvn dependency:go-offline -q

COPY backend/gsad/src ./src
RUN mvn package -DskipTests -q

# Stage 2: runtime (reuse same Temurin base as build — avoids extra Docker Hub pull)
FROM maven:3.9-eclipse-temurin-21-alpine
WORKDIR /app

RUN apk add --no-cache curl \
    && addgroup -S gsad && adduser -S gsad -G gsad
USER gsad

COPY --from=build /workspace/target/gsad-*.war app.war

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.war"]
