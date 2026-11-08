/** Read-only Vedoy Monetize Statistics integration.
 * Configure the real, verified Monetize endpoint before use. Fail closed on unverified origins.
 */
export type MonetizeSummary = {
 source:'vedoy-monetize'; from:string; to:string;
 coverage?:{sampled?:boolean; notes?:string};
 metrics?:{pageViews?:number; conversions?:number; conversionRate?:number; revenueNok?:number};
 generatedAt:string;
};
export interface MonetizeConfig {
 baseUrl:string; token:string; allowedOrigins:readonly string[];
}
function isoDate(value:string) {
 if(!/^\d{4}-\d{2}-\d{2}$/.test(value) || Number.isNaN(Date.parse(value+'T00:00:00Z'))) throw new Error('Invalid date');
 return value;
}
export async function getMonetizeSummary(
 config:MonetizeConfig, projectId:string, from:string, to:string,
 fetcher:typeof fetch=fetch
):Promise<MonetizeSummary|null> {
 if(!/^[a-zA-Z0-9_-]{1,80}$/.test(projectId)) throw new Error('Invalid project ID');
 const url=new URL(config.baseUrl);
 if(url.protocol!=='https:' || !config.allowedOrigins.includes(url.origin) || url.username || url.password) throw new Error('Untrusted Monetize origin');
 if(!config.token) throw new Error('Missing server-side Monetize token');
 const endpoint=new URL('/v1/statistics/projects/'+encodeURIComponent(projectId)+'/summary',url.origin);
 endpoint.searchParams.set('from',isoDate(from));
 endpoint.searchParams.set('to',isoDate(to));
 const controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),8000);
 try {
  const response=await fetcher(endpoint.toString(),{
   headers:{Authorization:'Bearer '+config.token,Accept:'application/json'},
   redirect:'error',signal:controller.signal,cache:'no-store'
  });
  if(response.status===404 || response.status===501 || response.status===503) return null;
  if(!response.ok) throw new Error('Monetize request failed: '+response.status);
  const body:unknown=await response.json();
  if(!body || typeof body!=='object' || !('source' in body) || body.source!=='vedoy-monetize' || !('generatedAt' in body) || typeof body.generatedAt!=='string') throw new Error('Invalid Monetize response');
  const data=body as MonetizeSummary;
  if(data.metrics) for(const value of Object.values(data.metrics)) if(value!==undefined && (typeof value!=='number' || !Number.isFinite(value) || value<0)) throw new Error('Invalid metric');
  return data;
 } finally {clearTimeout(timeout)}
}
