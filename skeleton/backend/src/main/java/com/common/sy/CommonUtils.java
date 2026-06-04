package com.common.sy;

import java.util.ArrayList;
import java.util.List;

/** Common helpers for generated services. */
public final class CommonUtils {

    private CommonUtils() {
    }

    /**
     * Filter grid rows by their status. Best-effort: reads each row's
     * {@code getStatus()} and matches it (case-insensitive) to the GridStatus name.
     * Rows without a getStatus() accessor are skipped.
     */
    public static <T> List<T> filterByStatus(List<T> rows, GridStatus status) {
        List<T> result = new ArrayList<>();
        if (rows == null) {
            return result;
        }
        for (T row : rows) {
            try {
                Object value = row.getClass().getMethod("getStatus").invoke(row);
                if (value != null && status.name().equalsIgnoreCase(String.valueOf(value))) {
                    result.add(row);
                }
            } catch (ReflectiveOperationException ignore) {
                // no getStatus() — skip
            }
        }
        return result;
    }
}
