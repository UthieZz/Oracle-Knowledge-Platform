import React, { useEffect, useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { AuthService } from '../services/AuthService';

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<'loading' | 'signedOut' | 'authorised' | 'denied'>('loading');
  const [detail, setDetail] = useState('');
  useEffect(() => AuthService.observe(async user => {
    if (!user) return setState('signedOut');
    try { await AuthService.getSession(); setState('authorised'); }
    catch (error: any) { setDetail(error?.message || 'No silo access has been assigned.'); setState('denied'); }
  }), []);
  if (state === 'authorised') return <>{children}</>;
  return <main className="min-h-screen bg-black text-white flex items-center justify-center p-6"><section className="max-w-md text-center space-y-5"><ShieldCheck className="mx-auto text-blue-400" size={42}/><h1 className="text-2xl font-bold">Oracle Studio Enterprise</h1><p className="text-gray-400">{state === 'loading' ? 'Verifying your organisation access…' : detail || 'Sign in through your organisation to access an authorised business silo.'}</p>{state === 'signedOut' && <button onClick={() => AuthService.signIn().catch(error => setDetail(error.message))} className="bg-blue-600 hover:bg-blue-500 px-5 py-3 rounded-lg font-semibold">Sign in securely</button>}</section></main>;
}
