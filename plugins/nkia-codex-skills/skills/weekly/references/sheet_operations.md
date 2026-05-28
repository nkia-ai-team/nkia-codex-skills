# Google Sheets Operations

구글 시트 탭 탐색, 행 탐색, 셀 기록 로직을 정의합니다.

---

## 1. 스프레드시트 정보

| 항목 | 값 |
|------|---|
| 스프레드시트 ID | config의 `spreadsheetId` |
| 탭 이름 형식 | `YYYYMMDD` (예: `20260409`) |
| 템플릿 탭 | config의 `templateTabName`, 없으면 `템플릿` → `Template` → `template` 순서 |
| 헤더 행 | 3행 (보고자, 업무구분, 업무, 업무 내용, 투입시간, 업무 구분, 업무) |
| 데이터 시작 행 | 4행~ |

### 시트 컬럼 구조

| 컬럼 | 내용 | 영역 |
|------|------|------|
| A | 보고자 (이름) | 금주 업무 실적 |
| B | 업무구분 (드롭다운) | 금주 업무 실적 |
| C | 업무 (목표일, 진행율) | 금주 업무 실적 |
| D | 업무 내용 (상세) | 금주 업무 실적 |
| E | 투입시간 | 금주 업무 실적 (기록 안 함) |
| F | 업무 구분 (드롭다운) | 차주 업무 계획 |
| G | 업무 (차주 계획) | 차주 업무 계획 |

실제 시트 상단 구조:

| 행 | 내용 |
|---|---|
| 1 | `주간업무보고` |
| 2 | `금주 업무 실적`, `차주 업무 계획`, `총 업무시간` 섹션 헤더 |
| 3 | 컬럼 헤더 |
| 4+ | 보고자별 데이터 |

---

## 2. 탭(시트) 탐색

### 2.1 목요일 날짜로 탭 이름 생성

    thursdayDate = weekEnd  // data_collection.md에서 계산된 목요일
    tabName = thursdayDate.format("YYYYMMDD")  // 예: "20260409"

### 2.2 탭 존재 확인

스프레드시트의 시트 목록을 조회하여 해당 탭이 존재하는지 확인합니다. 탭이 없을 때 템플릿 복사를 해야 하므로 `sheetId`, `title`, `index`를 함께 조회합니다:

    gws sheets spreadsheets get \
      --params '{"spreadsheetId": "{spreadsheetId}", "fields": "sheets.properties(sheetId,title,index)"}'

응답에서 `sheets[].properties.title`을 순회하여 `tabName`과 일치하는 탭을 찾습니다.

**탭이 없는 경우:**

템플릿 탭을 복사해 새 주간 탭을 만듭니다. 빈 탭을 만드는 `addSheet`는 사용하지 않습니다. 빈 탭은 서식, 수식, 병합 셀, 드롭다운, 컬럼 폭을 보존하지 못합니다.

1. 템플릿 탭 후보를 정합니다.
   - config에 `templateTabName`이 있으면 그 값을 우선 사용합니다.
   - 없으면 `템플릿`, `Template`, `template` 순서로 찾습니다.
2. 시트 목록 응답에서 템플릿 탭의 `sheetId`를 찾습니다.
3. 템플릿 탭을 `duplicateSheet`로 복사하고 새 이름을 `tabName`으로 지정합니다:

       gws sheets spreadsheets batchUpdate \
         --params '{"spreadsheetId": "{spreadsheetId}"}' \
         --json '{
           "requests": [
             {
               "duplicateSheet": {
                 "sourceSheetId": {templateSheetId},
                 "newSheetName": "{tabName}"
               }
             }
           ]
         }'

4. 복사 후 시트 목록을 다시 조회해 `tabName`이 생성되었는지 확인합니다.
5. 생성된 탭에서 보고자 행 탐색을 계속합니다.

**템플릿 탭도 없는 경우:**

    ERROR: 탭 "{tabName}"을(를) 찾을 수 없고, 복사할 템플릿 탭도 없습니다.
    템플릿 후보: {templateTabName 또는 템플릿, Template, template}
    사용 가능한 최근 탭: {최근 5개 탭 이름 나열}
    해결: 시트에 템플릿 탭을 만들거나 weekly-report.json의 templateTabName을 실제 템플릿 탭 이름으로 설정해주세요.

**복사 중 이미 같은 이름의 탭이 생성된 경우:**

다른 사용자가 같은 시점에 탭을 만들었을 수 있습니다. 시트 목록을 다시 조회해 `tabName`이 존재하면 오류로 중단하지 말고 해당 탭을 사용합니다. 다시 조회해도 없으면 복사 실패로 보고하고 쓰기를 중단합니다.

---

## 3. 보고자 행 탐색

### 3.1 A열 읽기

해당 탭의 A열을 읽어 보고자 이름을 찾습니다:

    gws sheets spreadsheets values get \
      --params '{"spreadsheetId": "{spreadsheetId}", "range": "{tabName}!A4:A30"}'

### 3.2 이름 매칭

응답의 `values` 배열을 순회하여 config의 `reporterName`과 일치하는 셀을 찾습니다.

**매칭 규칙:**
- 정확한 문자열 매칭 (공백 trim 후 비교)
- 매칭된 셀의 행 번호를 `targetRow`로 저장

**이름을 찾을 수 없는 경우:**

    ERROR: A4:A30에서 "{reporterName}"을(를) 찾을 수 없습니다.
    config의 reporterName이 시트에 기재된 이름과 일치하는지 확인해주세요.
    A4:A30에 있는 이름 목록: {발견된 이름들}
    재설정: $weekly --reconfigure

---

## 4. 셀 기록

### 4.1 기존 데이터 확인

기록 전에 해당 행의 B~G열 현재 값을 읽어 기존 데이터가 있는지 확인합니다:

    gws sheets spreadsheets values get \
      --params '{"spreadsheetId": "{spreadsheetId}", "range": "{tabName}!B{targetRow}:G{targetRow}"}'

기존 데이터가 있으면 사용자에게 경고합니다:

    ⚠️ 이미 기록된 데이터가 있습니다:
    [B] 업무구분: 백로그
    [C] 업무: 1. RCA Agent ...
    ...

    덮어쓸까요? (y/n)

### 4.2 값 기록

사용자가 확인하면 `gws sheets +append` 대신 **특정 범위에 직접 쓰기**를 사용합니다:

    gws sheets spreadsheets values update \
      --params '{
        "spreadsheetId": "{spreadsheetId}",
        "range": "{tabName}!B{targetRow}:D{targetRow}",
        "valueInputOption": "USER_ENTERED"
      }' \
      --json '{
        "values": [["{B열값}", "{C열값}", "{D열값}"]]
      }'

    gws sheets spreadsheets values update \
      --params '{
        "spreadsheetId": "{spreadsheetId}",
        "range": "{tabName}!F{targetRow}:G{targetRow}",
        "valueInputOption": "USER_ENTERED"
      }' \
      --json '{
        "values": [["{F열값}", "{G열값}"]]
      }'

**주의사항:**
- E열(투입시간)은 건너뜁니다 → B~D와 F~G를 분리하여 기록
- `valueInputOption: "USER_ENTERED"` — 셀 내 줄바꿈(`\n`)이 올바르게 처리됨
- 드롭다운(B열, F열) 값은 기존 선택지와 정확히 일치해야 합니다

### 4.3 셀 내 줄바꿈

C, D, G열은 여러 줄 텍스트가 들어갑니다. Google Sheets에서 셀 내 줄바꿈은 `\n` 문자로 표현합니다.

JSON 전달 시:

    "1. RCA 멀티턴 후속 질문\n2. alarm_select_popup 렌더링\n3. ..."

---

## 5. 기록 검증

기록 후 해당 셀을 다시 읽어 정상적으로 기록되었는지 확인합니다:

    gws sheets spreadsheets values get \
      --params '{"spreadsheetId": "{spreadsheetId}", "range": "{tabName}!B{targetRow}:G{targetRow}"}'

기록한 값과 읽은 값이 일치하면 성공, 불일치하면 경고:

    WARN: 기록된 값이 예상과 다릅니다. 시트에서 직접 확인해주세요.

---

## 6. gws CLI 응답 파싱

모든 `gws` 명령어의 출력은 **JSON 형식**입니다. `jq`가 설치되어 있으면 파이프로 필터링할 수 있습니다:

    # 탭 이름 목록 추출
    gws sheets spreadsheets get \
      --params '...' | jq -r '.sheets[].properties.title'

    # 탭 이름과 sheetId 추출
    gws sheets spreadsheets get \
      --params '...' | jq -r '.sheets[].properties | "\(.title)\t\(.sheetId)"'

    # A열 값 추출
    gws sheets spreadsheets values get \
      --params '...' | jq -r '.values[][0]'

`jq`가 없으면 JSON 응답을 직접 파싱합니다.
