export const maskEmail = (email: string): string => {
  if (!email.includes('@')) return email;
  const [localPart, domain] = email.split('@');

  if (localPart.length <= 2) {
    return `${localPart[0] || ''}*${domain ? `@${domain}` : ''}`;
  }

  const visible = localPart.slice(0, 2);
  const masked = '*'.repeat(localPart.length - 2);

  return `${visible}${masked}@${domain}`;
};
