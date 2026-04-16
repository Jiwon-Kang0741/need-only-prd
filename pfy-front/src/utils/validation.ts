import { z } from 'zod';

/**
 * 필수 입력값 (빈 문자열 허용하지 않음)
 * @param fieldName - 필드 이름 (에러 메시지에 사용)
 */
export const isRequired = (fieldName: string) =>
  z.string().min(1, { message: `${fieldName} is required` });

/**
 * 숫자만 허용 (0~9)
 * @param fieldName - 필드 이름 (에러 메시지에 사용)
 */
export const onlyNumbers = (fieldName: string) =>
  z
    .string()
    .regex(/^\d+$/, { message: `${fieldName} must contain only numbers` });

/**
 * 최소 길이 제한
 * @param len - 최소 길이
 * @param fieldName - 필드 이름 (에러 메시지에 사용)
 */
export const minLength = (len: number, fieldName: string) =>
  z
    .string()
    .min(len, { message: `${fieldName} must be at least ${len} characters` });

/**
 * 최대 길이 제한
 * @param len - 최대 길이
 * @param fieldName - 필드 이름 (에러 메시지에 사용)
 */
export const maxLength = (len: number, fieldName: string) =>
  z
    .string()
    .max(len, { message: `${fieldName} must be at most ${len} characters` });

/**
 * 이메일 형식 검증
 * @param fieldName - 필드 이름 (에러 메시지에 사용)
 */
export const email = (fieldName: string) =>
  z.string().email({ message: `${fieldName} must be a valid email` });

/**
 * 비밀번호 복잡도 검증
 * - 최소 10자
 * - 영문 (대소문자 구분 X)
 * - 숫자 1개 이상
 * - 특수문자 1개 이상 (!@#$%^&*)
 * - 동일 문자 3회 이상 연속 불가
 */
export const passwordComplex = (fieldName: string) =>
  z
    .string()
    // 기본 규칙 (길이, 영문/숫자/특수문자)
    .regex(/^(?=.*[A-Za-z])(?=.*\d)(?=.*[!@#$%^&*]).{10,}$/, {
      message: `${fieldName} must be at least 10 characters, include letters, numbers, and special characters`,
    })
    // 동일 문자 3회 이상 반복 방지
    .refine((val) => !/(.)\1{2,}/.test(val), {
      message: `${fieldName} cannot contain the same character 3 times in a row`,
    });

/**
 * 사용자 ID 포함 여부 체크
 */
export const excludeUserId = (password: string, userId: string) => {
  return !password.toLowerCase().includes(userId.toLowerCase());
};

/**
 * datatalbe 신규 생성 row 인풋 검증
 * 입력이 안된 인풋이 하나라도 있을 때
 */
export const isEmptyRow = (row: Record<string, any>): boolean => {
  const empty = Object.entries(row)
    .filter(([key]) => key !== 'id' && key !== 'isNew')
    .some(([, val]) => val === '' || val === null || val === undefined);

  return empty;
};
