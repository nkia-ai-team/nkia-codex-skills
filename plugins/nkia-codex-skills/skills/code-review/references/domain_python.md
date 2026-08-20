# Domain Checklist — Python (FastAPI / ai_portal 등)

코드 리뷰 시 변경된 파일이 Python (`.py`)이면 [code_review_ruleset.md](code_review_ruleset.md) Section 5에 더해 본 체크리스트를 적용합니다.

각 항목은 룰셋 명시 위반이므로 발견 시 confidence 80 이상으로 보고 가능합니다.

---

## 1. 언어 관용구

- [ ] **Mutable default argument 금지** — `def f(x=[])` 류는 호출 간 상태 누수. `None` 후 함수 내 초기화로 교체
- [ ] **Bare `except:` 금지** — 항상 구체 예외 타입 명시. `except Exception` 도 최대한 좁힐 것
- [ ] **`==` vs `is`** — None / True / False 비교는 `is` 사용
- [ ] **Comprehension 우선** — 단순 루프+`append`는 list/dict comprehension으로
- [ ] **f-string** — `%` 포매팅 / `.format()` 대신 f-string
- [ ] **Type hints** — public 함수·메서드는 인자/반환 타입 힌트 필수 (mypy/pyright 기준)
- [ ] **dataclass / pydantic BaseModel** — DTO는 dict 대신 명시 모델 사용

## 2. async / await

- [ ] **이벤트 루프 차단 금지** — async 컨텍스트에서 `time.sleep`, blocking I/O 호출 금지 (`asyncio.sleep`, `aiohttp`, `httpx.AsyncClient` 사용)
- [ ] **DB 드라이버 정합성** — async 핸들러에서 sync 드라이버(`psycopg2`, sync `pymongo`) 호출 금지. async 드라이버(`asyncpg`, `motor`) 사용
- [ ] **`asyncio.gather` 예외 전파** — `return_exceptions=True` 사용 시 결과를 반드시 분기 처리
- [ ] **fire-and-forget 태스크** — `asyncio.create_task` 결과를 보관하지 않으면 GC로 사라질 수 있음. 참조 유지 + 예외 핸들러 부착
- [ ] **`await` 누락** — 코루틴 호출 후 `await` 빠뜨리면 즉시 실행 안 됨. 린터로 잡지 못한 케이스 의심

## 3. FastAPI / Pydantic

- [ ] **요청 검증 위임** — 직접 isinstance 검사 대신 Pydantic 모델로 검증. `Field(..., min_length=1, le=100)` 등 제약 활용
- [ ] **Pydantic v2 마이그레이션** — `BaseModel.dict()` → `model_dump()`, `BaseModel.parse_obj` → `model_validate`
- [ ] **응답 모델 명시** — `response_model=` 또는 반환 타입 힌트로 직렬화 스키마 고정 (민감 필드 노출 방지)
- [ ] **Depends 캐시** — `Depends(...)` 가 요청당 1회만 실행되도록 의존성 그래프 설계. 내부에서 또 호출 X
- [ ] **백그라운드 작업** — `BackgroundTasks`는 응답 후 동일 워커에서 실행. 무거운 작업은 Celery/큐로 위임
- [ ] **오류 응답** — `raise HTTPException(status_code=..., detail=...)` 사용. dict 직접 반환 금지

## 4. 보안

- [ ] **SQL Injection** — `execute(f"... {user_input}")` 금지. 파라미터 바인딩 사용
- [ ] **`eval` / `exec` / `pickle.loads`** — 사용자 입력에 절대 노출 금지
- [ ] **`subprocess shell=True`** — 사용자 입력과 결합 금지. 인자 리스트로 전달
- [ ] **Path traversal** — 사용자 입력 경로는 `Path.resolve()` 후 base 디렉토리 prefix 검증
- [ ] **YAML** — `yaml.load` 대신 `yaml.safe_load`
- [ ] **시크릿** — 코드에 하드코딩 금지. `os.getenv` + 시작 시 누락 검증

## 5. 성능 / 자원 관리

- [ ] **컨텍스트 매니저** — 파일/DB 커넥션/소켓은 반드시 `with` 또는 `async with`
- [ ] **N+1 (ORM)** — SQLAlchemy 사용 시 `selectinload`/`joinedload`로 사전 로딩
- [ ] **DB 세션 스코프** — request scope 외부로 세션 누수 X. FastAPI는 `Depends(get_db)` 패턴
- [ ] **JSON 직렬화 비용** — 큰 응답은 `orjson` 검토. 매 요청 `dataclass → dict → json` 다단 변환 지양
- [ ] **로깅** — 운영 코드에 `print` 금지. `logging` 모듈 사용. f-string 대신 `logger.info("x=%s", x)` 권장 (지연 평가)

## 6. 테스트 (pytest)

- [ ] **fixture 스코프** — `function`/`module`/`session` 의도적으로 선택. session 스코프 fixture가 mutable 상태를 공유하면 위험
- [ ] **`@pytest.mark.parametrize`** — 동일 로직 반복 테스트는 파라미터화
- [ ] **async 테스트** — `pytest-asyncio`의 `@pytest.mark.asyncio` 또는 `asyncio_mode = "auto"` 설정
- [ ] **외부 의존성 모킹** — 실 API/DB 호출 없는 단위 테스트는 `pytest-httpx`, `respx`, monkeypatch 활용
- [ ] **테스트 격리** — 모듈 레벨 전역 상태 변경 시 fixture로 setup/teardown 보장
- [ ] **저장소 규칙**: 저장소 가이드가 요구하면 테스트 케이스 ID와 결과를 매핑해 출력 (예: `[TC-XXX-001] ✅`)

## 7. 패키지 / 의존성 (uv)

- [ ] **패키지 도구 일관성** — 저장소가 `uv`를 사용하면 `pip install`로 우회하지 않음
- [ ] **버전 핀** — `pyproject.toml`에 의존성 추가 시 의도된 제약(`~=`, `>=`) 검토
- [ ] **lockfile 변경** — `uv.lock` diff가 의도와 일치하는지 확인 (transitive 대량 변경 주의)

---

## 출력 시 적용 예시

```markdown
#### `services/itsm_query.py:42-58`: 🔴 Critical · Confidence: 92/100 — async 핸들러에서 sync I/O

`requests.get(...)`이 async 함수 내부에서 호출되어 이벤트 루프를 차단합니다.
동시 요청 처리량이 worker 수만큼 제한됩니다.

**권장:** `httpx.AsyncClient`로 교체.
```
