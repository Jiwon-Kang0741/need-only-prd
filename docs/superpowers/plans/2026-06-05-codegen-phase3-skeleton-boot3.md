# Codegen Rewrite — Phase 3: Skeleton Boot3/Java21/jakarta Upgrade Plan

> **For agentic workers:** infra/config phase — verification is a Docker Maven compile (no local JVM). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Upgrade `skeleton/backend` from Spring Boot 2.7.18 / Java 11 / javax to **Spring Boot 3.5.x / Java 21 / jakarta** (BackendGuide §10.3 mandates `jakarta.validation.*`; §1.1 says Java 21 / Boot 3.5.9), so Phase-4 generated DTOs (jakarta validation annotations) compile.

**Architecture:** Modify the static skeleton template (pom, Dockerfile, vendored framework classes). The bare skeleton (Application + `aondev.framework.*` + `com.common.*`, no generated `biz.*` yet) must compile under Boot 3 / jakarta. Verified via a throwaway Docker `maven:3.9-eclipse-temurin-21` container running `mvn compile` (the only available JVM is in Docker).

**Tech Stack:** Spring Boot 3.5.x, Java 21, jakarta, MyBatis (mybatis-spring-boot-starter 3.x), Maven-in-Docker.

---

## Context / current state (verified)
- No local `java`/`mvn`; Docker daemon UP. ALL build verification = Docker.
- `skeleton/backend/pom.xml`: parent `spring-boot-starter-parent` **2.7.18**, `<java.version>11`, `mybatis-spring-boot-starter` **2.3.2**, deps: starter-web, postgresql, lombok, starter-validation, jackson-databind, joda-time. Explicit `spring-boot-maven-plugin` 2.7.18.
- `skeleton/backend/Dockerfile`: `maven:3.9-eclipse-temurin-11` builder + `eclipse-temurin:11-jre` runtime.
- Only javax usage in skeleton source: `aondev/framework/web/ServiceIdDispatcher.java` — `javax.annotation.PostConstruct`, `javax.servlet.http.HttpServletRequest`.

---

## Task 1: Upgrade pom.xml

**File:** `skeleton/backend/pom.xml`

- [ ] **Step 1:** Set parent version to a resolvable Boot 3.5.x. Try `3.5.9` first (guide §1.1). If the Docker compile (Task 4) reports it cannot be resolved, fall back to the latest resolvable `3.5.x`, else `3.4.x` — record which was used.
- [ ] **Step 2:** `<java.version>11</java.version>` → `<java.version>21</java.version>`.
- [ ] **Step 3:** `mybatis-spring-boot-starter` `2.3.2` → `3.0.4` (the Boot 3 / jakarta line; if 3.0.4 unresolvable, latest `3.0.x`).
- [ ] **Step 4:** `spring-boot-maven-plugin` — remove the explicit `<version>2.7.18</version>` so it inherits from the parent (keep the lombok exclude config).
- [ ] **Step 5:** Leave starter-web, starter-validation (now jakarta under Boot3), postgresql, lombok, jackson, joda-time as-is.

## Task 2: Upgrade Dockerfile

**File:** `skeleton/backend/Dockerfile`

- [ ] `maven:3.9-eclipse-temurin-11` → `maven:3.9-eclipse-temurin-21`; `eclipse-temurin:11-jre` → `eclipse-temurin:21-jre`. Keep the two-stage build as-is.

## Task 3: javax → jakarta in vendored classes

**File:** `skeleton/backend/src/main/java/aondev/framework/web/ServiceIdDispatcher.java`

- [ ] `import javax.annotation.PostConstruct;` → `import jakarta.annotation.PostConstruct;`
- [ ] `import javax.servlet.http.HttpServletRequest;` → `import jakarta.servlet.http.HttpServletRequest;`
- [ ] Re-sweep ALL skeleton java for any remaining `javax.` (validation/annotation/servlet) and convert to `jakarta.`:
  `grep -rn "javax\." skeleton/backend/src/main/java` must return EMPTY afterward.

## Task 4: Docker compile verification

- [ ] **Step 1:** From repo root, compile the skeleton in a JDK21 Maven container:
```bash
docker run --rm -v "$PWD/skeleton/backend":/app -w /app maven:3.9-eclipse-temurin-21 mvn -B -DskipTests compile
```
Expected: `BUILD SUCCESS`. (First run downloads Boot3 deps — minutes. That's fine.)
- [ ] **Step 2:** If it fails: read the error. Common fixes — Boot version not resolvable (adjust per Task 1 Step 1), mybatis starter version mismatch, a missed `javax.` import, or a vendored class using a Boot-2-only API. Fix the specific cause (skeleton only — never edit `pfy_prompt/`), re-run until `BUILD SUCCESS`.
- [ ] **Step 3:** Confirm `grep -rn "javax\." skeleton/backend/src/main/java` is empty and `grep -n "3\.\|21" skeleton/backend/pom.xml` shows the Boot3/java21 versions.

## Task 5: Commit

- [ ] Stage ONLY skeleton files (never `git add -A` — repo has unrelated noise):
```bash
git add skeleton/backend/pom.xml skeleton/backend/Dockerfile skeleton/backend/src/main/java/aondev/framework/web/ServiceIdDispatcher.java
git commit -m "$(printf 'feat(skeleton): upgrade to Spring Boot 3.5/Java21/jakarta (guide §10.3,§1.1)\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```
(If the javax sweep touched other files, include them in the add.)

---

## Self-Review
- Spec coverage: spec §7 (skeleton Boot3 upgrade) fully covered. Decision (locked): guide wins → jakarta/Boot3.
- Verification is real (Docker compile BUILD SUCCESS), not assumed.
- No `pfy_prompt/` edits. Only skeleton touched. Python pipeline untouched (Phase 4 wires generation to jakarta output).
- Record the exact Boot version + mybatis-starter version that compiled, for Phase 4/7.
