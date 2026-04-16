import { storeToRefs } from 'pinia';

import { useUserStore } from '@/stores/userStore';

export function useRolePermission() {
  const userStore = useUserStore();
  const { user } = storeToRefs(userStore);

  /**
   * hasRole
   * - 하나 이상의 역할을 체크 가능
   * - 문자열('A,B') 또는 여러 인자('A','B') 모두 지원
   * - 접미사 기반 필터링 지원: '_USER', '_ADM' 등
   * - user.roles 중 하나라도 조건에 맞으면 true 반환
   * - 사용 예시
   * hasRole('ITO_ADM');         // 정확히 'ITO_ADM'가 있을 때 true
   * hasRole('*_USER');             // 모든 '_USER'로 끝나는 역할이 있을 때 true
   * hasRole('MT_*');            // 'MT_'로 시작하는 역할이 있을 때 true
   * hasRole('ITO_ADM,MT_USER'); // 둘 중 하나라도 있으면 true
   */

  const hasRole = (...roles: string[]) => {
    if (!user.value?.roles?.length) return false;

    const userRoles = user.value.roles;

    // roles 배열 안에 콤마가 있는 경우 분리하고, 공백 제거
    const requiredRoles = roles
      .flatMap((r) => r.split(','))
      .map((r) => r.trim())
      .filter(Boolean);

    return requiredRoles.some((required) => {
      if (required.startsWith('*')) {
        // 접미사 필터링: '*_USER' → 모든 '_USER'로 끝나는 역할
        const suffix = required.slice(1);
        return userRoles.some((role) => role.endsWith(suffix));
      }
      if (required.endsWith('*')) {
        // 접두사 필터링: 'ADMIN_*' → 모든 'ADMIN_'로 시작하는 역할
        const prefix = required.slice(0, -1);
        return userRoles.some((role) => role.startsWith(prefix));
      }
      // 정확한 매칭
      return userRoles.includes(required);
    });
  };

  return {
    hasRole,
  };
}
