'use client';

import { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, Link2, Loader2, RefreshCw } from 'lucide-react';
import { apiRequest } from '@/lib/api';

type Status = { connected: boolean; portal_id: string | null };
type HubSpotList = { id: string; name: string; last_synced_at: string | null };

export default function HubSpotPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [lists, setLists] = useState<HubSpotList[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const [nextStatus, nextLists] = await Promise.all([apiRequest<Status>('/api/hubspot/status'), apiRequest<HubSpotList[]>('/api/hubspot/lists')]);
      setStatus(nextStatus); setLists(nextLists);
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not load HubSpot status.'); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);

  async function connect() {
    setBusy(true); setError(null);
    try { const result = await apiRequest<{ authorization_url: string }>('/api/hubspot/connect'); window.location.assign(result.authorization_url); }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not start HubSpot connection.'); setBusy(false); }
  }
  async function sync() {
    setBusy(true); setError(null); setMessage(null);
    try { const result = await apiRequest<{ contacts_synced: number; lists_synced: number }>('/api/hubspot/sync', { method: 'POST' }); setMessage(`${result.contacts_synced} contacts and ${result.lists_synced} lists synced.`); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'HubSpot sync failed.'); }
    finally { setBusy(false); }
  }

  if (loading) return <div className="flex min-h-[320px] items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-[#D6A84F]" /></div>;
  return <div className="mx-auto max-w-5xl space-y-8 p-6 lg:p-10"><div><p className="mb-2 text-sm font-semibold uppercase tracking-[0.2em] text-[#D6A84F]">CRM connection</p><h1 className="text-3xl font-bold text-[#F5F5F3]">HubSpot</h1><p className="mt-2 text-sm leading-6 text-[#9EA3AA]">HubSpot provides the contacts and lists used for CampaignIQ outreach.</p></div>{error && <div className="flex gap-3 rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-300"><AlertCircle className="h-5 w-5 shrink-0" />{error}</div>}{message && <div className="flex gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-sm text-emerald-300"><CheckCircle2 className="h-5 w-5 shrink-0" />{message}</div>}<section className="rounded-2xl border border-[#C8CBD0]/10 bg-[#111418] p-6"><div className="flex flex-wrap items-center justify-between gap-5"><div><p className="text-sm font-medium text-[#F5F5F3]">Connection status</p><p className="mt-2 text-sm text-[#9EA3AA]">{status?.connected ? `Connected to portal ${status.portal_id || 'unknown'}` : 'No HubSpot portal connected.'}</p></div><div className="flex gap-3">{status?.connected ? <button onClick={() => void sync()} disabled={busy} className="inline-flex items-center gap-2 rounded-xl border border-[#D6A84F]/30 px-4 py-3 text-sm font-semibold text-[#F0C76A] disabled:opacity-60">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}Sync now</button> : <button onClick={() => void connect()} disabled={busy} className="inline-flex items-center gap-2 rounded-xl bg-[#D6A84F] px-4 py-3 text-sm font-semibold text-[#080A0D] disabled:opacity-60">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Link2 className="h-4 w-4" />}Connect HubSpot</button>}</div></div></section><section className="overflow-hidden rounded-2xl border border-[#C8CBD0]/10 bg-[#111418]"><div className="border-b border-[#C8CBD0]/10 px-6 py-5"><h2 className="font-semibold text-[#F5F5F3]">Synced lists</h2></div>{lists.length === 0 ? <p className="p-6 text-sm text-[#9EA3AA]">No lists synced yet.</p> : lists.map((list) => <div key={list.id} className="flex items-center justify-between border-b border-[#C8CBD0]/10 px-6 py-4 last:border-0"><span className="text-sm text-[#F5F5F3]">{list.name}</span><span className="text-xs text-[#8C9299]">{list.last_synced_at ? new Date(list.last_synced_at).toLocaleString() : 'Not synced'}</span></div>)}</section></div>;
}
