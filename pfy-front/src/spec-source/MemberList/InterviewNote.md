# InterviewNote

## 1. Basic Information
| 항목 | 값 |
|---|---|
| 화면명 | 회원 목록 |
| 화면 ID | SCR_MEMBERLIST_001 |
| 인터뷰 일자 | 2026-04-20 |

## 2. Requirement Summary

### 2.1 Keep
| @id | 요구사항 |
|---|---|
| KEEP-001 | 기존 인터뷰 응답값이 모두 "ㅇ"로만 기재되어 있어 확정된 현행 유지사항을 식별할 수 없음 |
| KEEP-002 | 회원 목록 화면이 존재하며 회원 조회 업무를 수행하는 기본 목적은 유지 |

### 2.2 Change
| @id | 요구사항 |
|---|---|
| CHG-001 | 회원 핵심 필드(memberNo, memberName, loginId, mobileNo, memberStatus, emailVerifiedYn, joinDate)의 데이터 스펙을 명확히 정의 필요 |
| CHG-002 | 회원명, 로그인ID 검색의 매칭 방식(부분일치/전방일치/완전일치), 대소문자 구분, 공백/특수문자 처리 규칙 정의 필요 |
| CHG-003 | 회원상태 검색의 단일선택/복수선택 여부 및 이메일인증여부 검색 UI(체크박스/Y/N/전체) 정의 필요 |
| CHG-004 | 가입일 검색 기준일 의미, 기간 포함 여부, 시간 처리, From/To 단독 입력 허용 여부 정의 필요 |
| CHG-005 | 목록 기본 정렬, 사용자 정렬 변경 허용 여부, 정렬 가능 컬럼, 2차 정렬 기준 정의 필요 |
| CHG-006 | 상세 이동 및 삭제 수행 UX(행 클릭/선택 후 버튼/행별 버튼), 삭제 단건/다건 지원 여부 정의 필요 |
| CHG-007 | 조회/상세/등록/삭제/엑셀다운로드 기능별 권한 분리 및 개인정보 접근 통제 기준 정의 필요 |
| CHG-008 | 조회 결과 없음, 403, 500, 타임아웃 발생 시 화면 메시지 및 재시도/문의 UX 정의 필요 |
| CHG-009 | 회원 삭제 방식(물리/논리), 삭제 가능 조건, 확인 문구, 삭제 후 목록 갱신 방식 정의 필요 |
| CHG-010 | 엑셀 다운로드 범위, 최대 건수, 출력 컬럼, 라벨/코드 출력 기준, 마스킹, 외부 연계 데이터 범위 정의 필요 |

### 2.3 Add
| @id | 요구사항 |
|---|---|
| ADD-001 | 목록조회 API, 상세조회 API, 삭제 API, 엑셀 다운로드 API, 공통코드 조회 API 명세 추가 필요 |
| ADD-002 | 화면 필드별 DataSpec 문서화 필요 |
| ADD-003 | 정렬/페이징/권한/유효성 규칙을 포함한 Business Rule 문서화 필요 |
| ADD-004 | 검색조건 및 결과 컬럼에 대한 마스킹 정책 명시 필요 |
| ADD-005 | 삭제/다운로드 등 사용자 액션별 감사로그 기록 여부 확인 필요 |

### 2.4 Out of Scope
| @id | 요구사항 |
|---|---|
| OUT-001 | 회원 등록 화면의 상세 입력 항목 정의는 본 회원 목록 화면 범위 외 |
| OUT-002 | 회원 상세 화면의 레이아웃/세부 탭 구성은 본 인터뷰 범위 외 |
| OUT-003 | 외부 회원/인증 시스템의 내부 인터페이스 상세 프로토콜 정의는 본 화면 범위 외 |

### 2.5 TBD
| @id | 요구사항 |
|---|---|
| TBD-001 | memberNo의 DB 타입, 길이, 필수 여부, 유니크 여부, 숫자형/문자열 식별자 여부 미확정 |
| TBD-002 | memberName의 DB 타입, 길이, 필수 여부 미확정 |
| TBD-003 | loginId의 DB 타입, 길이, 필수 여부, 유니크 여부, 중복 허용 여부 미확정 |
| TBD-004 | mobileNo의 DB 타입, 길이, 필수 여부, 유니크 여부, 중복 허용 여부 미확정 |
| TBD-005 | memberStatus의 코드 체계, DB 타입, 길이, 필수 여부 미확정 |
| TBD-006 | emailVerifiedYn의 표현 방식(Y/N, Boolean), 필수 여부 미확정 |
| TBD-007 | joinDate의 업무 기준일(가입완료일/승인일/계정생성일) 및 DB 타입 미확정 |
| TBD-008 | 회원명/로그인ID 검색 연산자(Like/Prefix/Equal), 대소문자 민감도, trim 및 특수문자 처리 규칙 미확정 |
| TBD-009 | 회원상태 단일선택/복수선택 여부 미확정 |
| TBD-010 | 이메일인증여부 검색 UI가 체크박스인지 3상태 선택인지 미확정 |
| TBD-011 | 가입일 기간 검색의 포함 조건, 시간 보정 규칙, From/To 단독 입력 허용 여부 미확정 |
| TBD-012 | 기본 정렬 기준 및 헤더 정렬 허용 컬럼 미확정 |
| TBD-013 | 동일값 발생 시 2차 정렬 기준 미확정 |
| TBD-014 | 상세 이동 UX와 삭제 UX 및 다건 삭제 지원 여부 미확정 |
| TBD-015 | 기능별 권한 분리 모델, 탈퇴회원 조회 허용, 휴대폰번호 마스킹, 엑셀 다운로드 권한 미확정 |
| TBD-016 | 조회 결과 없음/권한 없음/서버 오류/타임아웃의 예외 메시지 및 처리 UX 미확정 |
| TBD-017 | 삭제가 논리삭제인지 물리삭제인지, 삭제 가능 조건, 삭제 후 페이지 유지 방식 미확정 |
| TBD-018 | 엑셀 다운로드 범위(전체 결과/현재 페이지), 최대 건수, 컬럼 구성, 출력 형식, 마스킹 여부 미확정 |
| TBD-019 | 외부 회원/인증 시스템 연계 데이터 존재 여부 및 연계 항목 미확정 |
| TBD-020 | 삭제/다운로드 감사로그 기록 요건 미확정 |

## 3. Functional Requirements
| 구분 | @id | 기능명 | 설명 | 관련 ID |
|---|---|---|---|---|
| 조회 | FR-001 | 회원 목록 조회 | 검색조건(memberName, loginId, memberStatus, emailVerifiedYn, joinDate 범위) 기반 목록 조회 | CHG-001, CHG-002, CHG-003, CHG-004, CHG-005, TBD-001, TBD-008, TBD-009, TBD-010, TBD-011, TBD-012 |
| 조회 | FR-002 | 회원 상세 이동 | 목록에서 선택한 회원의 상세 화면으로 이동 | CHG-006, TBD-014 |
| 삭제 | FR-003 | 회원 삭제 | 선택한 회원 삭제 처리 수행 | CHG-006, CHG-009, TBD-014, TBD-017 |
| 다운로드 | FR-004 | 엑셀 다운로드 | 조회 결과를 엑셀로 다운로드 | CHG-007, CHG-010, TBD-015, TBD-018 |
| 공통 | FR-005 | 코드 조회 | 회원상태, 이메일인증여부 등 조회조건/표시용 코드 조회 | ADD-001, TBD-005, TBD-006 |
| 예외처리 | FR-006 | 예외 메시지 표시 | 빈 결과, 권한 없음, 서버 오류, 타임아웃 시 적절한 메시지/행동 제공 | CHG-008, TBD-016 |
| 권한 | FR-007 | 기능별 권한 통제 | 조회/상세/등록/삭제/다운로드 및 개인정보 마스킹 권한 제어 | CHG-007, TBD-015 |
| 정렬/페이징 | FR-008 | 정렬 및 페이지 이동 | 기본 정렬, 사용자 정렬, 페이지 번호 및 건수 처리 | CHG-005, TBD-012, TBD-013 |

## 4. DataSpec
| 화면필드명 | 필드ID | 유형 | DB타입 | 길이 | 필수 | 유니크 | 표시형식 | 설명 | 관련 ID |
|---|---|---|---|---|---|---|---|---|---|
| 회원번호 | memberNo | 목록컬럼/상세키 | TBD | TBD | TBD | TBD | 텍스트 | 회원 식별자, 숫자형/문자열 여부 미확정 | CHG-001, TBD-001 |
| 회원명 | memberName | 검색조건/목록컬럼 | TBD | TBD | TBD | N | 텍스트 | 회원 실명 또는 표시명, 검색 연산자 미확정 | CHG-001, CHG-002, TBD-002, TBD-008 |
| 로그인ID | loginId | 검색조건/목록컬럼 | TBD | TBD | TBD | TBD | 텍스트 | 로그인 식별 ID, 중복 허용 여부 미확정 | CHG-001, CHG-002, TBD-003, TBD-008 |
| 휴대폰번호 | mobileNo | 목록컬럼 | TBD | TBD | TBD | TBD | 전화번호/마스킹 가능 | 개인정보 필드, 마스킹 권한 정책 필요 | CHG-001, CHG-007, TBD-004, TBD-015 |
| 회원상태 | memberStatus | 검색조건/목록컬럼 | TBD | TBD | TBD | N | 코드/라벨 | 회원 상태 코드값 및 라벨 체계 미확정 | CHG-001, CHG-003, TBD-005, TBD-009 |
| 이메일인증여부 | emailVerifiedYn | 검색조건/목록컬럼 | TBD | TBD | TBD | N | Y/N 또는 라벨 | 인증 여부 표현 및 검색 UI 미확정 | CHG-001, CHG-003, TBD-006, TBD-010 |
| 가입일 | joinDate | 검색조건/목록컬럼 | TBD | TBD | TBD | N | 일시(YYYY-MM-DD 또는 YYYY-MM-DD HH:mm:ss) | 업무 기준일 및 기간검색 규칙 미확정 | CHG-001, CHG-004, TBD-007, TBD-011 |
| 가입일 시작 | joinDateFrom | 검색조건 | DATE/DATETIME | TBD | N | N | 날짜선택 | 기간 검색 시작값, 단독 입력 허용 여부 미확정 | CHG-004, TBD-011 |
| 가입일 종료 | joinDateTo | 검색조건 | DATE/DATETIME | TBD | N | N | 날짜선택 | 기간 검색 종료값, 포함 조건 및 시간 보정 미확정 | CHG-004, TBD-011 |
| 페이지번호 | pageNo | 시스템 | INT | TBD | Y | N | 숫자 | 목록 페이징 요청 파라미터 | ADD-003 |
| 페이지크기 | pageSize | 시스템 | INT | TBD | Y | N | 숫자 | 목록 페이징 요청 파라미터 | ADD-003 |
| 정렬컬럼 | sortBy | 시스템 | VARCHAR | TBD | N | N | 텍스트 | 사용자 선택 정렬 컬럼 | CHG-005, TBD-012 |
| 정렬방향 | sortDirection | 시스템 | VARCHAR | 4 | N | N | ASC/DESC | 정렬 방향 | CHG-005, TBD-012 |

## 5. BusinessRules
| @id | 분류 | 규칙 |
|---|---|---|
| BR-001 | 정렬 | 기본 정렬 기준은 미확정이며 가입일 최신순/회원번호순/최근수정순 중 결정 필요 |
| BR-002 | 정렬 | 사용자 헤더 정렬 허용 여부 및 허용 컬럼 범위는 미확정 |
| BR-003 | 정렬 | 동일값 발생 시 2차 정렬 기준은 미확정 |
| BR-004 | 페이징 | 목록 조회는 pageNo, pageSize 기반 서버 페이징 필요 |
| BR-005 | 페이징 | 삭제 후 현재 페이지 유지 여부 또는 1페이지 재조회 여부는 미확정 |
| BR-006 | 권한 | 조회, 상세조회, 등록, 삭제, 엑셀다운로드 권한의 통합/분리 모델은 미확정 |
| BR-007 | 권한 | 탈퇴 회원 조회 허용 여부는 권한 정책에 따라 결정 필요 |
| BR-008 | 권한 | 휴대폰번호 노출/마스킹은 역할별 정책 정의 필요 |
| BR-009 | 권한 | 엑셀 다운로드 권한 대상(운영자/관리자 등)은 미확정 |
| BR-010 | 유효성 | 회원명 검색어의 Like/Prefix/Equal 규칙은 미확정 |
| BR-011 | 유효성 | 로그인ID 검색의 대소문자 구분 여부, trim 처리, 특수문자 처리 규칙은 미확정 |
| BR-012 | 유효성 | 회원상태 검색의 단일선택/복수선택 여부는 미확정 |
| BR-013 | 유효성 | 이메일인증여부 검색은 체크박스 또는 Y/N/전체 방식 중 미확정 |
| BR-014 | 유효성 | 가입일 기간 검색은 From/To 단독 입력 허용 여부 및 시작/종료 포함 조건 미확정 |
| BR-015 | 삭제 | 회원 삭제는 물리삭제/논리삭제 여부가 미확정 |
| BR-016 | 삭제 | 삭제 가능 대상 조건(상태, 로그인 이력 등)은 미확정 |
| BR-017 | 삭제 | 삭제 전 확인 문구와 삭제 후 재조회 방식은 미확정 |
| BR-018 | 다운로드 | 엑셀 다운로드는 조회조건 전체 결과/현재 페이지 기준 여부가 미확정 |
| BR-019 | 다운로드 | 최대 다운로드 건수 제한, 출력 컬럼, 코드/라벨 출력 기준, 마스킹 여부는 미확정 |
| BR-020 | 예외처리 | 빈 결과, 403, 500, 타임아웃에 대한 메시지/재시도/문의안내 수준은 미확정 |
| BR-021 | 감사로그 | 삭제 및 엑셀 다운로드 실행 시 감사로그 기록 여부는 미확정 |

## 6. UI Components
| 구분 | 컴포넌트 | 설명 | 관련 ID |
|---|---|---|---|
| 검색영역 | 회원명 입력 | 회원명 검색어 입력 필드 | CHG-002, TBD-008 |
| 검색영역 | 로그인ID 입력 | 로그인ID 검색어 입력 필드 | CHG-002, TBD-008 |
| 검색영역 | 회원상태 선택 | 단일/복수 선택 여부 미확정인 상태 선택 컴포넌트 | CHG-003, TBD-009 |
| 검색영역 | 이메일인증여부 선택 | 체크박스 또는 3상태 선택 컴포넌트 | CHG-003, TBD-010 |
| 검색영역 | 가입일 From/To | 기간 검색 날짜 선택 컴포넌트 | CHG-004, TBD-011 |
| 검색영역 | 조회 버튼 | 조건으로 목록 조회 실행 | FR-001 |
| 검색영역 | 초기화 버튼 | 검색조건 초기화, 제공 여부 상세 UX 미확정 | CHG-008, TBD-016 |
| 목록영역 | 회원 목록 테이블 | 회원번호, 회원명, 로그인ID, 휴대폰번호, 회원상태, 이메일인증여부, 가입일 표시 | CHG-001, TBD-001, TBD-018 |
| 목록영역 | 정렬 헤더 | 컬럼별 정렬 기능, 허용 범위 미확정 | CHG-005, TBD-012 |
| 목록영역 | 페이지네이션 | 페이지 이동 및 페이지 크기 선택 | FR-008 |
| 액션영역 | 상세 버튼/행 클릭 | 상세 이동 방식 미확정 | CHG-006, TBD-014 |
| 액션영역 | 삭제 버튼 | 단건/다건 삭제 방식 미확정 | CHG-006, CHG-009, TBD-014, TBD-017 |
| 액션영역 | 엑셀 다운로드 버튼 | 권한 기반 다운로드 실행 | CHG-007, CHG-010, TBD-015, TBD-018 |
| 메시지영역 | 빈 결과 메시지 | 조회 결과 없음 안내 | CHG-008, TBD-016 |
| 메시지영역 | 오류 메시지 | 403/500/타임아웃 안내 및 재시도 UX | CHG-008, TBD-016 |

## 7. API Specification
| @id | method | endpoint | purpose | requestParams | responseFields | relatedIds |
|---|---|---|---|---|---|---|
| API-001 | GET | /api/members | 회원 목록 조회 | memberName(String, TBD), loginId(String, TBD), memberStatus(String/List, IN or EQUAL), emailVerifiedYn(String, EQUAL), joinDateFrom(Date/DateTime, >=), joinDateTo(Date/DateTime, <=), pageNo(Integer, EQUAL), pageSize(Integer, EQUAL), sortBy(String, EQUAL), sortDirection(String, EQUAL) | items(Array), memberNo(String), memberName(String), loginId(String), mobileNo(String), memberStatus(String), memberStatusLabel(String), emailVerifiedYn(String), emailVerifiedLabel(String), joinDate(DateTime), totalCount(Integer), pageNo(Integer), pageSize(Integer) | CHG-001, CHG-002, CHG-003, CHG-004, CHG-005, CHG-007, TBD-001, TBD-008, TBD-009, TBD-010, TBD-011, TBD-012, TBD-015 |
| API-002 | GET | /api/members/{memberNo} | 회원 상세 조회 | memberNo(String, EQUAL) | memberNo(String), memberName(String), loginId(String), mobileNo(String), memberStatus(String), emailVerifiedYn(String), joinDate(DateTime) | CHG-006, TBD-001, TBD-014 |
| API-003 | DELETE | /api/members/{memberNo} | 회원 단건 삭제 | memberNo(String, EQUAL) | result(String), deletedMemberNo(String), deleteType(String), memberStatus(String), message(String) | CHG-006, CHG-009, TBD-014, TBD-017 |
| API-004 | DELETE | /api/members | 회원 다건 삭제 | memberNos(List<String>, IN) | result(String), deletedCount(Integer), failedCount(Integer), message(String) | CHG-006, CHG-009, TBD-014, TBD-017 |
| API-005 | GET | /api/members/excel | 회원 목록 엑셀 다운로드 | memberName(String, TBD), loginId(String, TBD), memberStatus(String/List, IN or EQUAL), emailVerifiedYn(String, EQUAL), joinDateFrom(Date/DateTime, >=), joinDateTo(Date/DateTime, <=), downloadScope(String, EQUAL) | fileName(String), fileUrl(String) | CHG-007, CHG-010, TBD-015, TBD-018 |
| API-006 | GET | /api/common-codes/member-status | 회원상태 코드 조회 | codeGroup(String, EQUAL) | code(String), codeName(String), sortOrder(Integer), useYn(String) | ADD-001, TBD-005 |
| API-007 | GET | /api/common-codes/email-verified | 이메일인증여부 코드 조회 | codeGroup(String, EQUAL) | code(String), codeName(String), sortOrder(Integer), useYn(String) | ADD-001, TBD-006, TBD-010 |
| API-008 | GET | /api/authorizations/screens/SCR_MEMBERLIST_001 | 화면 권한 조회 | screenId(String, EQUAL) | canSearch(Boolean), canViewDetail(Boolean), canCreate(Boolean), canDelete(Boolean), canDownloadExcel(Boolean), canViewWithdrawn(Boolean), mobileNoMaskingYn(Boolean) | CHG-007, TBD-015 |
| API-009 | POST | /api/audit-logs/downloads | 다운로드 감사로그 기록 | screenId(String, EQUAL), actionType(String, EQUAL), criteria(String, EQUAL) | result(String), logId(String) | ADD-005, TBD-020 |
| API-010 | POST | /api/audit-logs/deletions | 삭제 감사로그 기록 | screenId(String, EQUAL), actionType(String, EQUAL), targetIds(List<String>, IN) | result(String), logId(String) | ADD-005, TBD-020 |

## 8. Open Issues / TBD
| @id | 이슈 | 확인 필요사항 |
|---|---|---|
| TBD-001 | 회원번호 스펙 미확정 | 숫자형 키인지 문자열 식별자인지, 길이/유니크/필수 여부 확인 필요 |
| TBD-002 | 회원명 스펙 미확정 | DB 타입, 최대 길이, 필수 여부 확인 필요 |
| TBD-003 | 로그인ID 스펙 미확정 | DB 타입, 최대 길이, 필수 여부, 유니크 및 중복 허용 여부 확인 필요 |
| TBD-004 | 휴대폰번호 스펙 미확정 | DB 타입, 최대 길이, 필수 여부, 유니크 및 중복 허용 여부 확인 필요 |
| TBD-005 | 회원상태 코드 미확정 | 코드값, 라벨값, 정렬순서, 사용 여부 확인 필요 |
| TBD-006 | 이메일인증여부 스펙 미확정 | Y/N 코드인지 Boolean인지, 필수 여부 확인 필요 |
| TBD-007 | 가입일 기준일 미확정 | 가입완료일/관리자 승인일/최초 계정생성일 중 무엇인지 확인 필요 |
| TBD-008 | 문자열 검색 규칙 미확정 | memberName/loginId의 Like/Prefix/Equal, 대소문자, trim, 특수문자 처리 확인 필요 |
| TBD-009 | 회원상태 검색 UI 미확정 | 단일선택인지 복수선택인지 확인 필요 |
| TBD-010 | 이메일인증 검색 UI 미확정 | 체크박스인지 Y/N/전체 3상태 선택인지 확인 필요 |
| TBD-011 | 가입일 기간검색 규칙 미확정 | 시작/종료 포함 조건, 시간값 보정, From/To 단독입력 허용 확인 필요 |
| TBD-012 | 기본/사용자 정렬 미확정 | 기본 정렬과 사용자 변경 가능 정렬 컬럼 확인 필요 |
| TBD-013 | 2차 정렬 기준 미확정 | 동일값 발생 시 tie-breaker 컬럼 확인 필요 |
| TBD-014 | 상세/삭제 UX 미확정 | 행 클릭/선택 후 버튼/행별 버튼 및 단건·다건 삭제 지원 확인 필요 |
| TBD-015 | 권한/마스킹 정책 미확정 | 기능별 권한, 탈퇴회원 조회, 개인정보 노출, 다운로드 가능 대상 확인 필요 |
| TBD-016 | 예외 UX 미확정 | 빈 결과/403/500/타임아웃 메시지, 재시도 버튼, 문의안내 확인 필요 |
| TBD-017 | 삭제 업무규칙 미확정 | 물리/논리 삭제, 대상 조건, 확인 문구, 삭제 후 목록 재조회 방식 확인 필요 |
| TBD-018 | 엑셀 다운로드 규칙 미확정 | 다운로드 범위, 최대 건수, 출력 컬럼, 코드/라벨, 마스킹 확인 필요 |
| TBD-019 | 외부 연계 범위 미확정 | 외부 회원/인증 시스템 연계 데이터 존재 여부 및 항목 확인 필요 |
| TBD-020 | 감사로그 요건 미확정 | 삭제 및 다운로드 감사로그 기록 필요 여부 확인 필요 |

## 9. Assumptions
| @id | 가정 |
|---|---|
| ASM-001 | 인터뷰 응답이 모두 "ㅇ"로 기재되어 있어 본 문서는 확정 요구사항이 아닌 분석 관점의 정리 문서로 작성함 |
| ASM-002 | 회원 목록 화면은 일반적인 엔터프라이즈 목록 화면 패턴(검색조건, 테이블, 페이지네이션, 상세/삭제/다운로드 액션)을 따른다고 가정함 |
| ASM-003 | 회원상태 및 이메일인증여부는 코드성 데이터이므로 공통코드 또는 준하는 API 조회가 필요하다고 가정함 |
| ASM-004 | 개인정보 필드인 휴대폰번호는 역할에 따라 마스킹 또는 비마스킹 노출이 필요하다고 가정함 |
| ASM-005 | 삭제 및 엑셀 다운로드는 보안상 감사로그 대상일 가능성이 높다고 가정함 |