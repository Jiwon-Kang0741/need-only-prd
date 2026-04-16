/**
 * 에러 응답에서 우선순위에 따라 메시지를 추출합니다
 *
 * 우선순위:
 * 1. errorInfo.errorMessage + (details 첫번째 키의 값)
 * 2. header.responseMessage
 * 3. error.message
 * 4. 기본 메시지
 *
 * @param error - 에러 객체
 * @param defaultMessage - 기본 메시지
 * @returns 포맷된 에러 메시지
 */
export function formatErrorMessage(error: any, defaultMessage: string): string {
  const errorInfo = error.response?.data?.errorInfo;
  const responseMessage = error.response?.data?.header?.responseMessage;

  // 1순위: errorInfo.errorMessage
  if (errorInfo?.errorMessage) {
    let message = errorInfo.errorMessage;

    // details 객체에 키가 있으면 첫 번째 키의 값을 괄호 안에 추가
    if (errorInfo.details && typeof errorInfo.details === 'object') {
      const firstKey = Object.keys(errorInfo.details)[0];
      if (firstKey && errorInfo.details[firstKey]) {
        message += ` (${errorInfo.details[firstKey]})`;
      }
    }

    return message;
  }

  // 2순위: header.responseMessage
  if (responseMessage) {
    return responseMessage;
  }

  // 3순위: error.message
  if (error.message) {
    return error.message;
  }

  // 4순위: 기본 메시지
  return defaultMessage;
}
