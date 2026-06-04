package com.common.exception;

/**
 * Standard business/system exception. Service methods wrap DAO calls and throw
 * {@code HscException.systemError("메시지", e)} (always pass the caught exception).
 */
public class HscException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public HscException(String message) {
        super(message);
    }

    public HscException(String message, Throwable cause) {
        super(message, cause);
    }

    public static HscException systemError(String message) {
        return new HscException(message);
    }

    public static HscException systemError(String message, Throwable cause) {
        return new HscException(message, cause);
    }
}
