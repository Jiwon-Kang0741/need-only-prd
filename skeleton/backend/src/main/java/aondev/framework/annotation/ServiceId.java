package aondev.framework.annotation;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Service identifier — routes POST /online/mvcJson/{screenCode}-{method} to the
 * annotated method. value() = "{ScreenCode}/{methodName}".
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface ServiceId {
    String value();
}
