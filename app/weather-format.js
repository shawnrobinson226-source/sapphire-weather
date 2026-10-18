// Pure display helpers; never infer the current day from forecast position.
export function locationDate(timezone, now=Date.now()) {
  try {
    const parts=new Intl.DateTimeFormat('en',{timeZone:timezone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now);
    const get=type=>parts.find(p=>p.type===type).value;
    return `${get('year')}-${get('month')}-${get('day')}`;
  } catch { return ''; }
}
export function dayLabel(date, timezone, now=Date.now()) {
  if(date===locationDate(timezone,now))return 'Today';
  return new Date(date+'T12:00:00Z').toLocaleDateString(undefined,{weekday:'short',timeZone:'UTC'});
}
export function ageLabel(stamp, now=Date.now()) {
  const minutes=Math.max(0,Math.floor((now-new Date(stamp).getTime())/60000));
  if(!Number.isFinite(minutes))return 'unknown age';
  if(minutes<1)return 'just now';
  if(minutes<60)return `${minutes} min ago`;
  if(minutes<1440)return `${Math.floor(minutes/60)} hr ago`;
  return `${Math.floor(minutes/1440)} days ago`;
}
export function isStale(weather, minutes, now=Date.now()) {
  return now-new Date(weather.fetched_at).getTime()>=minutes*60000 || weather.forecast[0].date!==locationDate(weather.timezone,now);
}
export function fetchedLabel(stamp, timezone) {
  try{return new Date(stamp).toLocaleString(undefined,{timeZone:timezone,month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});}
  catch{return stamp;}
}
