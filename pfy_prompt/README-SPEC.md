# SPEC 파일 역할

| 파일 | 용도 |
|------|------|
| `spec.template.md` | Mockup → Spec LLM에 주입되는 **골격**(placeholder). `master_spec_prompt()`가 로드한다. |
| `spec.example.md` | 채워진 **참고 예시**. `POST /api/spec/load-file` 시 `spec.md`가 없으면 이 파일을 읽는다. |
| `spec.md` | 마지막 import/생성 결과 **캐시**. `.gitignore`에 있어 저장소에는 없을 수 있다. |

구조 변경 시 `spec.template.md`와 `spec.example.md`를 함께 맞춘다.
