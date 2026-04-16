import { http, HttpResponse } from 'msw';

export const authHandlers = [
  http.post('/online/api/auth/login', async ({ request }) => {
    const body = (await request.json()) as {
      username: string;
      password: string;
    };
    const { username, password } = body;

    if (username === 'admin') {
      // 정상 로그인
      if (password === '1111') {
        return HttpResponse.json({
          token:
            'eyJhbGciOiJIUzUxMiJ9.eyJhdXRoZW50aWNhdGVkIjpmYWxzZSwidXNlck5tIjoic3BzMSIsInRtcFB3ZFluIjoiTiIsImxvZ25EdG0iOiIyMDI1LTA4LTEyVDA1OjI4OjMyLjIxNzI4MloiLCJ0eXBlIjoib3RwLWF1dGgiLCJ1c2VySWQiOiJzcHMxIiwic3ViIjoic3BzMSIsImlhdCI6MTc1NDk3Nzg4OCwiZXhwIjoxNzU0OTc4NDg4fQ.vUuf-UqACXvENHSw5ZdEb9OeBesH-7wXpROwkFjPcZT1nnaiG9SQHTTTLcj_MoDtNvGpRxokP6gezo4pTVGD9w',
          authenticated: false,
        });
      }
      // 임시 비밀번호 로그인
      if (password === '2222') {
        return HttpResponse.json({
          loginSuccess: true,
          authenticated: false,
          tempLogin: true,
          token:
            'eyJhbGciOiJIUzUxMiJ9.eyJhdXRoZW50aWNhdGVkIjpmYWxzZSwidXNlck5tIjoic3BzMSIsInRtcFB3ZFluIjoiTiIsImxvZ25EdG0iOiIyMDI1LTA4LTEyVDA1OjE1OjMwLjg5OTYwNFoiLCJ0eXBlIjoib3RwLWF1dGgiLCJ1c2VySWQiOiJzcHMxIiwic3ViIjoic3BzMSIsImlhdCI6MTc1NDk3NjQ0OSwiZXhwIjoxNzU0OTc3MDQ5fQ.3FgB9b27vrAAGY8c8DyAuAhl55gd-DZC0N3nq7f74fq0XFnEbW6A9wiaF7mS0N6ePBQWY-zqPoU1rlyB5WbF0g',
        });
      }
    }
    return HttpResponse.json({ message: 'Failed Login' }, { status: 401 });
  }),
  http.post('/online/api/auth/2fa/verify', async ({ request }) => {
    const body = (await request.json()) as { otpCode: string };
    const { otpCode } = body;

    if (otpCode === '111111') {
      return HttpResponse.json({
        token:
          'eyJhbGciOiJIUzUxMiJ9.eyJhdXRoZW50aWNhdGVkIjp0cnVlLCJ1c2VyTm0iOiJzcHMxIiwiY19oYXNoIjoiaSt4cDcycGRvNTFBVGlTeG5RL01rUElHRDUzdDB3ZVNKRWpFcitXRkIvYz0iLCJtYXhfZXhwIjoxNzU1MjgwMjk4MDYwLCJsb2duRHRtIjoiMjAyNS0wOC0xMlQwNTo1MToyOC41ODI3NzdaIiwidHlwZSI6IjJmYS1hdXRoIiwidXNlcklkIjoic3BzMSIsImF1dGhvcml0aWVzIjpbIklUT19NR1IiXSwic3ViIjoic3BzMSIsImp0aSI6Ik96MGNzZ1BwcXlVTXFsRHJtUkJaeTZhZTR6R3JhV19rIiwiaWF0IjoxNzU0OTc3ODk4LCJleHAiOjE3NTUyODAyOTh9.Qxz7u4oM6ikqyYs9H4UnB4qDhcquCfQ9QkVVt1pYOjz6C4Mgq0GYTOJugyMRFfzf9ZG8BejtQAPPCO62qjyMzg',
        authenticated: true,
        user: {
          userId: 'sps1',
          userNm: 'sps1',
          useYn: 'Y',
          lognDtm: '2025-08-11T23:52:09.908430Z',
          email: null,
          empno: 'sps1',
          compCd: null,
          deptCd: null,
          posiCd: null,
          jobCd: null,
          userIp: null,
          langCd: 'ko-KR',
          sknCd: 'Dark',
          natnCd: null,
          typeCd: null,
          roles: ['ITO_MGR'],
        },
      });
    }

    return HttpResponse.json(
      { message: 'Failed Login', otpRequired: false },
      { status: 401 }
    );
  }),
  http.post('/api/auth/2fa/resend', async () => {
    // 5분 후 만료시간 예시
    const expiresAt = new Date(Date.now() + 5 * 60 * 1000).toISOString();

    return HttpResponse.json({
      success: true,
      message: 'OTP 코드가 다시 전송되었습니다.',
      expiresAt,
    });
  }),
  http.post('/api/auth/2fa/resendOtp', async () => {
    return HttpResponse.json({
      success: true,
      message: 'OTP 코드가 재전송되었습니다.',
    });
  }),
  http.post('/api/auth/sendPasswordResetEmail', async ({ request }) => {
    const body = (await request.json()) as { username: string };
    const { username } = body;

    if (!username) {
      return HttpResponse.json(
        { message: 'username is required' },
        { status: 400 }
      );
    }
    return HttpResponse.json({
      success: true,
      message: `Temporary password email sent to username: ${username}`,
    });
  }),
  http.post('/api/auth/2fa/resetPassword', async ({ request }) => {
    const body = (await request.json()) as { newPassword: string };
    const { newPassword } = body;

    const passwordRegex = /^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*]).{8,}$/;
    if (!passwordRegex.test(newPassword)) {
      return HttpResponse.json(
        { message: 'Password does not meet complexity requirements.' },
        { status: 400 }
      );
    }

    return HttpResponse.json({
      success: true,
      message: 'Password has been changed successfully.',
    });
  }),
  http.post('/api/objPermission', async ({ request }) => {
    const body = (await request.json()) as { windowId: string };
    const { windowId } = body;

    const permissionMap: Record<string, string[]> = {
      DSOV010: ['btnSave', 'btnDelete'],
      DSOV020: ['btnSave'],
      MTOV010: ['btnSave', 'btnDelete', 'staNatnCd'],
      MTCT010: ['btnSave', 'btnDelete' /* 'btnTotalProgress' */],
    };

    const permissionList = permissionMap[windowId];

    if (permissionList) {
      return HttpResponse.json({
        permissionList,
      });
    }

    return HttpResponse.json(
      { message: 'Failed Object Permission', success: false },
      { status: 401 }
    );
  }),
  http.get('/api/user/me', () => {
    let userInfo;
    const saved = localStorage.getItem('mockUserInfo');
    if (saved) {
      userInfo = JSON.parse(saved);
    } else {
      userInfo = {
        sknCd: 'Dark',
        langCd: 'ko-Kr',
      };
    }

    return HttpResponse.json({
      success: true,
      data: userInfo,
      message: 'User info retrieved successfully',
    });
  }),
  http.post('/api/user/settings', async ({ request }) => {
    const body = (await request.json()) as Partial<{
      langCd: string;
      sknCd: string;
    }>;

    // 로컬스토리지에서 기존 값 가져오기
    let mockUserInfo;
    const saved = localStorage.getItem('mockUserInfo');
    if (saved) {
      mockUserInfo = JSON.parse(saved);
    } else {
      mockUserInfo = {
        userId: 'admin',
        userNm: 'admin',
        useYn: 'Y',
        lognDtm: new Date().toISOString(),
        email: null,
        empno: 'admin',
        compCd: null,
        deptCd: null,
        posiCd: null,
        jobCd: null,
        userIp: null,
        langCd: 'ko-KR',
        sknCd: 'Dark',
        natnCd: null,
        typeCd: null,
        roles: ['ITO_MGR'],
      };
    }

    // 받은 필드만 업데이트
    const updated = {
      ...mockUserInfo,
      ...body,
    };

    // 로컬스토리지에 저장
    localStorage.setItem('mockUserInfo', JSON.stringify(updated));

    // 성공 응답
    return HttpResponse.json(updated);
  }),
  http.post('/api/auth/logout', () => {
    // 로컬 스토리지 정리
    localStorage.removeItem('mockUserInfo');

    // 응답
    return HttpResponse.json({
      success: true,
      message: '로그아웃 처리 완료',
    });
  }),
];
