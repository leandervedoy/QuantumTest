import type { SupabaseClient } from '@supabase/supabase-js';
export const SHIELD_CHECKS = ['tls','pqc','security'] as const;
export const MONTHLY_PRICE_NOK = 99;
export function nextMonthly(date: Date): Date {
  const next = new Date(date);
  const day = next.getUTCDate();
  next.setUTCDate(1);
  next.setUTCMonth(next.getUTCMonth()+1);
  const last = new Date(Date.UTC(next.getUTCFullYear(),next.getUTCMonth()+1,0)).getUTCDate();
  next.setUTCDate(Math.min(day,last));
  return next;
}
export async function scheduleDue(db: SupabaseClient, now = new Date()) {
  const {data,error}=await db.from('shield_subscriptions').select('id,next_run_at').eq('status','active').not('authorized_at','is',null).lte('next_run_at',now.toISOString()).limit(100);
  if(error) throw error;
  let queued=0;
  for(const sub of data??[]) {
    const due = new Date(sub.next_run_at);
    const {error:jobError}=await db.from('shield_scan_jobs').upsert({subscription_id:sub.id,scheduled_for:due.toISOString()},{onConflict:'subscription_id,scheduled_for',ignoreDuplicates:true});
    if(jobError) throw jobError;
    const {error:advanceError}=await db.from('shield_subscriptions').update({next_run_at:nextMonthly(due).toISOString()}).eq('id',sub.id).eq('next_run_at',sub.next_run_at);
    if(advanceError) throw advanceError;
    queued++;
  }
  return queued;
}
export async function claimJob(db: SupabaseClient) {
 const {data,error}=await db.rpc('shield_claim_job');
 if(error) throw error;
 return data?.[0]??null;
}
