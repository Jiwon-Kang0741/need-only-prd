# CPMS 차세대 구축용 용어집

> 본 문서는 CPMS(Compliance Management System, 준법경영관리시스템) 프로젝트에서 사용하는 용어를 정리한 것으로,  
> 차세대 구축 시 **소스명**, **Controller**, **Service**, **Dto**, **Mapper** 등 네이밍에 공통 적용할 목적으로 작성되었습니다.  
> 각 용어에 대해 **한글명**, **4~5자 직관적 약어**, **설명**을 제시합니다.

---

## 1. 모듈(업무) 접두어

| 한글명 | 약어(4~5자) | 설명 | 사용 예 |
|--------|-------------|------|---------|
| 실적/활동 | ACT | Activity, 실적관리·준법실천 활동 | ActController, ActService, ActDto |
| 점검/모니터링 | MON | Monitor, 준법점검·모니터링 | MonController, MonChkService |
| 실무/실천 | PRA | Practice, 목표수립·성과평가·서약 등 실무 | PraGoalService, PraApldgMapper |
| 교육 | EDU | Education, 교육과정·온라인·눈높이교육 등 | EduProgController, EduEyesDto |
| 센터/자료실 | CNR | Center, 자료실·콘텐츠 관리 | CnrRepoService, CnrAcontMapper |
| 시스템 | SYS | System, 시스템관리·메뉴·권한·로그·도움말 | SysLogService, SysBoardController |
| 상단/공통화면 | TOP | Top, 메인 공지·FAQ·통합검색 | TopNotiService, TopSearchDto |
| 서약/실천(수신) | RNM | Receipt/Renew, 서약·실천 수신·동의 | RnmPldgService, RnmPldcMapper |
| 정보/업무 | INF | Information, 업무정보·게시 등 | InfAcpwkService |
| 이벤트 | EVN | Event, 이벤트·퀴즈 등 | EvnQuizService |
| 공통 | CMN | Common, 로그인·게시판·권한·공통코드 | CmnConstants, BoardService |

---

## 2. 실적/활동(ACT) 도메인 용어

| 한글명 | 약어(4~5자) | 설명 | 사용 예 |
|--------|-------------|------|---------|
| 부서 | DEPT | Department, 실적대상 부서 | ActDeptController, CPTB_ACT_DEPT |
| 임원 | EXEC | Executive, 임원·부서장 | ActExecService, CPTB_ACT_EXEC |
| 관리 | MNG | Management, 실적관리·대표이사지전파 등 | ActMngService, ACT_MNG |
| 실적관리(통합) | AMNG | Activity Management | ActAmngService, ACT_AMNG |
| 부서(관리) | ADEPT | Activity Dept | ActAdeptService |
| 임원(관리) | AEXEC | Activity Exec | ActAexecService |
| 기준/표준 | CRT | Criterion/Standard (ACT 내) | ActCrtService, ACT_CRT |
| 기준(관리) | ACRT | Activity Criterion | ActAcrtService |
| 실천 | CONDUCT | Conduct, 준법실천 | ActConductService, CPTB_ACT_CONDUCT |
| 진행/프로그램 | PROG | Progress/Program, 활동진행 | ActProgService, ACT_PROG |
| 통계 | STAT | Statistics, 실적통계 | ActStatService, ACT_STAT |
| 사용자/개인별 | USER | User, 개인별 활동 | ActUserService, ACT_USER |
| 제안 | PRPS | Proposal, 개선제안 | ActPrpsService, ACT_PRPS_POP |
| 의지표명 | CMPL | Compliance (의지표명) | ActCmplService, ACT_CMPL |
| 실적탭 | RTAB | Result Tab | ACT_AMNG_RTAB |
| 강의 | LECT | Lecture | ACT_AMNG_LECT |
| 점검(팝업) | CHCK/CHEK | Check (팝업) | ACT_AMNG_CHCK |
| 증빙첨부 | ATCH_EVDN | Attachment Evidence | ActAtchEvdnService |
| 눈높이교육 | LVL_EDU | Level Education | ActLvlEduService |
| 임원강의 | EXEC_EDU | Executive Education | ActExecEduService |
| 참석/회의 | MEETING | Meeting, 준법실천자교육 참석 | ActMeetingService, CPTB_ACT_MEETING |
| 가이드 | GUID | Guide, 활동 가이드 | ActGuidService, ACT_GUID |
| 제안(게시) | ASUGG | Suggestion | ActAsuggService |
| 실적목록 | LIST | List, 실적 목록 테이블 | CPTB_ACT_LIST |
| 데이터 | DATA | Data, 자료(001/002 등) | ACT_DATA_001, ACT_DATA_002 |
| 기준표 | STANDARD | Standard, 활동 기준 | CPTB_ACT_STANDARD |
| 준법실천 | COMPLIANCE | Compliance | CPTB_ACT_COMPLIANCE |

---

## 3. 점검/모니터링(MON) 도메인 용어

| 한글명 | 약어(4~5자) | 설명 | 사용 예 |
|--------|-------------|------|---------|
| 일반 | GEN | General, 일반 점검 | MonGenService |
| 문제/이슈 | PRO | Problem | MonProService, CPTB_CHECK_PROBLEM |
| 주제/테마 | THM | Theme | MonThmService |
| 배포 | DPLY | Deploy, 점검 배포 | MonDplyService, CPTB_CHECK_DPLY |
| 배포(관리) | ADPLY | Admin Deploy | MonAdplyService |
| 점검문제 | APRO | Admin Problem | MonAproService |
| 설문 | SURVEY | Survey | MonSurveyService, CPTB_SURVEY_* |
| 점검문제(점검) | CPRO | Check Problem | MonCproService |
| 점검자 | ATHM | Authority/Checker | MonAthmService |
| 결과 | RSLT | Result, 점검 결과 | MonRsltService, MON_RSLT |
| 결과(관리) | ARSLT | Admin Result | MonArsltService |
| 점검 | CHK | Check | MonChkService, MON_CHK |
| 점검(상세) | LCHK | List/Detail Check | MonLchkService |
| 리스크 | RISK | Risk | MonRiskService |
| 점검대상자 | TRG_USER | Target User | CPTB_CHECK_TRG_USER |
| 점검실시자 | PRT_USER | Partner/Practice User | CPTB_CHECK_PRT_USER |
| 점검기준 | STANDARD | Check Standard | CPTB_CHECK_STANDARD |
| 점검문제 | PROBLEM | Check Problem | CPTB_CHECK_PROBLEM |
| 점검해결 | PRT_SOL | Partner Solution | CPTB_CHECK_PRT_SOL |
| 자가점검 | SELF_USER | Self Check User | CPTB_CHECK_SELF_USER |
| 설문목록/평가/결과 | SURVEY_LIST / SURVEY_EVAL / SURVEY_RESULT | Survey domain | CPTB_SURVEY_* |

---

## 4. 실무/목표(PRA) 도메인 용어

| 한글명 | 약어(4~5자) | 설명 | 사용 예 |
|--------|-------------|------|---------|
| 목표 | GOAL | Goal, CP 목표수립·성과평가 | PraGoalService, CPTB_PRT_GOALS |
| 신청/원서 | APLDG | Application/Pledge (출원·신청) | PraApldgService, PRA_APLDG |

---

## 5. 교육(EDU) 도메인 용어

| 한글명 | 약어(4~5자) | 설명 | 사용 예 |
|--------|-------------|------|---------|
| 온라인 | PONL | Online, 온라인교육 진행현황 | EduPonlService, CPTB_LMS_RESULT_LIST |
| 프로그램 | PROG | Program, 교육 프로그램 | EduProgService, CPTB_EDU_PROG |
| 프로그램(관리) | APROG | Admin Program | EduAprogService |
| 눈높이 | EYES | Eyes, 찾아가는 눈높이교육 | EduEyesService, CPTB_EDU_EYES |
| 동의/서약 | AGREE | Agreement | CPTB_EDU_AGREE, EDU_AGREE_USER |
| 서약 | PLEDGE | Pledge | CPTB_EDU_PLEDGE |
| 실천 | CONDUCT | Conduct, 교육 실천 | CPTB_EDU_CONDUCT |

---

## 6. 센터/자료실(CNR) 도메인 용어

| 한글명 | 약어(4~5자) | 설명 | 사용 예 |
|--------|-------------|------|---------|
| 자료실 | REPO | Repository | CnrRepoService, CNR_REPO |
| 콘텐츠/결재콘텐츠 | ACONT | Article Content | CnrAcontService, CNR_ACONT |
| 관리 | MNG | Center Management | CPTB_CNR_MNG |
| 결재 | APPR | Approval | CPTB_BOARD_APPR, CPTB_CNR_MNG_APPR |
| 조건 | COND | Condition | CPTB_BOARD_COND |

---

## 7. 시스템(SYS) 도메인 용어

| 한글명 | 약어(4~5자) | 설명 | 사용 예 |
|--------|-------------|------|---------|
| 로그 | LOG | Log, 관리/메뉴/사용자 로그 | SysLogService, CPTB_MNG_LOG |
| 게시판 | BOARD | Board | SysBoardService, CPTB_BOARD |
| 도움말 | HELP | Help | SysHelpService, CPTB_SYS_HELP |
| 메뉴 | MENU | Menu | CPTB_MENU, CPTB_SUB_MENU |
| 권한 | ROLE/AUTH | Role/Authority | SYS_ROLE_001, CPTB_AUTH, CPTB_USER_AUTH |
| 메뉴권한 | MENU_AUTH | Menu Authority | CPTB_MENU_AUTH |

---

## 8. 상단/공통(TOP) 도메인 용어

| 한글명 | 약어(4~5자) | 설명 | 사용 예 |
|--------|-------------|------|---------|
| 공지 | NOTI | Notice | TopNotiService, TOP_NOTI |
| FAQ | FAQ | FAQ | TopFaqService, TOP_FAQ |
| 검색 | SEARCH | Search, 통합검색 | TopSearchService, TOP_SEARCH |

---

## 9. 서약/실천 수신(RNM) 도메인 용어

| 한글명 | 약어(4~5자) | 설명 | 사용 예 |
|--------|-------------|------|---------|
| 서약 | PLDG | Pledge | RnmPldgService, RNM_PLDG |
| 실천 | PLDC | Conduct | RnmPldcService, RNM_PLDC |

---

## 10. 정보/이벤트(INF, EVN) 도메인 용어

| 한글명 | 약어(4~5자) | 설명 | 사용 예 |
|--------|-------------|------|---------|
| 업무 | ACPWK | Affair/Work | InfAcpwkService, INF_ACPWK |
| 퀴즈 | QUIZ | Quiz | EvnQuizService, CPTB_QUIZ_* |

---

## 11. 공통/기술 용어

| 한글명 | 약어(4~5자) | 설명 | 사용 예 |
|--------|-------------|------|---------|
| 게시판 | BOARD | Board | CPTB_BOARD, BoardQuery |
| 게시판설정 | BOARD_SET | Board Setting | CPTB_BOARD_SET |
| 댓글 | COMT | Comment | CPTB_BOARD_COMT |
| 권한 | AUTH | Authority | CPTB_AUTH, AuthManagement |
| 사용자권한 | USER_AUTH | User Authority | CPTB_USER_AUTH |
| 메뉴권한 | MENU_AUTH | Menu Authority | CPTB_MENU_AUTH |
| 상세코드 | DTCD | Detail Code | CPTB_DTCD |
| 포인트마스터/상세 | POINT_MST / POINT_DTL | Point Master/Detail | CPTB_POINT_* |
| 로그인 | LOGIN | Login | LoginService, LoginQuery |
| 공통 | COMMON/CMN | Common | CommonService, CmnConstants |
| 인증관리 | AUTH_MGMT / AM | Auth Management | AuthManagementService |
| 게시관리 | BD | Board | BoardManagementService |
| 시스템관리 | SM | System Management | SystemManagementService |
| 용어관리 | ITRM | ITRM (기타관리) | ITRMManagementService |

---

## 12. 화면/처리 유형 (접미어)

| 한글명 | 약어(4~5자) | 설명 | 사용 예 |
|--------|-------------|------|---------|
| 목록 | LIST | List 화면/목록 조회 | *_LIST.xfdl, searchXxxList |
| 상세 | DTL | Detail, 상세 화면/조회 | *_DTL.xfdl, getXxxDtl |
| 저장/등록 | SAVE | Save, 등록·수정 화면 | *_SAVE.xfdl, saveXxx |
| 팝업 | POP | Popup | *_POP.xfdl, openXxxPop |
| 메인 | MAIN | Main | CNR_REPO_MAIN |
| 항목/아이템 | ITEM | Item | PRA_APLDG_ITEM |
| 편집 | EDIT | Edit | PRA_APLDG_EDIT |

---

## 13. 테이블/DB 접두어 규칙

| 접두어 | 의미 | 비고 |
|--------|------|------|
| CPTB_ | CPMS Table | 본 시스템 DB 테이블 공통 접두어 |
| CPVW_ | CPMS View | 뷰 |
| SQ_CPTB_ | Sequence | 시퀀스 (예: SQ_CPTB_MNG_LOG) |

---

## 14. 네이밍 적용 예시 (차세대)

- **Controller**: `ActDeptController`, `MonChkController`, `PraGoalController`
- **Service**: `ActDeptService`, `ActDeptServiceImpl`
- **Dto**: `ActDeptDto`, `ActDeptSaveDto`, `ActDeptListDto`
- **Mapper**: `ActDeptMapper`, `ActDeptMapper.xml`
- **엔티티**: `CptbActDept` (CPTB_ACT_DEPT 대응)
- **화면/리소스**: `act-dept-list`, `act-dept-dtl`, `act-dept-save`

---

*작성일: 2025년 기준 | 프로젝트: CPMS Online (cpms-online)*
