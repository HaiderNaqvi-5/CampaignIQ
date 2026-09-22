'use client';

import { useEffect, useState } from 'react';
import { AlertCircle, Loader2, Save, Users } from 'lucide-react';
import { apiRequest } from '@/lib/api';

type Contact = { id: string; email: string | null; first_name: string | null; last_name: string | null; company: string | null; job_title: string | null };

export default function ContactsPage() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { apiRequest<Contact[]>('/api/contacts').then(setContacts).catch((err) => setError(err instanceof Error ? err.message : 'Could not load contacts.')).finally(() => setLoading(false)); }, []);
  function change(id: string, field: keyof Contact, value: string) { setContacts((current) => current.map((contact) => contact.id === id ? { ...contact, [field]: value || null } : contact)); }
  async function save(contact: Contact) {
    setSaving(contact.id); setError(null);
    try { const updated = await apiRequest<Contact>(`/api/contacts/${contact.id}`, { method: 'PATCH', body: JSON.stringify({ first_name: contact.first_name, last_name: contact.last_name, email: contact.email, company: contact.company, job_title: contact.job_title }) }); setContacts((current) => current.map((item) => item.id === updated.id ? updated : item)); }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not save contact.'); }
    finally { setSaving(null); }
  }

  if (loading) return <div className="flex min-h-[320px] items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-[#D6A84F]" /></div>;
  return <div className="mx-auto max-w-6xl space-y-8 p-6 lg:p-10"><div><p className="mb-2 text-sm font-semibold uppercase tracking-[0.2em] text-[#D6A84F]">CRM contacts</p><h1 className="text-3xl font-bold text-[#F5F5F3]">Contacts</h1><p className="mt-2 text-sm leading-6 text-[#9EA3AA]">Review and edit the synced contacts available for campaigns.</p></div>{error && <div className="flex gap-3 rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-300"><AlertCircle className="h-5 w-5 shrink-0" />{error}</div>}<section className="overflow-auto rounded-2xl border border-[#C8CBD0]/10 bg-[#111418]"><div className="flex items-center gap-3 border-b border-[#C8CBD0]/10 px-6 py-5"><Users className="h-5 w-5 text-[#D6A84F]" /><h2 className="font-semibold text-[#F5F5F3]">{contacts.length} synced contact{contacts.length === 1 ? '' : 's'}</h2></div>{contacts.length === 0 ? <p className="p-6 text-sm text-[#9EA3AA]">No contacts yet. Connect and sync HubSpot first.</p> : <div className="min-w-[760px]"><div className="grid grid-cols-[1.1fr_1.1fr_1.4fr_1.2fr_1.2fr_80px] gap-3 border-b border-[#C8CBD0]/10 px-6 py-3 text-xs font-semibold uppercase tracking-wide text-[#8C9299]"><span>First name</span><span>Last name</span><span>Email</span><span>Company</span><span>Job title</span><span /></div>{contacts.map((contact) => <div key={contact.id} className="grid grid-cols-[1.1fr_1.1fr_1.4fr_1.2fr_1.2fr_80px] items-center gap-3 border-b border-[#C8CBD0]/10 px-6 py-3 last:border-0"><input value={contact.first_name || ''} onChange={(e) => change(contact.id, 'first_name', e.target.value)} className="rounded-lg border border-[#C8CBD0]/10 bg-[#080A0D] p-2 text-sm text-[#F5F5F3]" /><input value={contact.last_name || ''} onChange={(e) => change(contact.id, 'last_name', e.target.value)} className="rounded-lg border border-[#C8CBD0]/10 bg-[#080A0D] p-2 text-sm text-[#F5F5F3]" /><input type="email" value={contact.email || ''} onChange={(e) => change(contact.id, 'email', e.target.value)} className="rounded-lg border border-[#C8CBD0]/10 bg-[#080A0D] p-2 text-sm text-[#F5F5F3]" /><input value={contact.company || ''} onChange={(e) => change(contact.id, 'company', e.target.value)} className="rounded-lg border border-[#C8CBD0]/10 bg-[#080A0D] p-2 text-sm text-[#F5F5F3]" /><input value={contact.job_title || ''} onChange={(e) => change(contact.id, 'job_title', e.target.value)} className="rounded-lg border border-[#C8CBD0]/10 bg-[#080A0D] p-2 text-sm text-[#F5F5F3]" /><button title="Save contact" onClick={() => void save(contact)} disabled={saving === contact.id} className="flex justify-center text-[#F0C76A] disabled:opacity-60">{saving === contact.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}</button></div>)}</div>}</section></div>;
}
