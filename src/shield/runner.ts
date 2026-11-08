import type {SupabaseClient} from '@supabase/supabase-js';
import {claimJob} from './scheduler';
export type ScanResult={tls:{status:string;details:unknown};pqc:{status:string;details:unknown};security:{status:string;details:unknown}};
export interface ScanAdapter {runAuthorizedPassiveChecks(targetUrl:string):Promise<ScanResult>}
export async function runOne(db:SupabaseClient,adapter:ScanAdapter) {
 const job=await claimJob(db);
 if(!job) return {processed:false};
 const {data:subscription,error}=await db.from('shield_subscriptions').select('*').eq('id',job.subscription_id).single();
 if(error || !subscription || subscription.status!=='active' || !subscription.authorized_at) throw new Error('Subscription not authorized');
 try {
  // Adapter MUST enforce URL ownership, public DNS/IP, outbound network restrictions, timeouts and passive-only scans.
  const result=await adapter.runAuthorizedPassiveChecks(subscription.target_url);
  const {error:writeError}=await db.from('shield_scan_jobs').update({status:'succeeded',result,finished_at:new Date().toISOString(),locked_until:null}).eq('id',job.id).eq('status','running');
  if(writeError) throw writeError;
  await db.from('shield_notifications').upsert({subscription_id:job.subscription_id,job_id:job.id,kind:'scan_completed',payload:{job_id:job.id}},{onConflict:'job_id,kind',ignoreDuplicates:true});
  return {processed:true,success:true};
 } catch(e) {
  const retry=job.attempts<3;
  await db.from('shield_scan_jobs').update({status:retry?'queued':'failed',scheduled_for:retry?new Date(Date.now()+job.attempts*60000).toISOString():job.scheduled_for,error_code:'SCAN_FAILED',locked_until:null,finished_at:retry?null:new Date().toISOString()}).eq('id',job.id);
  if(!retry) await db.from('shield_notifications').upsert({subscription_id:job.subscription_id,job_id:job.id,kind:'scan_failed',payload:{job_id:job.id}},{onConflict:'job_id,kind',ignoreDuplicates:true});
  return {processed:true,success:false};
 }
}
