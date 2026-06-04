package com.common.dto.base;

import java.io.Serializable;

import lombok.Data;

/**
 * Base class for request (search) DTOs. Carries paging input. Mapper XML reads
 * {@code #{pageSize}} / {@code #{pageStart}} (LIMIT / OFFSET), derived from
 * page/size so callers may send either page/size or the derived values.
 */
@Data
public class SearchBaseDto implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 페이지 번호 (1-base) */
    private int page = 1;

    /** 페이지 크기 */
    private int size = 10;

    /** LIMIT 값 — 페이지 크기 */
    public int getPageSize() {
        return this.size;
    }

    /** OFFSET 값 — (page-1) * size */
    public int getPageStart() {
        int p = this.page <= 0 ? 1 : this.page;
        return (p - 1) * this.size;
    }
}
