# 명명 규칙 가이드

## 📋 개요

본 문서는 화면명을 기준으로 백엔드 코드의 명명 규칙을 정의합니다.

---

## 1. 기본 명명 형식

### 1.1 화면명 구성 원칙

```
[LV1메뉴][LV2메뉴][행위][역할]
```

- **구분자 없음**: 언더스코어(`_`)를 사용하지 않고 PascalCase로 연결
- **예시**: `CpmsEduRegLst`
  - `Cpms`: LV1 메뉴
  - `Edu`: LV2 메뉴
  - `Reg`: 행위 (등록)
  - `Lst`: 역할 (내역)

### 1.2 역할(Suffix) 분류

화면의 성격에 따라 아래 suffix를 사용합니다:

| 화면 유형 | Suffix | 설명 |
|---------|--------|------|
| 내역, 조회, 로그, 현황, 관리 | `Lst` | 목록 조회 화면 |
| 신청, 등록 | `Edit` | 등록/수정 화면 |
| 조회 팝업 | `SPopup` | 조회용 팝업 (Search Popup) |
| 등록/수정/삭제 팝업 | `EPopup` | CRUD 팝업 (Edit Popup) |

### 1.3 영문 약어 규칙

화면명을 간결하게 유지하기 위해 다음 약어를 사용합니다:

| 한글/영문 | 약어 | 예시 |
|----------|------|------|
| 공통 (Common) | `Cmn` | CmnCodeLst |
| 시스템 (System) | `Sys` | CmnSysLgnLogLst |
| 화면 (Screen) | `Scrn` | CmnScrnAccLogLst |
| 접속 (Access) | `Acc` | CmnScrnAccLogLst |
| 로그인 (Login) | `Lgn` | CmnSysLgnLogLst |
| 에러 (Error) | `Err` | CmnErrLogLst |
| 이메일 (Email) | `Eml` | CmnEmlSndLogLst |
| 발송 (Send) | `Snd` | CmnEmlSndLogLst |
| 다운로드 (Download) | `Dwn` | CmnGridDwnLogLst |
| 인터페이스 (Interface) | `If` | CmnIfRcvLst |
| 수신 (Receive) | `Rcv` | CmnIfRcvLst |
| 이력 (History) | `Hist` | CmnIfSndHistLst |
| 문서 (Document) | `Doc` | CmnDocFrmLst |
| 양식 (Form) | `Frm` | CmnDocFrmLst |
| 라벨 (Label) | `Lbl` | CmnLblLst |
| 메시지 (Message) | `Msg` | CmnMsgLst |
| 코드 (Code) | `Cd` | CmnCdLst |
| 사용자 (User) | `Usr` | CmnUsrLst |
| 부서 (Department) | `Dept` | CmnDeptLst |
| 권한 (Authority) | `Auth` | CmnAuthGrpLst |
| 그룹 (Group) | `Grp` | CmnAuthGrpLst |
| 메뉴 (Menu) | `Mnu` | CmnAuthGrpMnuLst |
| 역할 (Role) | `Rol` | CmnRolAuthLst |
| 게시판 (Board) | `Bbs` | CmnBbsLst |
| 설정 (Setting) | `Set` | CmnBbsSetLst |

---

## 2. 백엔드 클래스 명명 규칙

화면명을 기준으로 아래와 같이 백엔드 클래스를 생성합니다.

### 2.1 클래스 구조

각 화면당 아래 파일들이 생성됩니다:

```
화면명 + Dao (Interface)
화면명 + DaoImpl (구현체)
화면명 + Service (Interface)
화면명 + ServiceImpl (구현체)
화면명 + Mapper (XML)
화면명 + ReqDto (요청 Dto)
화면명 + ResDto (응답 Dto)
```

### 2.2 예시

화면명이 `CpmsEduRegLst`인 경우:

```java
// Interface
CpmsEduRegLstDao.java
CpmsEduRegLstService.java

// 구현체
CpmsEduRegLstDaoImpl.java
CpmsEduRegLstServiceImpl.java

// Mapper
CpmsEduRegLstMapper.xml

// Dto
CpmsEduRegLstReqDto.java
CpmsEduRegLstResDto.java
```

---

## 3. 메서드 명명 규칙

### 3.1 Service 계층 메서드

| 메서드명 | 용도 | 설명 |
|---------|------|------|
| `search` | 조회 | 데이터 조회 (단건/목록) |
| `save` | 저장 | 등록/수정/삭제 처리 |

**예시**:
```java
// CpmsEduRegLstService.java
CpmsEduRegLstResDto search(CpmsEduRegLstReqDto request);
void save(CpmsEduRegLstReqDto request);
```

### 3.2 Mapper 계층 메서드

| 메서드명 | 용도 | 사용 Dto |
|---------|------|----------|
| `select` | 조회 | ResDto |
| `insert` | 등록 | ReqDto |
| `update` | 수정 | ReqDto |
| `delete` | 삭제 | ReqDto |

**예시**:
```xml
<!-- CpmsEduRegLstMapper.xml -->
<select id="select" resultType="CpmsEduRegLstResDto">
  ...
</select>

<insert id="insert" parameterType="CpmsEduRegLstReqDto">
  ...
</insert>

<update id="update" parameterType="CpmsEduRegLstReqDto">
  ...
</update>

<delete id="delete" parameterType="CpmsEduRegLstReqDto">
  ...
</delete>
```

---

## 4. Dto 명명 및 사용 규칙

### 4.1 Dto 명명

```
화면명 + ReqDto   → 요청용 (CUD 작업)
화면명 + ResDto  → 응답용 (조회 작업)
```

### 4.2 Dto 사용 기준

**XML Mapper 기준**으로 Dto를 구분합니다:

| 작업 유형 | 사용 Dto | Mapper 메서드 |
|----------|----------|--------------|
| 조회 (Read) | ResDto | `select` |
| 등록 (Create) | ReqDto | `insert` |
| 수정 (Update) | ReqDto | `update` |
| 삭제 (Delete) | ReqDto | `delete` |

### 4.3 예시

```java
// 조회용
public class CpmsEduRegLstResDto {
    private String eduId;
    private String eduName;
    private String regDate;
    // ... getters and setters
}

// 등록/수정/삭제용
public class CpmsEduRegLstReqDto {
    private String eduId;
    private String eduName;
    private String userId;
    // ... getters and setters
}
```

---

## 5. 기술 스택

- **백엔드**: HONE21 프레임워크
- **프론트엔드**: Vue.js
- **데이터 전송**: ReqDto / ResDto (향후 Map 변환 고려 예정)

---

## 6. 명명 규칙 예시 모음

### 예시 1: 교육 등록 내역

| 항목 | 값 |
|-----|-----|
| 화면명 | `CpmsEduRegLst` |
| Dao | `CpmsEduRegLstDao` / `CpmsEduRegLstDaoImpl` |
| Service | `CpmsEduRegLstService` / `CpmsEduRegLstServiceImpl` |
| Mapper | `CpmsEduRegLstMapper.xml` |
| Dto | `CpmsEduRegLstReqDto` / `CpmsEduRegLstResDto` |

### 예시 2: 조회 팝업

| 항목 | 값 |
|-----|-----|
| 화면명 | `CpmsDeptSPopup` |
| Dao | `CpmsDeptSPopupDao` / `CpmsDeptSPopupDaoImpl` |
| Service | `CpmsDeptSPopupService` / `CpmsDeptSPopupServiceImpl` |
| Mapper | `CpmsDeptSPopupMapper.xml` |
| Dto | `CpmsDeptSPopupReqDto` / `CpmsDeptSPopupResDto` |

### 예시 3: 등록 화면

| 항목 | 값 |
|-----|-----|
| 화면명 | `CpmsUserEdit` |
| Dao | `CpmsUserEditDao` / `CpmsUserEditDaoImpl` |
| Service | `CpmsUserEditService` / `CpmsUserEditServiceImpl` |
| Mapper | `CpmsUserEditMapper.xml` |
| Dto | `CpmsUserEditReqDto` / `CpmsUserEditResDto` |

---

## 7. 체크리스트

새로운 화면 개발 시 아래 항목을 확인하세요:

- [ ] 화면명이 `[LV1메뉴][LV2메뉴][행위][역할]` 형식으로 구성되었는가?
- [ ] 영문 약어 규칙을 준수했는가? (섹션 1.3 참고)
- [ ] 역할 Suffix가 올바른가? (Lst / Edit / SPopup / EPopup)
- [ ] Dao, DaoImpl, Service, ServiceImpl, Mapper 파일이 모두 생성되었는가?
- [ ] ReqDto와 ResDto가 모두 생성되었는가?
- [ ] Service 메서드명이 `search`, `save`로 통일되었는가?
- [ ] Mapper 메서드명이 `select`, `insert`, `update`, `delete`로 통일되었는가?
- [ ] Dto가 적절하게 사용되었는가? (select → ResponseDto, insert/update/delete → RequestDto)

---

## 📎 엑셀 파일 생성 (공통화면_명명규칙.xlsx)

본 문서와 동일한 내용을 엑셀 시트로 쓰려면 프로젝트 폴더에서 아래를 실행하세요.

```bash
pip install -r requirements.txt
python build_naming_excel.py
```

생성 파일: `공통화면_명명규칙.xlsx` (시트: 개요, 역할/Suffix, 영문 약어, 백엔드 클래스, Service/Mapper 메서드, Dto 기준, 예시, 체크리스트, 기술스택, 문서이력)

---

## 📝 문서 이력

| 버전 | 날짜 | 작성자 | 내용 |
|-----|------|-------|------|
| 1.0 | 2026-02-13 | - | 초안 작성 |
| 1.1 | 2026-02-13 | - | 영문 약어 규칙 추가 |
| 1.1 | 2026-02-20 | - | 영문 약어 변경 Dto |

