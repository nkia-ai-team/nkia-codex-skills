# Domain Checklist — React / TypeScript (NDS, UI 등)

코드 리뷰 시 변경된 파일이 `.tsx` / `.ts` (React 컨텍스트)이면 [code_review_ruleset.md](code_review_ruleset.md) Section 5에 더해 본 체크리스트를 적용합니다.

각 항목은 룰셋 명시 위반이므로 발견 시 confidence 80 이상으로 보고 가능합니다.

---

## 1. TypeScript 기본

- [ ] **`any` 사용 정당화** — 명시 이유 없이 `any` 도입 금지. 가능하면 `unknown` + 좁힘 사용
- [ ] **non-null assertion (`!`) 남용 금지** — null 가능성을 타입으로 좁히거나 옵셔널 체이닝(`?.`) 사용
- [ ] **`as` 캐스팅** — narrowing이 안 되는 곳에서만 사용. 가능한 type guard로 대체
- [ ] **public API 타입 명시** — 컴포넌트 props, hook 반환값, 외부 노출 함수에 타입 명시
- [ ] **enum vs union literal** — 단순 상수 집합은 `'a' | 'b' | 'c'` union 우선
- [ ] **discriminated union** — 상호 배타적 상태는 `kind` 필드로 좁히기 (boolean flag 조합 X)

## 2. React Hooks

- [ ] **dependency 배열 정확성** — `useEffect`/`useMemo`/`useCallback` deps에 사용한 모든 외부 식별자 포함. eslint `react-hooks/exhaustive-deps` 위반 금지
- [ ] **stale closure** — 핸들러가 오래된 state/prop을 참조 — `useRef` 또는 함수형 setState(`setX(prev => ...)`)로 회피
- [ ] **`useEffect` 데이터 페칭** — 가능하면 React Query / SWR 등 데이터 라이브러리로 대체. 직접 fetch는 cleanup·중복 호출·race condition 처리 필요
- [ ] **cleanup 누락** — subscription, setTimeout/Interval, AbortController는 effect cleanup에서 해제
- [ ] **조건부 hook 호출 금지** — hook은 항상 동일 순서로 호출
- [ ] **`useMemo`/`useCallback` 남용** — 모든 함수·값을 메모이즈하지 말 것. 실제 비용·재참조가 문제일 때만
- [ ] **custom hook 명명** — `use` 접두사 필수

## 3. 렌더링 / 상태

- [ ] **key prop** — 리스트는 안정적 고유 ID 사용. `index` 사용은 정렬·삽입·삭제 없는 경우만
- [ ] **불필요한 state** — 다른 state로 파생 가능한 값은 state 대신 계산식
- [ ] **prop drilling 깊이** — 3단 이상이면 Context / 상태 라이브러리 검토
- [ ] **immutability** — state 직접 mutate 금지 (`state.items.push(...)` X). 새 배열·객체 생성
- [ ] **controlled vs uncontrolled** — 한 입력에 둘을 섞지 말 것 (`value` 없이 `onChange`만 등 의도 명시)
- [ ] **Suspense / error boundary** — 비동기 컴포넌트는 fallback·에러 경계로 감쌀 것

## 4. 접근성 (a11y)

- [ ] **semantic HTML** — `<div onClick>` 대신 `<button>`. 인터랙티브 요소는 키보드 접근 가능해야 함
- [ ] **alt 텍스트** — `<img>`에 `alt` 의무. 장식용은 `alt=""`
- [ ] **label 연결** — form input은 `<label htmlFor>` 또는 `aria-label`
- [ ] **focus 관리** — 모달/팝오버 열릴 때 focus 이동, 닫힐 때 트리거로 복귀
- [ ] **role / aria-***** — semantic HTML로 표현되지 않는 위젯에만 보조적으로 사용
- [ ] **색상 대비** — WCAG AA 4.5:1 (텍스트), 3:1 (대형 텍스트)

## 5. 성능

- [ ] **리스트 가상화** — 100개 이상 리스트는 virtualization 검토 (react-window 등)
- [ ] **이미지 최적화** — 적절한 크기·포맷·`loading="lazy"`
- [ ] **bundle 영향** — 새 의존성 추가 시 size 영향 검토. tree-shaking 가능한 import 사용 (`import { x } from 'lib'`)
- [ ] **re-render 범위** — Context value를 매 렌더 새 객체로 만들면 모든 consumer 리렌더. memoize
- [ ] **중복 fetch** — 같은 데이터를 여러 컴포넌트에서 호출하면 캐시 레이어로 통합

## 6. 보안 (프론트)

- [ ] **`dangerouslySetInnerHTML`** — 사용자 입력은 sanitize (DOMPurify 등) 후에만
- [ ] **외부 링크 `rel`** — `target="_blank"`에는 `rel="noopener noreferrer"` 필수
- [ ] **시크릿** — API 키·토큰을 클라이언트 번들에 포함 금지. 백엔드 프록시 경유
- [ ] **localStorage 민감정보** — JWT 등 보관 시 XSS 노출 위험. httpOnly 쿠키 검토
- [ ] **URL 파라미터 트러스트 X** — 라우팅 파라미터·쿼리는 항상 검증·sanitize

## 7. NDS / 디자인 시스템

- [ ] **토큰 사용** — 색상·간격·폰트는 디자인 토큰 사용. 인라인 hex/px 금지
- [ ] **컴포넌트 재사용** — NDS에 동일 컴포넌트 있는데 자체 구현 금지. 누락된 variant는 NDS에 추가
- [ ] **Tailwind 클래스** — 매직 px 대신 토큰 기반 유틸리티 (`text-sm`, `gap-4` 등)
- [ ] **Headless UI 패턴** — NDS는 Headless UI + Tailwind 기반. 접근성·키보드 동작은 Headless UI에 위임

## 8. 테스트

- [ ] **Testing Library 쿼리** — `getByRole` 우선, `getByTestId`는 최후 수단
- [ ] **사용자 행위 기반** — 구현 디테일(state 이름, 클래스) 대신 화면 결과·인터랙션 검증
- [ ] **`act` 경고** — 비동기 업데이트는 `await waitFor` / `findBy*` / `userEvent` 사용
- [ ] **Playwright E2E** — 저장소 가이드가 요구하는 핵심 플로우는 Playwright로 검증

---

## 출력 시 적용 예시

```markdown
#### `components/UserList.tsx:34-42`: 🟡 Warning · Confidence: 88/100 — useEffect 의존성 누락

`useEffect`가 `userId`를 사용하지만 deps 배열이 `[]`로 비어 있어,
prop이 바뀌어도 fetch가 재실행되지 않습니다.

**권장:**
```tsx
useEffect(() => { fetchUser(userId) }, [userId])
```
또는 `react-query`의 `useQuery({ queryKey: ['user', userId], ... })`로 교체 검토.
```
