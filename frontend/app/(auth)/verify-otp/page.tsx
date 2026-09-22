'use client';
import { useState } from 'react';
import { Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { apiRequest } from '@/lib/api';
import { setToken } from '@/lib/auth';

function VerifyOtpForm() {
  const router = useRouter();
  const params = useSearchParams();
  const email = params.get('email') ?? '';
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [resending, setResending] = useState(false);
  async function verify() {
    setError(null);
    setBusy(true);
    try {
      const result = await apiRequest<{ access_token: string }>('/api/auth/verify-otp', { method: 'POST', noAuth: true, body: JSON.stringify({ email, code }) });
      setToken(result.access_token);
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not verify this code.');
    } finally {
      setBusy(false);
    }
  }
  async function resend() {
    setError(null);
    setResending(true);
    try {
      await apiRequest('/api/auth/resend-otp', { method: 'POST', noAuth: true, body: JSON.stringify({ email }) });
      setCode('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not resend the code.');
    } finally {
      setResending(false);
    }
  }
  return <main className="mx-auto max-w-md p-8"><h1 className="text-2xl font-semibold">Verify your email</h1><p className="mt-2 text-slate-500">Enter the six-digit code sent to {email}.</p>{error && <p className="mt-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}<input className="mt-6 w-full rounded border p-3 tracking-[0.5em]" inputMode="numeric" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} placeholder="000000" /><button disabled={busy || code.length !== 6} onClick={() => void verify()} className="mt-4 rounded bg-slate-900 px-4 py-3 text-white disabled:opacity-50">{busy ? 'Verifying…' : 'Verify email'}</button><button disabled={resending} onClick={() => void resend()} className="mt-4 block text-sm text-slate-600 underline disabled:opacity-50">{resending ? 'Sending…' : 'Resend code'}</button></main>;
}

export default function VerifyOtpPage() {
  return <Suspense fallback={<main className="mx-auto max-w-md p-8">Loading…</main>}><VerifyOtpForm /></Suspense>;
}
