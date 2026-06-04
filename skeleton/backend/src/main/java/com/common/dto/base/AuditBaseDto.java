package com.common.dto.base;

import java.io.Serializable;

import lombok.Data;

/**
 * Base class for response DTOs. Carries audit columns mapped from
 * insert_uid/insert_dt/update_uid/update_dt (see BackendGuide §4.7).
 */
@Data
public class AuditBaseDto implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 최초 생성자 ID (insert_uid) */
    private String fstCrtrId;

    /** 최초 생성 일시 (insert_dt) */
    private String fstCretDtm;

    /** 최종 수정자 ID (update_uid) */
    private String lastMdfrId;

    /** 최종 수정 일시 (update_dt) */
    private String lastMdfcDtm;
}
