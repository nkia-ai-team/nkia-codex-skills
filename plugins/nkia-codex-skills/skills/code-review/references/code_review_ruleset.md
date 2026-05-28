# AI 기반 MR 코드 리뷰 룰셋

본 문서는 Codex 등 AI 도구가 Pull Request / Merge Request 코드 리뷰를 수행할 때 따라야 할 규칙을 정의합니다.

CodeRabbit은 의존성이 아니라 품질 기준점입니다. Codex가 GitHub/GitLab CLI/API로 직접 수집한 PR/MR 데이터를 바탕으로, 상용 리뷰 도구 수준의 체계적인 코드 리뷰를 수행하는 것을 목표로 합니다.

---

## 1. 리뷰 수행 순서

AI 코드 리뷰는 다음 순서로 진행합니다:

```
1. 브랜치명 검증
2. 커밋 메시지 검증
3. MR 메타데이터 검토
4. 코드 변경 사항 분석
5. 품질/보안/성능 검토
6. 리뷰 결과 작성
```

---

## 2. 브랜치명 검증

### 2.1 검증 규칙

Linear 자동 생성 브랜치 형식을 권장하지만, Linear 이슈 없이 진행되는 standalone 작업도 허용합니다.

**정규식 패턴:**
```regex
^(?:(feature|bugfix|fix|hotfix|refactor|docs|test|config|chore|ci|build|perf)/(?:[A-Za-z]+-[0-9]+-)?[a-z0-9]+(?:-[a-z0-9]+)*|develop-[0-9]+(?:\.[0-9]+)*_[0-9]+-chat-[a-z0-9]+(?:-[a-z0-9]+)*)$
```

**검증 항목:**

| 항목 | 규칙 | 예시 |
|------|------|------|
| Type Prefix | feature, bugfix, fix, hotfix, refactor, docs, test, config, chore, ci, build, perf 중 하나 | `feature/` |
| Linear 이슈 번호 | 선택 항목. 있으면 `{팀키}-{이슈번호}` 형식 (대소문자 허용) | `nkiaai-129`, `NKIAAI-129` |
| 설명 | kebab-case, 소문자 | `improve-rca-logging-system` |
| UI repo standalone | `develop-10.x.y_z-chat-{function}` 형식 허용 | `develop-10.2.1_3-chat-filter` |

**예시:**
- `feature/nkiaai-129-improve-rca-logging-system-for-operator-readability`
- `bugfix/nkiaai-130-fix-login-error`
- `chore/cleanup-local-dev-scripts`
- `fix/login-error`
- `develop-10.2.1_3-chat-filter`

### 2.2 브랜치-작업 타입 일치 검증

| 브랜치 타입 | 허용되는 작업 |
|-------------|--------------|
| feature | 새로운 기능 추가 |
| bugfix | 버그 수정 |
| fix | 버그 수정 (`bugfix` alias) |
| hotfix | 긴급 운영 이슈 수정 |
| refactor | 리팩토링, 성능 개선 |
| docs | 문서 작업만 |
| test | 테스트 코드만 |
| config | 설정 파일만 |
| chore | 빌드/개발 편의/운영성 보조 작업 |
| ci | CI/CD 파이프라인 작업 |
| build | 빌드/패키징 작업 |
| perf | 성능 개선 |

### 2.3 리뷰 코멘트 예시

```markdown
## 브랜치명 검증

**브랜치:** `feature/nkiaai-129-api-diff-slack-notification`

| 항목 | 상태 | 비고 |
|------|------|------|
| Type Prefix | ✅ | feature |
| Linear 이슈 번호 | ✅ | nkiaai-129 |
| 네이밍 규칙 | ✅ | kebab-case 준수 |
| 타입-작업 일치 | ✅ | 새 기능 추가 작업 |
```

Linear 이슈 없이 진행되는 standalone 작업은 Linear 이슈 번호를 `➖ N/A`로 표시하고 경고/실패로 계산하지 않습니다.

---

## 3. 커밋 메시지 검증

### 3.1 검증 규칙

**정규식 패턴:**
```regex
^(?:[A-Za-z]+-[0-9]+ )?(Feat|Fix|Refactor|Cleanup|Chore|Wip|Revert|Style|Merge|Docs|Config|Dependency|Test|Build|Ci|Perf) : .+$
```

**검증 항목:**

| 항목 | 규칙 | 예시 |
|------|------|------|
| Linear 이슈 번호 | 선택 항목. 있으면 `{팀키}-{이슈번호}` 형식 (대소문자 허용) | `nkiaai-129`, `NKIAAI-129` |
| Type | 허용된 타입 키워드 | `Feat` |
| 구분자 | ` : ` (공백 포함 콜론) | ` : ` |
| 내용 | 한글/영문, 명확한 설명 | `API 변경 감지 시스템 구축` |

### 3.2 Type Keyword 검증

| Type | 용도 | 변경 범위 |
|------|------|----------|
| Feat | 새로운 기능 추가 | 신규 파일/메서드 추가 |
| Fix | 오류 수정 | 버그 수정 코드 |
| Refactor | 리팩토링/성능 개선 | 기존 코드 구조 변경 |
| Cleanup | 불필요한 코드 정리 | 파일/코드 삭제 |
| Chore | 개발 편의/운영성 보조 작업 | 로컬 스크립트, 자동 정리, 비기능성 유지보수 |
| Wip | 진행 중 작업 | 임시 커밋 (MR 시 지양) |
| Revert | 이전 변경 되돌리기 | revert 커밋 |
| Style | 코드 스타일 수정 | 포맷팅, 공백 등 |
| Merge | 병합 커밋 | merge commit |
| Docs | 문서 변경 | .md 파일 등 |
| Config | 설정 파일 변경 | 빌드/배포 설정 |
| Dependency | 의존성 변경 | 라이브러리 추가/업데이트 |
| Test | 테스트 코드 | *Test.java, *Spec.java |
| Build | 빌드/패키징 변경 | Gradle/Maven/npm build 설정 |
| Ci | CI/CD 변경 | pipeline, workflow, runner 설정 |
| Perf | 성능 개선 | 캐싱, 쿼리 최적화, 병목 개선 |

### 3.3 Linear 이슈 번호 검증

```
브랜치: feature/nkiaai-129-api-diff-notification
커밋: nkiaai-129 Feat : API 변경 감지 시스템 구축
      ^^^^^^^^^^
      브랜치와 커밋 양쪽에 있으면 동일해야 함
```

검증 규칙:
- 브랜치와 커밋 양쪽에 Linear 이슈 번호가 있으면 동일해야 합니다.
- 브랜치에 Linear 이슈 번호가 있는데 커밋에 없으면 경고로 표시합니다.
- 커밋에 Linear 이슈 번호가 있는데 브랜치에 없으면 경고로 표시합니다.
- 브랜치/제목/커밋 어디에도 Linear 이슈 번호가 없으면 standalone 작업으로 간주하고, Linear 이슈 번호 누락을 경고/실패로 계산하지 않습니다.

### 3.4 리뷰 코멘트 예시

```markdown
## 커밋 메시지 검증

**총 커밋 수:** 4개

| 커밋 | Linear 이슈 | Type | 상태 | 비고 |
|------|-------------|------|------|------|
| `nkiaai-129 Feat : API 변경 감지 시스템 구축` | ✅ | ✅ Feat | ✅ | - |
| `nkiaai-129 Fix : Slack 웹훅 URL 수정` | ✅ | ✅ Fix | ✅ | - |
| `nkiaai-129 Chore : bootRun 종료 시 포트 자동 정리` | ✅ | ✅ Chore | ✅ | - |
| `Docs : README 업데이트` | ➖ N/A | ✅ Docs | ✅ | standalone 작업 |

⚠️ **수정 필요:** Type/구분자/내용 형식이 깨졌거나, 존재하는 Linear 이슈 번호가 서로 불일치할 때만 표시합니다.
```

---

## 4. MR 메타데이터 검토

### 4.1 필수 항목 체크리스트

| 항목 | 필수 | 검증 내용 |
|------|------|----------|
| Title | ✅ | 명확한 설명. Linear 이슈 번호는 있으면 검증하고, standalone 작업이면 없어도 실패 처리하지 않음 |
| Description | ✅ | 기능 상세 설명 작성 |
| Part (FE/BE) | ✅ | 해당 파트 선택 |
| Target Branch | ✅ | develop (master 아님) |
| 연관 백로그 | 권장 | `#이슈번호` 형식 |
| 테스트 코드 | ✅ | 체크 여부 확인 |
| 정적 분석 | ✅ | 체크 여부 확인 |

### 4.2 변경 규모 검증

| 변경 라인 | 상태 | 권고 |
|----------|------|------|
| 1-200 | ✅ 적정 | - |
| 201-500 | ⚠️ 주의 | 분할 검토 권장 |
| 500+ | ❌ 과다 | MR 분할 필요 |

---

## 5. 코드 리뷰 체크리스트

### 5.1 코드 품질

#### 클린 코드 원칙
- [ ] **단일 책임 원칙 (SRP)** - 클래스/메서드가 하나의 책임만 가지는가?
- [ ] **메서드 길이** - 20줄 이하인가? 복잡한 경우 분리 필요
- [ ] **중복 코드** - DRY 원칙 준수, 기존 유틸리티 활용
- [ ] **네이밍** - 의미 있는 변수/메서드명 사용
- [ ] **매직 넘버** - 상수로 정의되어 있는가?

#### Java/Spring 특화
- [ ] **Optional 사용** - null 대신 Optional 활용
- [ ] **Stream API** - 적절한 활용, 과도한 체이닝 지양
- [ ] **Lombok** - 적절한 어노테이션 사용 (@Getter, @Builder 등)
- [ ] **의존성 주입** - 생성자 주입 사용 (@RequiredArgsConstructor)
- [ ] **불변성** - final 키워드 적절히 사용

### 5.2 보안 검토 (OWASP Top 10)

| 취약점 | 검토 항목 |
|--------|----------|
| Injection | SQL, NoSQL, Command, LDAP 인젝션 방지 |
| Broken Auth | 인증/세션 관리 적절성 |
| Sensitive Data | 민감 정보 노출 여부 (로그, 응답) |
| XXE | XML 외부 엔티티 처리 |
| Broken Access | 권한 검증 누락 |
| Security Misconfig | 보안 설정 오류 |
| XSS | 입력값 이스케이프 처리 |
| Deserialization | 안전하지 않은 역직렬화 |
| Known Vuln | 취약한 라이브러리 사용 |
| Logging | 로깅/모니터링 부족 |

**검토 코드 패턴:**
```java
// ❌ SQL Injection 취약
String query = "SELECT * FROM users WHERE id = " + userId;

// ✅ PreparedStatement 사용
@Query("SELECT u FROM User u WHERE u.id = :id")
User findById(@Param("id") Long id);

// ❌ 민감 정보 로깅
log.info("User password: {}", password);

// ✅ 민감 정보 마스킹
log.info("User login attempt: {}", maskEmail(email));
```

### 5.3 성능 검토

| 항목 | 검토 내용 |
|------|----------|
| N+1 Query | JPA 연관관계 로딩 전략 확인 |
| Index | 쿼리 대상 컬럼 인덱스 존재 |
| Pagination | 대량 데이터 페이징 처리 |
| Caching | 반복 조회 데이터 캐싱 |
| Async | 비동기 처리 적절성 |
| Connection Pool | 연결 풀 크기 적정성 |

**검토 코드 패턴:**
```java
// ❌ N+1 문제
@OneToMany(fetch = FetchType.LAZY)
private List<Order> orders;  // 루프에서 각각 쿼리 발생

// ✅ Fetch Join 사용
@Query("SELECT u FROM User u JOIN FETCH u.orders")
List<User> findAllWithOrders();

// ❌ 전체 조회
List<Entity> findAll();  // 데이터 증가 시 OOM

// ✅ 페이징 적용
Page<Entity> findAll(Pageable pageable);
```

### 5.4 테스트 코드 검토

| 항목 | 검토 내용 |
|------|----------|
| 테스트 존재 | 신규/변경 코드에 대한 테스트 존재 |
| 테스트 커버리지 | 주요 로직 80% 이상 커버 |
| 테스트 품질 | 의미 있는 검증 (assert) 포함 |
| Edge Case | 경계값, 예외 케이스 테스트 |
| Mock 적절성 | 외부 의존성 적절히 모킹 |

**테스트 네이밍 규칙:**
```java
// 패턴: {테스트대상}_{시나리오}_{예상결과}
@Test
void searchTraces_WithValidRequest_ReturnsTraceList() { }

@Test
void searchTraces_WithInvalidTimeRange_ThrowsException() { }
```

### 5.5 에러 처리

- [ ] **예외 처리** - 적절한 예외 타입 사용
- [ ] **에러 메시지** - 사용자 친화적 메시지
- [ ] **로깅** - 에러 상황 적절히 로깅
- [ ] **Fallback** - 장애 시 대체 로직 존재

```java
// ❌ 포괄적 예외 처리
catch (Exception e) {
    log.error("Error", e);
}

// ✅ 구체적 예외 처리
catch (ResourceNotFoundException e) {
    log.warn("Resource not found: {}", e.getResourceId());
    throw new ApiException(ErrorCode.NOT_FOUND, e.getMessage());
}
```

### 5.6 API 문서화

- [ ] **Controller @Tag** - API 그룹 설명
- [ ] **@Operation** - 메서드별 summary, description
- [ ] **@ApiResponse** - 응답 코드별 설명
- [ ] **DTO @Schema** - 필드별 설명, example

### 5.7 스킬 문서 리뷰 (SKILL.md, references/*.md)

**⚠️ CRITICAL: 스킬 문서는 AI의 동작을 직접 제어하는 프롬프트/지시이므로 일반 문서(README.md 등)와 다릅니다. 보안/성능/품질 체크리스트를 동일하게 적용합니다. "N/A (문서 변경)"으로 스킵하면 안 됩니다.**

#### 보안 관점
- [ ] **민감 정보 노출** - API 키, 토큰, 비밀번호가 예시/템플릿에 하드코딩되어 있지 않은가?
- [ ] **권한 상승** - 스킬이 AI에게 과도한 권한(파일 삭제, 시스템 명령 등)을 부여하지 않는가?
- [ ] **인젝션 가능성** - 사용자 입력이 그대로 명령어/API 호출에 삽입되는 지시가 있는가?
- [ ] **데이터 유출** - 스킬이 민감 데이터를 외부 서비스에 전송하도록 지시하지 않는가?

#### 성능 관점
- [ ] **API 호출 효율** - 불필요한 중복 API 호출이 지시되어 있지 않은가?
- [ ] **병렬 처리** - 독립적인 API 호출이 순차 실행으로 지시되어 있지 않은가?
- [ ] **페이지네이션** - 대량 데이터 조회 시 페이지네이션/제한이 고려되어 있는가?
- [ ] **무한 루프 가능성** - 재시도/반복 로직에 최대 횟수 제한이 있는가?

#### 품질 관점
- [ ] **지시 명확성** - 모호한 표현 없이 AI가 정확히 하나의 동작만 해석할 수 있는가?
- [ ] **예시 일관성** - 규칙 설명과 예시가 서로 모순되지 않는가?
- [ ] **에러 처리** - 실패 시나리오(API 실패, 데이터 없음 등)에 대한 지시가 있는가?
- [ ] **섹션 번호 정합성** - 섹션 번호가 순서대로 매겨져 있고 누락/중복이 없는가?

---

## 6. 리뷰 결과 작성 형식

### 6.1 전체 요약

````markdown
# MR 코드 리뷰 결과

```review-verdict
VERDICT: needs-fix
CRITICAL: 0
WARNING: 1
INFO: 0
AUTOFIX_SAFE: yes
BLOCKED_REASON: none
MANUAL_MERGE_REQUIRED: yes
```

## 요약

| 항목 | 결과 |
|------|------|
| 브랜치명 | ✅ Pass |
| 커밋 메시지 | ⚠️ 1건 수정 필요 |
| Diff 완전성 | ✅ Pass |
| Linear Scope | ✅ Pass 또는 ➖ N/A |
| 코드 품질 | ✅ Pass |
| 보안 | ✅ Pass |
| 성능 | ⚠️ 개선 권장 |
| 테스트 | ❌ 테스트 추가 필요 |

**전체 판정:** ⚠️ 수정 후 승인 권장
````

### 6.1.1 Structured Verdict Block

리뷰 코멘트 최상단에는 `$ship`이 파싱할 수 있는 fenced block을 반드시 포함합니다.

````markdown
```review-verdict
VERDICT: approved | needs-fix | blocked
CRITICAL: {number}
WARNING: {number}
INFO: {number}
AUTOFIX_SAFE: yes | partial | no
BLOCKED_REASON: none | {reason}
MANUAL_MERGE_REQUIRED: yes
```
````

판정 규칙:

| VERDICT | 조건 |
|---------|------|
| approved | Critical 0, Warning 0, Diff 완전성 Pass, blocking scope/security/test issue 없음. Linear 이슈가 없는 standalone 작업은 Linear Scope `N/A`여도 승인 가능 |
| needs-fix | Critical 또는 Warning이 있거나, 수정 후 재리뷰가 필요한 품질/보안/성능/테스트 이슈가 있음 |
| blocked | PR/MR 데이터 불완전, 인증 실패, diff 누락, 대용량 파일 조회 실패, Linear task ID가 있는데 scope 검증 불가가 치명적일 때 |

`approved`여도 merge/approve는 사람이 직접 수행합니다.

### 6.2 상세 코멘트 형식

```markdown
### 📁 파일: `TraceQueryController.java`

#### Line 45-50: 🔴 Critical - N+1 Query 문제

**현재 코드:**
```java
traces.forEach(trace -> {
    trace.getSpans().size();  // N+1 발생
});
```

**문제점:**
- 각 trace마다 개별 쿼리 발생
- 100개 trace 조회 시 101개 쿼리 실행

**권장 수정:**
```java
@Query("SELECT t FROM Trace t JOIN FETCH t.spans WHERE t.id IN :ids")
List<Trace> findByIdsWithSpans(@Param("ids") List<Long> ids);
```

---

#### Line 78: 🟡 Warning - 하드코딩된 값

**현재 코드:**
```java
if (size > 100) {
    throw new IllegalArgumentException("Size exceeded");
}
```

**권장 수정:**
```java
private static final int MAX_PAGE_SIZE = 100;

if (size > MAX_PAGE_SIZE) {
    throw new IllegalArgumentException("Page size cannot exceed " + MAX_PAGE_SIZE);
}
```

**수정 분류:** `autofix-safe`

---

### 📦 파일: `trace_callback.py` (대용량 파일)

> ℹ️ **대용량 파일**: diff가 축소되어 전체 내용을 별도 조회하여 리뷰했습니다.

#### 전체 리뷰 결과: 🟢 양호

- 파일 크기: +646 lines
- 신규 파일로 전체 내용 검토 완료
- 특이 사항 없음
```

### 6.3 심각도 레벨

| 레벨 | 아이콘 | 의미 | 조치 |
|------|--------|------|------|
| Critical | 🔴 | 버그, 보안 취약점 | 반드시 수정 |
| Warning | 🟡 | 개선 권장 사항 | 수정 권장 |
| Info | 🔵 | 제안, 스타일 | 선택적 수정 |
| Praise | 🟢 | 좋은 코드 | 칭찬/참고 |

### 6.3.1 자동 수정 분류

모든 Critical/Warning/Info 지적사항에는 아래 중 하나를 붙입니다.

| 분류 | 의미 |
|------|------|
| `autofix-safe` | Codex가 안전하게 수정 가능. 포맷, import, 상수화, 명확한 null check, 작은 테스트 보강 등 |
| `manual-required` | 아키텍처, DB schema, 외부 API contract, 제품 요구사항 판단이 필요 |
| `owner-decision` | 여러 해결책이 가능하고 owner 의사결정이 필요한 변경 |

### 6.4 리뷰 히스토리

**재리뷰 시 코멘트 하단에 히스토리 테이블을 포함합니다.**

최초 리뷰에서도 히스토리 섹션을 포함하여, 이후 재리뷰 시 기존 코멘트를 업데이트할 때 행을 추가합니다.

**시각 기준:**
- 모든 `일시` 값은 KST(UTC+9, `Asia/Seoul`) 기준으로 작성합니다.
- 형식은 `YYYY-MM-DD HH:mm KST`를 사용합니다.
- 시스템 timezone이 UTC여도 `TZ=Asia/Seoul date '+%Y-%m-%d %H:%M KST'`처럼 KST로 산출합니다.
- 기존 히스토리 행에 `UTC` 표기가 있으면 새 코멘트로 업데이트할 때 KST로 변환합니다.

```markdown
---

## 📜 리뷰 히스토리

| # | 일시 | 판정 | 이슈 (🔴/🟡/🔵) | 변화 |
|---|------|------|-----------------|------|
{{#each history}}
| {{attempt}} | {{datetime}} | {{verdict}} | {{critical}}/{{warning}}/{{info}} | {{change}} |
{{/each}}
```

**변화 컬럼 작성 규칙:**
- 최초 리뷰: `최초 리뷰`
- 재리뷰: 이전 대비 변화를 요약 (예: `🟡 1건 해소`, `🔴 2건 추가`, `모든 이슈 해소`)

**예시:**

```markdown
## 📜 리뷰 히스토리

| # | 일시 | 판정 | 이슈 (🔴/🟡/🔵) | 변화 |
|---|------|------|-----------------|------|
| 1 | 2026-03-03 20:00 KST | ⚠️ 수정 후 승인 권장 | 0/1/0 | 최초 리뷰 |
| 2 | 2026-03-03 20:30 KST | ✅ 승인 | 0/0/0 | 🟡 1건 해소 |
```
