interface ErrorInfo {
  status: number;
  errorType: string;
  errorCode: string;
  errorMessage: string;
  details?: any;
}

export interface LoginResponse {
  loginSuccess: boolean; // 사용자 인증 여부
  authenticated: boolean; // otp 인증 여부
  tempLogin?: boolean; // 임시 비밀번호 로그인 여부
  tokenExpiresAt?: string; // 토큰 만료시간
  otpExpiresAt?: string; // OTP 입력 만료 시간
  sessionExpiresAt?: string; // 로그인 세션 만료 시간
  token: string;
  user?: UserInfo;
  payload?: string;
  errorInfo?: ErrorInfo;
  logout?: boolean;
}

export interface UserInfo {
  username: string; // 사용자 ID
  langCd: 'en-US' | 'ko-KR' | 'pl-PL'; // 언어 코드
  sknCd: 'dark' | 'light'; // 다크모드 여부
  userId: string;
  userNm: string;
  useYn: string;
  lognDtm: string;
  empno: string | null;
  compCd: string | null;
  deptCd: string | null;
  posiCd: string | null;
  jobCd: string | null;
  natnCd: string | null;
  typeCd: string | null;
  roles: string[];
}

export interface JwtPayload {
  userId: string;
  username: string;
  authenticated: boolean;
  type: string;
  exp: number;
  iat: number;
  tmpPwdYn: string;
  tfaEnblYn: string;
  expPwdYn: string;
  errorMsg: string;
}

export interface ResetPasswordParams {
  userId: string;
  newPwd: string;
  cnfPwd: string;
}

export interface ChangePasswordParams {
  userId: string;
  curPwd: string;
  newPwd: string;
  newPwdCnf: string;
}
