# weekly-report references

NKIA AI 팀 주간보고 자동화에 필요한 참고 자료.

## Google OAuth client

이 skill은 Google OAuth client 파일을 번들하지 않습니다. GitHub push protection이 OAuth client ID/secret 패턴을 차단하므로, 각 사용자는 팀에서 별도로 받은 `client_secret.json`을 로컬에 배치해야 합니다.

```bash
mkdir -p ~/.config/gws
cp /path/to/team/client_secret.json ~/.config/gws/client_secret.json
gws auth login
```

필요 scopes:

- `https://www.googleapis.com/auth/spreadsheets`
- `https://www.googleapis.com/auth/calendar.readonly`
