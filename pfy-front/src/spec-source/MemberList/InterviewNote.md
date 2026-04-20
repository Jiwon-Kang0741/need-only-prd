# InterviewNote

## 1. Basic Information

| 항목 | 값 |
|---|---|
| Screen Name | MemberList |
| Screen ID | SCR_MEMBERLIST_001 |
| Interview Date | 2026-04-20 |

## 2. Requirements Classification

### 2.1 Keep
| @id | Category | Requirement | Source |
|---|---|---|---|
| 해당 없음 | 해당 없음 | 해당 없음 | 해당 없음 |

### 2.2 Change
| @id | Category | Requirement | Source |
|---|---|---|---|
| 해당 없음 | 해당 없음 | 해당 없음 | 해당 없음 |

### 2.3 Add
| @id | Category | Requirement | Source |
|---|---|---|---|
| 해당 없음 | 해당 없음 | 해당 없음 | 해당 없음 |

### 2.4 Out of Scope
| @id | Category | Requirement | Source |
|---|---|---|---|
| OUT-001 | 데이터정의 | 회원 목록 컬럼 정의(데이터 타입, 최대 길이, 필수 여부, 마스킹 여부, 정렬 가능 여부), 상세 화면 기준 키 정의는 인터뷰 응답 부재로 본 범위에서 확정 불가 | Q1 |
| OUT-002 | 조회조건 | 회원 목록 필수 조회 조건, 입력 방식, 일치 방식, 대소문자 구분, 공백 처리 방식은 인터뷰 응답 부재로 본 범위에서 확정 불가 | Q2 |
| OUT-003 | 조회조건 | 목록 기본 정렬 1순위/2순위, 사용자 정렬 변경 허용 여부, 서버 정렬 고정 여부는 인터뷰 응답 부재로 본 범위에서 확정 불가 | Q3 |
| OUT-004 | 사용자행동 | 상세/등록 버튼 동작, 더블클릭 진입, 선택 방식, 등록 방식, 초기 입력 항목, 저장 시 필수값 검증 규칙은 인터뷰 응답 부재로 본 범위에서 확정 불가 | Q4 |
| OUT-005 | 사용자행동 | 삭제 방식(논리 삭제/물리 삭제), 단건/다건 삭제, 삭제 사유, 연관 데이터 존재 시 비활성 처리, 삭제 후 재조회, 감사로그 적재는 인터뷰 응답 부재로 본 범위에서 확정 불가 | Q5 |
| OUT-006 | 권한 | 조회/상세/등록/삭제/엑셀 다운로드 권한 분리, 역할별 버튼 노출, 조직 범위 제한, 개인정보 마스킹 권한 정책은 인터뷰 응답 부재로 본 범위에서 확정 불가 | Q6 |
| OUT-007 | 예외처리 | 미조회 상태/결과 없음 구분, 권한 없음 처리, 서버 오류/타임아웃 시 재시도 및 오류 코드 노출은 인터뷰 응답 부재로 본 범위에서 확정 불가 | Q7 |
| OUT-008 | 조회조건 | 페이지 크기 기본값, 페이지당 건수 변경, 총건수 정확도, 빈 페이지 보정 로직은 인터뷰 응답 부재로 본 범위에서 확정 불가 | Q8 |
| OUT-009 | 사용자행동 | 엑셀 다운로드 범위, 컬럼 구성, 파일명 규칙, 마스킹 적용, 다운로드 이력 저장, 대용량 비동기 처리 방식은 인터뷰 응답 부재로 본 범위에서 확정 불가 | Q9 |
| OUT-010 | 데이터정의 | 외부 연동 데이터 노출/검색 여부, 원천 시스템, 동기화 주기, 실시간 조회 여부, 장애 시 대체 표시값은 인터뷰 응답 부재로 본 범위에서 확정 불가 | Q10 |

### 2.5 TBD
| @id | Category | Requirement | Source |
|---|---|---|---|
| TBD-001 | 데이터정의 | 회원 목록 컬럼 정의 세부 명세 확정 필요 | Q1 |
| TBD-002 | 조회조건 | 검색 조건 및 검색 연산자 정의 필요 | Q2 |
| TBD-003 | 조회조건 | 기본 정렬 및 사용자 정렬 정책 정의 필요 | Q3 |
| TBD-004 | 사용자행동 | 상세/등록 동작 및 검증 규칙 정의 필요 | Q4 |
| TBD-005 | 사용자행동 | 삭제 정책 및 감사로그 처리 정의 필요 | Q5 |
| TBD-006 | 권한 | 기능별 권한 및 개인정보 노출 정책 정의 필요 | Q6 |
| TBD-007 | 예외처리 | 결과 없음/권한 없음/오류 처리 UX 정의 필요 | Q7 |
| TBD-008 | 조회조건 | 페이징 정책 및 총건수 처리 정의 필요 | Q8 |
| TBD-009 | 사용자행동 | 엑셀 다운로드 정책 정의 필요 | Q9 |
| TBD-010 | 데이터정의 | 외부 연동 데이터 사용 여부 및 연계 정책 정의 필요 | Q10 |

## 3. DataSpec

| Field Name | Type | Length | Required | Masking | Sortable | Description | Related @id |
|---|---|---:|---|---|---|---|---|
| memberPk | string | TBD | TBD | N | N | 상세 화면 이동 기준 내부 회원 PK 여부 미확정 | TBD-001 |
| memberNo | string | TBD | TBD | N | Y | 외부 노출용 회원번호 여부 및 사용 정책 미확정 | TBD-001 |
| memberId | string | TBD | TBD | N | Y | 회원ID 후보 컬럼, 최종 노출 여부 미확정 | TBD-001 |
| memberName | string | TBD | TBD | TBD | Y | 회원명 후보 컬럼, 마스킹 정책 미확정 | TBD-001, TBD-006 |
| loginId | string | TBD | TBD | TBD | Y | 로그인ID 후보 컬럼, 마스킹 정책 미확정 | TBD-001, TBD-006 |
| email | string | TBD | TBD | TBD | Y | 이메일 후보 컬럼, 마스킹 정책 미확정 | TBD-001, TBD-006 |
| mobileNo | string | TBD | TBD | TBD | Y | 휴대폰번호 후보 컬럼, 마스킹 정책 미확정 | TBD-001, TBD-006 |
| memberStatus | enum | TBD | TBD | N | Y | 회원상태 후보 컬럼, 코드값 정의 미확정 | TBD-001 |
| joinedAt | datetime | TBD | TBD | N | Y | 가입일시 후보 컬럼 | TBD-001 |
| lastLoginAt | datetime | TBD | TBD | N | Y | 최종접속일시 후보 컬럼 | TBD-001 |
| withdrawnYn | enum | 1 | TBD | N | Y | 탈퇴 여부 검색/표시 필요 여부 미확정 | TBD-002 |
| joinDateFrom | date | 10 | N | N | N | 가입일자 기간 검색 시작일 | TBD-002 |
| joinDateTo | date | 10 | N | N | N | 가입일자 기간 검색 종료일 | TBD-002 |
| page | number | TBD | Y | N | N | 현재 페이지 번호 | TBD-008 |
| pageSize | number | TBD | Y | N | N | 페이지당 건수 | TBD-008 |
| sortBy | string | TBD | N | N | N | 정렬 컬럼명 | TBD-003 |
| sortDirection | enum | 4 | N | N | N | 정렬 방향(asc/desc) | TBD-003 |
| ssoMemberNo | string | TBD | N | N | Y | SSO 회원번호 사용 여부 미확정 | TBD-010 |
| erpCustomerCode | string | TBD | N | N | Y | ERP 고객코드 사용 여부 미확정 | TBD-010 |
| crmGrade | enum | TBD | N | N | Y | CRM 등급 사용 여부 미확정 | TBD-010 |
| dormantYn | enum | 1 | N | N | Y | 휴면 여부 사용 여부 미확정 | TBD-010 |
| identityVerifiedYn | enum | 1 | N | N | Y | 본인인증 결과 사용 여부 미확정 | TBD-010 |

## 4. BusinessRules

| Rule Category | Rule | Related @id |
|---|---|---|
| Sorting | 기본 정렬 1순위/2순위 미정, 서버 정렬 고정 여부 미정 | TBD-003 |
| Sorting | 컬럼 헤더 클릭을 통한 사용자 정렬 변경 허용 여부 미정 | TBD-003 |
| Paging | 기본 페이지 크기 미정(후보: 10/20/50/100) | TBD-008 |
| Paging | 페이지당 건수 변경 허용 여부 미정 | TBD-008 |
| Paging | 총건수 정확 표시 여부 및 대용량 성능 제한 정책 미정 | TBD-008 |
| Paging | 마지막 페이지 빈 페이지 보정 로직 적용 여부 미정 | TBD-008 |
| Authorization | 조회/상세/등록/삭제/엑셀 다운로드 권한 분리 여부 미정 | TBD-006 |
| Authorization | 역할별 버튼 노출 정책 미정(운영자/상담원/정산담당자/읽기전용) | TBD-006 |
| Authorization | 본인 소속 조직 회원만 조회 가능 여부 미정 | TBD-006 |
| Authorization | 개인정보 컬럼 마스킹/비노출 정책 미정 | TBD-006 |
| Validation | 검색 조건별 입력 방식, 일치 방식, 대소문자 구분, 공백 처리 미정 | TBD-002 |
| Validation | 등록 시 초기 입력 항목 및 필수값 검증 규칙 미정 | TBD-004 |
| Validation | 삭제 사유 입력 필요 여부 미정 | TBD-005 |
| Deletion | 삭제 방식(논리 삭제/물리 삭제) 미정 | TBD-005 |
| Deletion | 단건/다건 삭제 허용 여부 미정 | TBD-005 |
| Deletion | 주문/정산/이력 연관 데이터 존재 시 비활성 처리 전환 여부 미정 | TBD-005 |
| Audit | 삭제 후 감사로그 적재 필요 여부 미정 | TBD-005 |
| Excel | 다운로드 범위(전체/검색결과 전체/현재 페이지) 미정 | TBD-009 |
| Excel | 다운로드 파일명 규칙, 마스킹 적용, 이력 저장, 대용량 비동기 처리 정책 미정 | TBD-009 |
| Exception | 최초 진입 미조회 상태와 검색 후 결과 없음 상태 구분 여부 미정 | TBD-007 |
| Exception | 권한 없음 시 접근 차단/안내 문구 정책 미정 | TBD-007 |
| Exception | 서버 오류/타임아웃 시 재시도 버튼 및 오류 코드 노출 정책 미정 | TBD-007 |
| Integration | 외부 연동 데이터의 원천 시스템, 동기화 주기, 실시간 조회 여부, 장애 대체값 정책 미정 | TBD-010 |

## 5. API Specification

| @id | API Name | Method | Endpoint | Request Params | Response Fields | Related @id |
|---|---|---|---|---|---|---|
| API-001 | 회원 목록 조회 | GET | /api/members | memberName(string, like), loginId(string, like), email(string, like), mobileNo(string, like), memberStatus(string, equal), withdrawnYn(string, equal), joinDateFrom(date, gte), joinDateTo(date, lte), page(number, equal), pageSize(number, equal), sortBy(string, equal), sortDirection(string, equal) | items(array), memberPk(string), memberNo(string), memberId(string), memberName(string), loginId(string), email(string), mobileNo(string), memberStatus(string), joinedAt(datetime), lastLoginAt(datetime), withdrawnYn(string), totalCount(number), page(number), pageSize(number) | TBD-001, TBD-002, TBD-003, TBD-008 |
| API-002 | 회원 상세 조회 | GET | /api/members/{memberKey} | memberKey(string, equal) | memberPk(string), memberNo(string), memberId(string), memberName(string), loginId(string), email(string), mobileNo(string), memberStatus(string), joinedAt(datetime), lastLoginAt(datetime), withdrawnYn(string), ssoMemberNo(string), erpCustomerCode(string), crmGrade(string), dormantYn(string), identityVerifiedYn(string) | TBD-001, TBD-004, TBD-010 |
| API-003 | 회원 등록 | POST | /api/members | memberId(string, equal), memberName(string, equal), loginId(string, equal), email(string, equal), mobileNo(string, equal), memberStatus(string, equal) | memberPk(string), memberNo(string), resultCode(string), resultMessage(string) | TBD-004 |
| API-004 | 회원 수정 | PUT | /api/members/{memberKey} | memberKey(string, equal), memberName(string, equal), email(string, equal), mobileNo(string, equal), memberStatus(string, equal) | memberPk(string), resultCode(string), resultMessage(string) | TBD-004 |
| API-005 | 회원 삭제/비활성 처리 | PATCH | /api/members/{memberKey}/status | memberKey(string, equal), memberStatus(string, equal), deleteReason(string, equal) | memberPk(string), memberStatus(string), resultCode(string), resultMessage(string) | TBD-005 |
| API-006 | 회원 일괄 삭제/비활성 처리 | PATCH | /api/members/status | memberKeys(array, in), memberStatus(string, equal), deleteReason(string, equal) | processedCount(number), failedCount(number), resultCode(string), resultMessage(string) | TBD-005 |
| API-007 | 회원 상태 코드 조회 | GET | /api/common-codes/member-status | codeGroup(string, equal) | code(string), codeName(string), sortOrder(number), useYn(string) | TBD-001, TBD-002 |
| API-008 | 엑셀 다운로드 | GET | /api/members/excel | memberName(string, like), loginId(string, like), email(string, like), mobileNo(string, like), memberStatus(string, equal), withdrawnYn(string, equal), joinDateFrom(date, gte), joinDateTo(date, lte), downloadScope(string, equal) | fileId(string), fileName(string), downloadUrl(string), maskedYn(string), resultCode(string) | TBD-009, TBD-006 |
| API-009 | 엑셀 다운로드 이력 저장 | POST | /api/members/excel-logs | fileName(string, equal), downloadScope(string, equal), conditionJson(string, equal), maskedYn(string, equal) | logId(string), resultCode(string), resultMessage(string) | TBD-009 |
| API-010 | 외부 연동 회원 속성 조회 | GET | /api/members/{memberKey}/external-attributes | memberKey(string, equal) | ssoMemberNo(string), erpCustomerCode(string), crmGrade(string), dormantYn(string), identityVerifiedYn(string), syncStatus(string) | TBD-010 |

## 6. Open Issues

| @id | Issue | Action Needed |
|---|---|---|
| TBD-001 | 회원 목록 컬럼, 타입, 길이, 필수 여부, 마스킹 여부, 정렬 가능 여부, 상세 이동 키 미확정 | 업무 담당자 인터뷰 재수행 및 화면 컬럼 명세 확정 |
| TBD-002 | 검색 조건, 입력 방식, 일치 방식, 대소문자, 공백 처리 정책 미확정 | 검색 조건 정의서 작성 및 승인 필요 |
| TBD-003 | 기본 정렬 우선순위 및 사용자 정렬 정책 미확정 | 정렬 정책 수립 및 성능 검토 필요 |
| TBD-004 | 상세/등록 동작, 선택 방식, 등록 방식, 저장 검증 규칙 미확정 | 사용자 시나리오 및 등록 정책 확정 필요 |
| TBD-005 | 삭제 방식, 다건 처리, 삭제 사유, 연관 데이터 처리, 감사로그 미확정 | 데이터 거버넌스 및 운영 정책 확정 필요 |
| TBD-006 | 기능별 권한, 조직 범위, 개인정보 마스킹 정책 미확정 | 권한 매트릭스 및 개인정보 처리 기준 확정 필요 |
| TBD-007 | 결과 없음/권한 없음/오류/타임아웃 UX 미확정 | 예외처리 UX 시나리오 정의 필요 |
| TBD-008 | 페이지 크기, 총건수, 빈 페이지 보정 정책 미확정 | 페이징 정책 및 성능 기준 확정 필요 |
| TBD-009 | 엑셀 다운로드 범위, 파일 규칙, 마스킹, 이력, 비동기 처리 미확정 | 다운로드 운영 정책 및 보안 기준 확정 필요 |
| TBD-010 | 외부 연동 데이터 사용 여부 및 연계 기준 미확정 | 연동 시스템 담당자 협의 및 인터페이스 정책 확정 필요 |