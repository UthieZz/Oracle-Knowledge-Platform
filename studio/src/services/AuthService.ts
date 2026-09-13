import { onAuthStateChanged, signOut, signInWithRedirect, OAuthProvider, User } from 'firebase/auth';
import { auth } from './firebase';

export interface SiloAccess { tenantId: string; siloId: string; role: string; }
export interface AuthSession { user: User; access: SiloAccess[]; active: SiloAccess; }

const SESSION_KEY = 'okp.active-silo';

export const AuthService = {
  async getSession(): Promise<AuthSession> {
    const user = auth.currentUser;
    if (!user) throw new Error('Authentication is required.');
    const claims = (await user.getIdTokenResult()).claims as Record<string, unknown>;
    const access = Array.isArray(claims.okp_access) ? claims.okp_access as SiloAccess[] : [];
    const requested = sessionStorage.getItem(SESSION_KEY);
    const active = access.find(item => `${item.tenantId}/${item.siloId}` === requested) || access[0];
    if (!active) throw new Error('This account has no assigned tenant or business silo.');
    return { user, access, active };
  },
  setActive(access: SiloAccess): void { sessionStorage.setItem(SESSION_KEY, `${access.tenantId}/${access.siloId}`); },
  signIn(): Promise<void> {
    const providerId = (import.meta as any).env?.VITE_OKP_AUTH_PROVIDER as string | undefined;
    if (!providerId) return Promise.reject(new Error('VITE_OKP_AUTH_PROVIDER is not configured.'));
    return signInWithRedirect(auth, new OAuthProvider(providerId));
  },
  observe(callback: (user: User | null) => void) { return onAuthStateChanged(auth, callback); },
  signOut() { return signOut(auth); },
};
