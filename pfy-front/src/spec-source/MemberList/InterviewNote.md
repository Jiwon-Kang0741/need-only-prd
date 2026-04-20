# InterviewNote

## 1. Basic Information
| 항목 | 값 |
|---|---|
| Screen Name | MemberList |
| Screen ID | SCR_MEMBERLIST_001 |
| Interview Date | 2026-04-20 |

## 2. Keep
| @id | 분류 | 내용 | 근거 Q&A |
|---|---|---|---|
| 해당 없음 | Keep | 해당 없음 | 해당 없음 |

## 3. Change
| @id | 분류 | 내용 | 근거 Q&A |
|---|---|---|---|
| 해당 없음 | Change | 해당 없음 | 해당 없음 |

## 4. Add
| @id | 분류 | 내용 | 근거 Q&A |
|---|---|---|---|
| 해당 없음 | Add | 해당 없음 | 해당 없음 |

## 5. Out of Scope
| @id | 분류 | 내용 | 근거 Q&A |
|---|---|---|---|
| 해당 없음 | Out of Scope | 해당 없음 | 해당 없음 |

## 6. TBD
| @id | 분류 | 내용 | 근거 Q&A |
|---|---|---|---|
| TBD-001 | TBD | 회원 목록 표시 컬럼 우선순위 확정 필요 | Q1 |
| TBD-002 | TBD | 회원 목록 컬럼별 데이터 타입, 최대 길이, 필수 여부, 마스킹 여부 확정 필요 | Q1 |
| TBD-003 | TBD | 검색 조건 항목 구성 확정 필요 | Q2 |
| TBD-004 | TBD | 검색 조건별 입력 형식 및 일치 조건(Like/Equal) 확정 필요 | Q2 |
| TBD-005 | TBD | 상태/유형 검색의 단일선택/다중선택 여부 확정 필요 | Q2 |
| TBD-006 | TBD | 날짜 검색의 기간 조회 방식(시작일~종료일) 확정 필요 | Q2 |
| TBD-007 | TBD | 목록 기본 정렬 1순위/2순위 및 tie-breaker 필드 확정 필요 | Q3 |
| TBD-008 | TBD | 컬럼 헤더 기반 사용자 정렬 변경 허용 여부 확정 필요 | Q3 |
| TBD-009 | TBD | 목록 화면 사용자 액션(상세이동/등록/수정/삭제/상태변경/비밀번호 초기화/엑셀다운로드) 확정 필요 | Q4 |
| TBD-010 | TBD | 액션별 행 단위/일괄처리 여부 및 체크박스 컬럼 필요 여부 확정 필요 | Q4 |
| TBD-011 | TBD | 일괄처리 최대 건수 확정 필요 | Q4 |
| TBD-012 | TBD | 화면 조회 권한, 개인정보 열람 권한, 수정 권한, 엑셀 다운로드 권한 분리 여부 확정 필요 | Q5 |
| TBD-013 | TBD | 권한 없을 때 UX 정책(메뉴 비노출/버튼 비활성화/403/마스킹) 확정 필요 | Q5 |
| TBD-014 | TBD | 조회 결과 없음, 서버 오류, 타임아웃, 권한 없음, 잘못된 검색조건 입력 시 메시지 및 재시도 정책 확정 필요 | Q6 |
| TBD-015 | TBD | 반드시 구분 안내해야 하는 업무 오류 케이스 확정 필요 | Q6 |
| TBD-016 | TBD | 회원 상태 코드 체계(저장값/표시명/기본값/변경 가능 여부/이력 관리) 확정 필요 | Q7 |
| TBD-017 | TBD | 회원 유형 코드 체계(저장값/표시명/기본값/변경 가능 여부/이력 관리) 확정 필요 | Q7 |
| TBD-018 | TBD | 페이지 크기 정책(10 고정 또는 20/50/100 선택) 확정 필요 | Q8 |
| TBD-019 | TBD | total count 정확 조회 여부 및 대량 데이터 성능 정책 확정 필요 | Q8 |
| TBD-020 | TBD | 무한스크롤 전환 가능성 여부 확정 필요 | Q8 |
| TBD-021 | TBD | 엑셀 다운로드 범위(현재 페이지/전체 검색결과/선택 행) 확정 필요 | Q9 |
| TBD-022 | TBD | 엑셀 파일 컬럼 구성 및 개인정보 마스킹 적용 여부 확정 필요 | Q9 |
| TBD-023 | TBD | 엑셀 다운로드 사유 입력, 로그 저장, 최대 다운로드 건수 제한 확정 필요 | Q9 |
| TBD-024 | TBD | 목록 데이터의 원천 시스템 구성(회원 마스터 단독/타 시스템 조합) 확정 필요 | Q10 |
| TBD-025 | TBD | 표시 항목별 원천 시스템, 실시간 조회 여부, 동기화 주기, 값 불일치 시 우선 기준 확정 필요 | Q10 |

## 7. DataSpec
| 필드명 | 화면구성 | 타입 | 길이 | 필수 | 마스킹 | 설명 | 관련 @id |
|---|---|---|---|---|---|---|---|
| screenTitle | 화면 제목 | string | 100 | Y | N | 화면 제목, 현재 정의값은 MemberList | 해당 없음 |
| memberList | 목록 영역 | object[] | - | Y | N | 회원 목록 데이터 집합, 실제 컬럼 구성 미확정 | TBD-001, TBD-002 |
| memberList[].memberId | 목록 컬럼 후보 | string/number | TBD | TBD | TBD | 회원 식별자 후보 컬럼 | TBD-001, TBD-002 |
| memberList[].loginId | 목록 컬럼 후보 | string | TBD | TBD | TBD | 로그인 ID 후보 컬럼 | TBD-001, TBD-002, TBD-025 |
| memberList[].memberName | 목록 컬럼 후보 | string | TBD | TBD | TBD | 회원명 후보 컬럼 | TBD-001, TBD-002 |
| memberList[].email | 목록 컬럼 후보 | string | TBD | TBD | TBD | 이메일 후보 컬럼 | TBD-001, TBD-002 |
| memberList[].mobileNo | 목록 컬럼 후보 | string | TBD | TBD | TBD | 휴대전화 후보 컬럼 | TBD-001, TBD-002 |
| memberList[].memberTypeCode | 목록 컬럼 후보 | enum/string | TBD | TBD | TBD | 회원유형 코드 후보 컬럼 | TBD-001, TBD-002, TBD-017 |
| memberList[].memberTypeName | 목록 컬럼 후보 | string | TBD | TBD | N | 회원유형 표시명 후보 컬럼 | TBD-001, TBD-017 |
| memberList[].joinDatetime | 목록 컬럼 후보 | datetime | - | TBD | N | 가입일시 후보 컬럼 | TBD-001, TBD-002 |
| memberList[].statusCode | 목록 컬럼 후보 | enum/string | TBD | TBD | TBD | 회원상태 코드 후보 컬럼 | TBD-001, TBD-002, TBD-016 |
| memberList[].statusName | 목록 컬럼 후보 | string | TBD | TBD | N | 회원상태 표시명 후보 컬럼 | TBD-001, TBD-016 |
| memberList[].lastLoginDatetime | 목록 컬럼 후보 | datetime | - | TBD | N | 마지막 접속일시 후보 컬럼 | TBD-001, TBD-002, TBD-025 |
| search.memberName | 검색조건 후보 | string | TBD | N | N | 회원명 검색, 일치 조건 미확정 | TBD-003, TBD-004 |
| search.loginId | 검색조건 후보 | string | TBD | N | N | 로그인ID 검색, 일치 조건 미확정 | TBD-003, TBD-004 |
| search.email | 검색조건 후보 | string | TBD | N | TBD | 이메일 검색, 일치 조건 미확정 | TBD-003, TBD-004 |
| search.mobileNo | 검색조건 후보 | string | TBD | N | TBD | 휴대전화 검색, 일치 조건 미확정 | TBD-003, TBD-004 |
| search.statusCodes | 검색조건 후보 | string[] | TBD | N | N | 회원상태 검색, 단일/다중선택 미확정 | TBD-003, TBD-005, TBD-016 |
| search.memberTypeCodes | 검색조건 후보 | string[] | TBD | N | N | 회원유형 검색, 단일/다중선택 미확정 | TBD-003, TBD-005, TBD-017 |
| search.joinDateFrom | 검색조건 후보 | date | - | N | N | 가입일 시작일, 범위 조회 방식 미확정 | TBD-003, TBD-006 |
| search.joinDateTo | 검색조건 후보 | date | - | N | N | 가입일 종료일, 범위 조회 방식 미확정 | TBD-003, TBD-006 |
| sortBy | 목록 제어 | string | 50 | N | N | 정렬 필드 | TBD-007, TBD-008 |
| sortDirection | 목록 제어 | enum | 4 | N | N | asc/desc | TBD-007, TBD-008 |
| pageNo | 목록 제어 | number | - | Y | N | 페이지 번호 | TBD-018 |
| pageSize | 목록 제어 | number | - | Y | N | 페이지 크기 | TBD-018 |
| totalCount | 목록 제어 | number | - | N | N | 전체 조회 건수 | TBD-019 |
| selectionIds | 일괄처리 제어 | string[] | TBD | N | N | 선택 행 ID 목록 | TBD-010, TBD-011 |
| excelDownloadReason | 엑셀 다운로드 | string | TBD | N | N | 다운로드 사유 | TBD-023 |

## 8. BusinessRules
| @id | 구분 | 규칙 |
|---|---|---|
| TBD-026 | 정렬 | 기본 정렬 1순위/2순위 및 tie-breaker 필드는 미정이며 업무 확정 필요 |
| TBD-027 | 정렬 | 사용자의 컬럼 헤더 클릭 정렬 변경 허용 여부 미정 |
| TBD-028 | 페이징 | 페이지 크기 10 고정 여부 또는 20/50/100 선택 제공 여부 미정 |
| TBD-029 | 페이징 | total count를 항상 정확히 제공할지 여부 미정 |
| TBD-030 | 페이징 | 대량 데이터 시 무한스크롤 또는 대략 건수 정책 적용 여부 미정 |
| TBD-031 | 권한 | 화면 접근 권한, 개인정보 열람 권한, 수정 권한, 엑셀 다운로드 권한의 분리 정책 미정 |
| TBD-032 | 권한 | 권한 미보유 시 메뉴 비노출/버튼 비활성화/403 오류/마스킹 처리 중 적용 정책 미정 |
| TBD-033 | 유효성 | 검색 조건 항목별 입력 형식, Like/Equal 조건, 단일/다중선택 여부 미정 |
| TBD-034 | 유효성 | 날짜 검색의 시작일/종료일 범위 입력 규칙 미정 |
| TBD-035 | 유효성 | 잘못된 검색조건 입력 시 오류 메시지 및 재시도 정책 미정 |
| TBD-036 | 유효성 | 일괄처리 허용 여부 및 최대 처리 건수 미정 |
| TBD-037 | 유효성 | 엑셀 다운로드 범위, 마스킹 적용, 사유 입력, 최대 다운로드 건수 제한 미정 |
| TBD-038 | 코드 | 회원 상태 코드 체계 및 변경/이력 관리 규칙 미정 |
| TBD-039 | 코드 | 회원 유형 코드 체계 및 변경/이력 관리 규칙 미정 |
| TBD-040 | 데이터연계 | 회원 목록 데이터의 원천 시스템, 실시간성, 동기화 주기, 값 불일치 우선 기준 미정 |
| TBD-041 | 예외처리 | 조회 결과 없음, 서버 오류, 타임아웃, 권한 없음에 대한 사용자 안내 정책 미정 |

## 9. API Specification
| @id | method | endpoint | 목적 | requestParams | responseFields | relatedIds |
|---|---|---|---|---|---|---|
| API-001 | GET | /api/members | 회원 목록 조회 | memberName(string, TBD), loginId(string, TBD), email(string, TBD), mobileNo(string, TBD), statusCodes(string[], TBD), memberTypeCodes(string[], TBD), joinDateFrom(date, >=), joinDateTo(date, <=), sortBy(string, =), sortDirection(string, =), pageNo(number, =), pageSize(number, =) | items(object[]), items.memberId(string/number), items.loginId(string), items.memberName(string), items.email(string), items.mobileNo(string), items.memberTypeCode(string), items.memberTypeName(string), items.joinDatetime(datetime), items.statusCode(string), items.statusName(string), items.lastLoginDatetime(datetime), pageNo(number), pageSize(number), totalCount(number) | TBD-001, TBD-002, TBD-003, TBD-004, TBD-005, TBD-006, TBD-007, TBD-008, TBD-018, TBD-019, TBD-024, TBD-025 |
| API-002 | GET | /api/members/{memberId} | 회원 상세 조회 | memberId(string, =) | memberId(string/number), loginId(string), memberName(string), email(string), mobileNo(string), memberTypeCode(string), memberTypeName(string), joinDatetime(datetime), statusCode(string), statusName(string), lastLoginDatetime(datetime) | TBD-009 |
| API-003 | POST | /api/members | 회원 신규 등록 | body(object, =) | memberId(string/number), resultCode(string), resultMessage(string) | TBD-009 |
| API-004 | PUT | /api/members/{memberId} | 회원 정보 수정 | memberId(string, =), body(object, =) | memberId(string/number), resultCode(string), resultMessage(string) | TBD-009, TBD-012 |
| API-005 | DELETE | /api/members/{memberId} | 회원 삭제 | memberId(string, =) | memberId(string/number), resultCode(string), resultMessage(string) | TBD-009, TBD-012 |
| API-006 | PATCH | /api/members/{memberId}/status | 회원 상태 변경 | memberId(string, =), statusCode(string, =) | memberId(string/number), statusCode(string), resultCode(string), resultMessage(string) | TBD-009, TBD-016 |
| API-007 | POST | /api/members/{memberId}/password-reset | 회원 비밀번호 초기화 | memberId(string, =) | memberId(string/number), resultCode(string), resultMessage(string) | TBD-009, TBD-012 |
| API-008 | POST | /api/members/bulk-actions | 회원 일괄처리 | actionType(string, =), selectionIds(string[], IN) | processedCount(number), failedCount(number), resultCode(string), resultMessage(string) | TBD-010, TBD-011 |
| API-009 | GET | /api/members/excel | 회원 목록 엑셀 다운로드 | memberName(string, TBD), loginId(string, TBD), email(string, TBD), mobileNo(string, TBD), statusCodes(string[], TBD), memberTypeCodes(string[], TBD), joinDateFrom(date, >=), joinDateTo(date, <=), scope(string, =), selectionIds(string[], IN), reason(string, =) | fileName(string), fileUrl(string), downloadToken(string) | TBD-021, TBD-022, TBD-023 |
| API-010 | GET | /api/codes/member-statuses | 회원 상태 코드 조회 | useYn(string, =) | code(string), codeName(string), defaultYn(string), changeableYn(string), historyManagedYn(string) | TBD-016 |
| API-011 | GET | /api/codes/member-types | 회원 유형 코드 조회 | useYn(string, =) | code(string), codeName(string), defaultYn(string), changeableYn(string), historyManagedYn(string) | TBD-017 |

## 10. Open Issues
| @id | 이슈 |
|---|---|
| TBD-001 | 회원 목록 표시 컬럼 우선순위 미확정 |
| TBD-002 | 회원 목록 컬럼별 상세 속성(타입/길이/필수/마스킹) 미확정 |
| TBD-003 | 검색 조건 항목 구성 미확정 |
| TBD-004 | 검색 조건별 입력 형식 및 일치 조건 미확정 |
| TBD-005 | 상태/유형 검색 선택 방식 미확정 |
| TBD-006 | 날짜 범위 검색 방식 미확정 |
| TBD-007 | 기본 정렬 및 tie-breaker 미확정 |
| TBD-008 | 사용자 정렬 변경 허용 여부 미확정 |
| TBD-009 | 화면 액션 범위 미확정 |
| TBD-010 | 일괄처리 및 체크박스 컬럼 필요 여부 미확정 |
| TBD-011 | 일괄처리 최대 건수 미확정 |
| TBD-012 | 액션별 권한 분리 여부 미확정 |
| TBD-013 | 권한 부족 시 UX 정책 미확정 |
| TBD-014 | 오류/예외 메시지 정책 미확정 |
| TBD-015 | 업무상 구분 필요 오류 케이스 미확정 |
| TBD-016 | 회원 상태 코드 체계 미확정 |
| TBD-017 | 회원 유형 코드 체계 미확정 |
| TBD-018 | 페이지 크기 정책 미확정 |
| TBD-019 | total count 정책 미확정 |
| TBD-020 | 무한스크롤 전환 가능성 미확정 |
| TBD-021 | 엑셀 다운로드 범위 미확정 |
| TBD-022 | 엑셀 컬럼 및 마스킹 정책 미확정 |
| TBD-023 | 엑셀 다운로드 사유/로그/건수 제한 미확정 |
| TBD-024 | 데이터 원천 시스템 구성 미확정 |
| TBD-025 | 원천별 실시간성/동기화/우선 기준 미확정 |