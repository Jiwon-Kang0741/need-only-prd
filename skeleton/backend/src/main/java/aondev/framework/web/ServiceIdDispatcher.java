package aondev.framework.web;

import com.fasterxml.jackson.databind.ObjectMapper;
import aondev.framework.annotation.ServiceId;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.ApplicationContext;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.annotation.PostConstruct;
import javax.servlet.http.HttpServletRequest;
import java.io.BufferedReader;
import java.lang.reflect.Method;
import java.util.*;

/**
 * @ServiceId dispatcher. Scans all Spring beans for @ServiceId-annotated methods
 * and routes POST /online/mvcJson/{screenCode}-{methodName} to them. The registry
 * key is the @ServiceId value ("{ScreenCode}/{methodName}"); the URL uses a dash
 * between screen code and method (per the CPMS API convention).
 */
@Slf4j
@RestController
@RequiredArgsConstructor
public class ServiceIdDispatcher {

    private final ApplicationContext context;
    private final ObjectMapper objectMapper;

    private final Map<String, MethodTarget> registry = new HashMap<>();

    private static class MethodTarget {
        final Object bean;
        final Method method;
        final Class<?> paramType;
        MethodTarget(Object bean, Method method, Class<?> paramType) {
            this.bean = bean;
            this.method = method;
            this.paramType = paramType;
        }
    }

    @PostConstruct
    public void init() {
        for (String beanName : context.getBeanDefinitionNames()) {
            Object bean;
            try {
                bean = context.getBean(beanName);
            } catch (Exception e) {
                continue;
            }
            for (Method method : bean.getClass().getMethods()) {
                ServiceId ann = method.getAnnotation(ServiceId.class);
                if (ann == null) continue;
                Class<?> paramType = method.getParameterCount() > 0
                        ? method.getParameterTypes()[0]
                        : null;
                registry.put(ann.value(), new MethodTarget(bean, method, paramType));
                log.info("Registered @ServiceId: {}", ann.value());
            }
        }
        log.info("ServiceIdDispatcher: {} endpoints registered", registry.size());
    }

    @PostMapping("/online/mvcJson/{serviceId}")
    public ResponseEntity<Map<String, Object>> dispatch(
            @PathVariable String serviceId,
            HttpServletRequest request
    ) {
        // URL "CpmsEduPgmLst-search" -> registry key "CpmsEduPgmLst/search"
        int dash = serviceId.lastIndexOf('-');
        String key = dash > 0
                ? serviceId.substring(0, dash) + "/" + serviceId.substring(dash + 1)
                : serviceId;
        MethodTarget target = registry.get(key);
        if (target == null) {
            return ResponseEntity.notFound().build();
        }
        try {
            Object result;
            if (target.paramType != null) {
                Object param = objectMapper.readValue(readBody(request), target.paramType);
                result = target.method.invoke(target.bean, param);
            } else {
                result = target.method.invoke(target.bean);
            }
            Map<String, Object> header = new LinkedHashMap<>();
            header.put("responseCode", "S0000");
            header.put("responseMessage", "SUCCESS");
            Map<String, Object> response = new LinkedHashMap<>();
            response.put("header", header);
            response.put("payload", result);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Error dispatching {}: {}", key, e.getMessage(), e);
            Map<String, Object> header = new LinkedHashMap<>();
            header.put("responseCode", "E9999");
            header.put("responseMessage", e.getMessage());
            Map<String, Object> response = new LinkedHashMap<>();
            response.put("header", header);
            response.put("payload", null);
            return ResponseEntity.ok(response);
        }
    }

    private String readBody(HttpServletRequest request) {
        try (BufferedReader reader = request.getReader()) {
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
            return sb.toString();
        } catch (Exception e) {
            return "{}";
        }
    }
}
