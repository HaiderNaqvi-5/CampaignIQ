'use client';

import { FormEvent, useEffect, useState } from 'react';
import Link from 'next/link';
import { AlertCircle, Loader2, Mail, Plus, Send, Users } from 'lucide-react';
import { apiRequest } from '@/lib/api';

type Bot = { id: string; name: string; website_url: string };
type Campaign = { id: string; name: string; topic: string; status: string; recipient_count: number };
type Contact = { id: string; email: string | null; first_name: string | null; last_name: string | null; company: string | null };
type HubSpotList = { id: string; name: string };
type CreatedCampaign = Campaign & { bot_id: string };
type Snapshot = { prepared: number; ineligible_contact_ids: string[]; duplicate_contact_ids: string[] };
type Recipient = { id: string; subject: string | null; body: string | null; status: string; contact_id: string };

export default function CampaignsPage() {
  const [bots, setBots] = useState<Bot[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [selectionMode, setSelectionMode] = useState<'all' | 'selected' | 'list'>('all');
  const [selectedContacts, setSelectedContacts] = useState<string[]>([]);
  const [lists, setLists] = useState<HubSpotList[]>([]);
  const [selectedLists, setSelectedLists] = useState<string[]>([]);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [review, setReview] = useState<Recipient[]>([]);
  const [reviewCampaignId, setReviewCampaignId] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [botId, setBotId] = useState('');
  const [name, setName] = useState('');
  const [topic, setTopic] = useState('');
  const [offer, setOffer] = useState('');
  const [followUpDays, setFollowUpDays] = useState('');
  const [followUpInstructions, setFollowUpInstructions] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [sendMessage, setSendMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const [loadedBots, loadedCampaigns, loadedContacts, loadedLists] = await Promise.all([apiRequest<Bot[]>('/api/bots'), apiRequest<Campaign[]>('/api/campaigns'), apiRequest<Contact[]>('/api/contacts'), apiRequest<HubSpotList[]>('/api/hubspot/lists')]);
      setBots(loadedBots); setCampaigns(loadedCampaigns); setContacts(loadedContacts); setLists(loadedLists); setBotId((current) => current || loadedBots[0]?.id || '');
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not load campaigns.'); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);

  async function createCampaign(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(null);
    try {
      const follow_ups = followUpDays && followUpInstructions ? [{ delay_days: Number(followUpDays), instructions: followUpInstructions }] : [];
      const campaign = await apiRequest<CreatedCampaign>('/api/campaigns', { method: 'POST', body: JSON.stringify({ bot_id: botId, name, topic, offer: offer || null, follow_ups }) });
      const selection = selectionMode === 'all' ? { all: true } : selectionMode === 'list' ? { list_ids: selectedLists } : { contact_ids: selectedContacts };
      const prepared = await apiRequest<Snapshot>(`/api/campaigns/${campaign.id}/recipients`, { method: 'POST', body: JSON.stringify(selection) });
      setSnapshot(prepared); setReviewCampaignId(campaign.id); setGenerating(true);
      await apiRequest(`/api/campaigns/${campaign.id}/generate`, { method: 'POST' });
      const detail = await apiRequest<{ recipients: Recipient[] }>(`/api/campaigns/${campaign.id}`);
      setReview(detail.recipients); setName(''); setTopic(''); setOffer(''); setFollowUpDays(''); setFollowUpInstructions(''); setSelectedContacts([]); setSelectedLists([]); await load();
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not create campaign.'); }
    finally { setSaving(false); setGenerating(false); }
  }

  async function sendCampaign() {
    if (!reviewCampaignId) return;
    setSending(true); setError(null); setSendMessage(null);
    try {
      const result = await apiRequest<{ status: string; queued: boolean }>(`/api/campaigns/${reviewCampaignId}/send`, { method: 'POST' });
      setSendMessage(result.queued ? 'Campaign queued for delivery.' : 'Campaign is ready for delivery; start the worker to send it.');
      await load();
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not queue campaign.'); }
    finally { setSending(false); }
  }

  function updateReviewField(recipientId: string, field: 'subject' | 'body', value: string) {
    setReview((current) => current.map((recipient) => recipient.id === recipientId ? { ...recipient, [field]: value } : recipient));
  }

  async function saveReviewRecipient(recipient: Recipient) {
    if (!reviewCampaignId || !recipient.subject?.trim() || !recipient.body?.trim()) return;
    try {
      await apiRequest(`/api/campaigns/${reviewCampaignId}/emails/${recipient.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ subject: recipient.subject, body: recipient.body }),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save this email.');
    }
  }

  function contactLabel(contactId: string) {
    const contact = contacts.find((item) => item.id === contactId);
    if (!contact) return contactId.slice(0, 8) + '…';
    return [contact.first_name, contact.last_name].filter(Boolean).join(' ') || contact.email || contactId.slice(0, 8) + '…';
  }

  if (loading) return <div className="flex min-h-[320px] items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-[#D6A84F]" /></div>;
  return <div className="mx-auto max-w-6xl space-y-8 p-6 lg:p-10">
    <div><p className="mb-2 text-sm font-semibold uppercase tracking-[0.2em] text-[#D6A84F]">Campaigns</p><h1 className="text-3xl font-bold text-[#F5F5F3]">Personalized outreach</h1><p className="mt-2 text-sm leading-6 text-[#9EA3AA]">Create a grounded campaign, then snapshot HubSpot recipients for review.</p></div>
    {error && <div className="flex gap-3 rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-300"><AlertCircle className="h-5 w-5 shrink-0" />{error}</div>}
    <section className="rounded-2xl border border-[#C8CBD0]/10 bg-[#111418] p-6"><div className="mb-6 flex items-center gap-3"><Plus className="h-5 w-5 text-[#D6A84F]" /><h2 className="font-semibold text-[#F5F5F3]">New campaign</h2></div>
      {bots.length === 0 ? <p className="text-sm text-[#9EA3AA]">Add a website first in <Link className="text-[#F0C76A]" href="/dashboard/bots">Websites</Link>.</p> : <form onSubmit={createCampaign} className="grid gap-4 md:grid-cols-2">
        <select value={botId} onChange={(e) => setBotId(e.target.value)} className="rounded-xl border border-[#C8CBD0]/10 bg-[#080A0D] p-3 text-sm text-[#F5F5F3]" required><option value="">Choose website</option>{bots.map((bot) => <option key={bot.id} value={bot.id}>{bot.name || bot.website_url}</option>)}</select>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Campaign name" required className="rounded-xl border border-[#C8CBD0]/10 bg-[#080A0D] p-3 text-sm text-[#F5F5F3]" />
        <textarea value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Topic or goal" required className="min-h-24 rounded-xl border border-[#C8CBD0]/10 bg-[#080A0D] p-3 text-sm text-[#F5F5F3] md:col-span-2" />
        <input value={offer} onChange={(e) => setOffer(e.target.value)} placeholder="Optional offer or instruction" className="rounded-xl border border-[#C8CBD0]/10 bg-[#080A0D] p-3 text-sm text-[#F5F5F3] md:col-span-2" />
        <div className="space-y-3 rounded-xl border border-[#C8CBD0]/10 bg-[#080A0D] p-4 md:col-span-2"><p className="text-sm font-medium text-[#C8CBD0]">Recipients</p><div className="flex flex-wrap gap-5 text-sm text-[#9EA3AA]"><label><input type="radio" checked={selectionMode === 'all'} onChange={() => setSelectionMode('all')} className="mr-2 accent-[#D6A84F]" />All synced contacts</label><label><input type="radio" checked={selectionMode === 'list'} onChange={() => setSelectionMode('list')} className="mr-2 accent-[#D6A84F]" />HubSpot list</label><label><input type="radio" checked={selectionMode === 'selected'} onChange={() => setSelectionMode('selected')} className="mr-2 accent-[#D6A84F]" />Choose contacts</label></div>{selectionMode === 'list' && <select multiple value={selectedLists} onChange={(e) => setSelectedLists(Array.from(e.target.selectedOptions, (option) => option.value))} className="min-h-24 w-full rounded-lg border border-[#C8CBD0]/10 bg-[#111418] p-2 text-sm text-[#F5F5F3]"><option disabled value="">Select one or more synced lists</option>{lists.map((list) => <option key={list.id} value={list.id}>{list.name}</option>)}</select>}{selectionMode === 'selected' && <div className="grid max-h-40 gap-2 overflow-auto border-t border-[#C8CBD0]/10 pt-3 sm:grid-cols-2">{contacts.length === 0 ? <p className="text-xs text-[#8C9299]">No synced contacts found. Sync HubSpot first.</p> : contacts.map((contact) => <label key={contact.id} className="flex items-center gap-2 text-xs text-[#9EA3AA]"><input type="checkbox" checked={selectedContacts.includes(contact.id)} onChange={(e) => setSelectedContacts((current) => e.target.checked ? [...current, contact.id] : current.filter((id) => id !== contact.id))} className="accent-[#D6A84F]" />{contact.first_name || contact.last_name || contact.email || 'Unnamed contact'}{contact.company ? ` · ${contact.company}` : ''}</label>)}</div>}</div>
        <div className="grid gap-3 rounded-xl border border-[#C8CBD0]/10 bg-[#080A0D] p-4 md:col-span-2 md:grid-cols-[160px_1fr]"><label className="text-sm text-[#C8CBD0]">Optional follow-up<input type="number" min="1" max="365" value={followUpDays} onChange={(e) => setFollowUpDays(e.target.value)} placeholder="Days after send" className="mt-2 w-full rounded-lg border border-[#C8CBD0]/10 bg-[#111418] p-2 text-sm text-[#F5F5F3]" /></label><label className="text-sm text-[#C8CBD0]">Instructions<textarea value={followUpInstructions} onChange={(e) => setFollowUpInstructions(e.target.value)} placeholder="What should the follow-up say?" className="mt-2 min-h-16 w-full rounded-lg border border-[#C8CBD0]/10 bg-[#111418] p-2 text-sm text-[#F5F5F3]" /></label></div>
        <button disabled={saving || (selectionMode === 'selected' && selectedContacts.length === 0) || (selectionMode === 'list' && selectedLists.length === 0) || (!!followUpDays !== !!followUpInstructions)} className="inline-flex w-fit items-center gap-2 rounded-xl bg-[#D6A84F] px-4 py-3 text-sm font-semibold text-[#080A0D] disabled:opacity-60">{saving && <Loader2 className="h-4 w-4 animate-spin" />}Create and snapshot</button>
      </form>}
    </section>
    {snapshot && <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-sm text-emerald-300"><p>Snapshot prepared for {snapshot.prepared} recipient{snapshot.prepared === 1 ? '' : 's'}. {snapshot.ineligible_contact_ids.length} excluded for missing/invalid email; {snapshot.duplicate_contact_ids.length} duplicate{snapshot.duplicate_contact_ids.length === 1 ? '' : 's'} removed.</p>{snapshot.ineligible_contact_ids.length > 0 && <p className="mt-2 text-xs text-emerald-200/80">Excluded: {snapshot.ineligible_contact_ids.map(contactLabel).join(', ')}</p>}{snapshot.duplicate_contact_ids.length > 0 && <p className="mt-1 text-xs text-emerald-200/80">Duplicates removed: {snapshot.duplicate_contact_ids.map(contactLabel).join(', ')}</p>}</div>}
    {generating && <div className="flex items-center gap-2 text-sm text-[#9EA3AA]"><Loader2 className="h-4 w-4 animate-spin text-[#D6A84F]" />Generating individually grounded emails…</div>}
    {sendMessage && <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-sm text-emerald-300">{sendMessage}</div>}
    {review.length > 0 && reviewCampaignId && <section className="space-y-4"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold text-[#F5F5F3]">Review generated emails</h2><button onClick={() => void sendCampaign()} disabled={sending} className="inline-flex items-center gap-2 rounded-xl bg-[#D6A84F] px-4 py-2.5 text-sm font-semibold text-[#080A0D] disabled:opacity-60">{sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}Send campaign</button></div>{review.map((email) => <div key={email.id} className="rounded-2xl border border-[#C8CBD0]/10 bg-[#111418] p-5"><div className="mb-3 flex items-center justify-between text-xs text-[#8C9299]"><span>Recipient {email.contact_id.slice(0, 8)}…</span><span>{email.status}</span></div><input value={email.subject || ''} onChange={(event) => updateReviewField(email.id, 'subject', event.target.value)} onBlur={() => void saveReviewRecipient(email)} className="mb-3 w-full rounded-lg border border-[#C8CBD0]/10 bg-[#080A0D] p-3 text-sm text-[#F5F5F3]" /><textarea value={email.body || ''} onChange={(event) => updateReviewField(email.id, 'body', event.target.value)} onBlur={() => void saveReviewRecipient(email)} className="min-h-32 w-full rounded-lg border border-[#C8CBD0]/10 bg-[#080A0D] p-3 text-sm text-[#F5F5F3]" /></div>)}</section>}
    <section className="overflow-hidden rounded-2xl border border-[#C8CBD0]/10 bg-[#111418]"><div className="border-b border-[#C8CBD0]/10 px-6 py-5"><h2 className="font-semibold text-[#F5F5F3]">Your campaigns</h2></div>{campaigns.length === 0 ? <p className="p-6 text-sm text-[#9EA3AA]">No campaigns yet.</p> : campaigns.map((campaign) => <div key={campaign.id} className="flex items-center gap-4 border-b border-[#C8CBD0]/10 px-6 py-5 last:border-0"><Mail className="h-5 w-5 text-[#D6A84F]" /><div className="min-w-0 flex-1"><p className="font-medium text-[#F5F5F3]">{campaign.name}</p><p className="mt-1 truncate text-sm text-[#8C9299]">{campaign.topic}</p></div><span className="hidden items-center gap-1 text-sm text-[#8C9299] sm:flex"><Users className="h-4 w-4" />{campaign.recipient_count}</span><span className="rounded-full border border-[#D6A84F]/20 bg-[#D6A84F]/10 px-2.5 py-1 text-xs font-semibold text-[#F0C76A]">{campaign.status}</span></div>)}</section>
  </div>;
}
