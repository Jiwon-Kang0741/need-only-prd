export const clearClientSession = () => {
  sessionStorage.removeItem('otpAuthToken');
  sessionStorage.removeItem('commonCode');
  localStorage.removeItem('accessToken');
  localStorage.removeItem('userStore');
};
