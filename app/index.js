// Native Sapphire app. The data path is shared with the conversational tool.
import pluginsAPI from '/static/shared/plugins-api.js';
import {dayLabel,ageLabel,isStale,fetchedLabel} from './weather-format.js';

const PATH = '/plugin-web/sapphire-weather/app/';
const icons = {
  pin: '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
  wind: '<path d="M3 7h12a3 3 0 1 0-3-3M2 12h17a3 3 0 1 1-3 3M4 17h5a2.5 2.5 0 1 1-2.5 2.5"/>',
  drop: '<path d="M12 2C10 6 5 10 5 15a7 7 0 0 0 14 0c0-5-5-9-7-13Z"/>',
  thermometer: '<path d="M9 14.5V5a3 3 0 0 1 6 0v9.5a5 5 0 1 1-6 0Z"/><path d="M12 9v9"/>',
  settings: '<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3" fill="currentColor"/><circle cx="15" cy="17" r="3" fill="currentColor"/>',
  refresh: '<path d="M20 7v5h-5M4 17v-5h5M5 7a8 8 0 0 1 13-2l2 3M4 16l2 3a8 8 0 0 0 13-2"/>',
  save: '<path d="M5 3h12l4 4v14H3V3h2Z"/><path d="M7 3v6h10V3M7 21v-8h10v8"/>'
};
const icon = name => `<svg class="sw-icon" viewBox="0 0 24 24" aria-hidden="true">${icons[name] || icons.sun}</svg>`;
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function scene(code) {
  const sunny = code != null && code <= 2;
  const rain = code != null && ((code >= 51 && code <= 67) || (code >= 80 && code <= 82) || code >= 95);
  const snow = code != null && ((code >= 71 && code <= 77) || code === 85 || code === 86);
  return `<svg viewBox="0 0 160 125" aria-hidden="true">
    ${sunny ? '<circle cx="72" cy="47" r="29" fill="#ffd493"/><g stroke="#ffd493" stroke-width="3" stroke-linecap="round"><path d="M72 6V0M72 94v-6M31 47h-7M120 47h-7M42 17l-5-5M107 82l-5-5M42 77l-5 5M107 12l-5 5"/></g>' : ''}
    ${code !== 0 ? '<path d="M38 91a23 23 0 0 1-2-46 32 32 0 0 1 61-7 26 26 0 1 1 14 53Z" fill="#d2e0ea"/><path d="M63 94a19 19 0 0 1-1-38 27 27 0 0 1 51-6 22 22 0 1 1 11 44Z" fill="#eef3f3"/>' : ''}
    ${rain ? '<g stroke="#89c8ff" stroke-width="4" stroke-linecap="round"><path d="m60 105-4 9m29-9-4 9m29-9-4 9"/></g>' : ''}
    ${snow ? '<g fill="#ccecff"><circle cx="60" cy="110" r="3"/><circle cx="85" cy="115" r="3"/><circle cx="110" cy="110" r="3"/></g>' : ''}
  </svg>`;
}

function temperature(value, from, to) {
  if (value == null) return null;
  return from === to ? value : to === 'imperial' ? value * 9 / 5 + 32 : (value - 32) * 5 / 9;
}
function shortDate(date) {
  return new Date(date + 'T12:00:00Z').toLocaleDateString(undefined, {month:'short', day:'numeric', timeZone:'UTC'});
}

export function render(container) {
  const link = document.createElement('link'); link.rel = 'stylesheet'; link.href = PATH + 'app.css';
  container.appendChild(link);
  const root = document.createElement('section'); root.className = 'sw-app'; root.setAttribute('aria-label','Weather dashboard');
  container.appendChild(root);
  let weather = null, viewUnits = 'metric', horizon = 3, selected = 0, active = true, requestId = 0, controller, choices = [], cacheMinutes=10, interacted=false, contextToken, contextError;
  const contextPromise=fetch('/api/plugin/sapphire-weather/context').then(async response=>{
    const data=await response.json().catch(()=>({error:'Could not verify the current chat. Reload Weather.'}));
    if(!response.ok||!data.context)throw new Error(data.error||'Reload Weather from a public chat.');
    contextToken=data.context;
  }).catch(error=>{contextError=error;});
  root.innerHTML = `
  <header class="sw-top"><div class="sw-brand"><div class="sw-brandmark">${icon('sun')}</div><div><div class="sw-eyebrow">Sapphire</div><div class="sw-brandname">Weather, at a glance.</div></div></div>
    <div class="sw-actions"><div class="sw-units" role="group" aria-label="Temperature units"><button type="button" data-unit="imperial" aria-pressed="false">°F</button><button type="button" data-unit="metric" aria-pressed="true">°C</button></div><button class="sw-quiet" data-action="preferences" aria-expanded="false" aria-label="Preferences">${icon('settings')}<span class="sw-pref-label">Preferences</span></button></div></header>
  <form class="sw-locationbar"><label class="sw-search">${icon('search')}<span class="sw-sr">City and region</span><input name="location" autocomplete="off" maxlength="160" placeholder="City, state or country" aria-label="City and region" required></label><button class="sw-primary" type="submit">Find weather</button></form>
  <div class="sw-status" role="status" aria-live="polite">Choose a city to see its forecast.</div>
  <div class="sw-choices sw-hidden" role="group" aria-label="Matching places"></div>
  <section class="sw-preferences sw-hidden" aria-label="Weather preferences"><h2>Make this your forecast</h2><p>Remember the city in the search box, your temperature unit, and the number of forecast days. Connection and cache settings stay in Sapphire’s plugin settings.</p><button class="sw-quiet" data-action="save">${icon('save')}Save current view</button><span class="sw-saving" role="status"></span></section>
  <div class="sw-empty"><div class="sw-empty-scene">${scene(2)}</div><h2>Your day, at a glance.</h2><p>One clear forecast. A little less scrolling.<br>Search for a city to get started.</p></div>
  <div class="sw-content sw-hidden"><div class="sw-stage"><article class="sw-hero"><div class="sw-place">${icon('pin')}<span>Local outlook</span></div><h1 class="sw-city"></h1><p class="sw-region"></p><div class="sw-temperature-row"><div class="sw-temperature"></div><div class="sw-scene"></div></div><p class="sw-condition"></p><p class="sw-highlow"></p><div class="sw-hero-bottom"><span class="sw-modeltime"></span><button class="sw-now" data-action="refresh">${icon('refresh')}Check weather</button></div></article><div class="sw-details"></div></div>
  <div class="sw-section-head"><h2>Your next few days</h2><label class="sw-sliderbox"><span class="sw-daycount">3 days</span><span class="sw-sr">Forecast days</span><input type="range" min="1" max="7" value="3" aria-label="Forecast days" aria-valuetext="3 forecast days"></label></div>
  <div class="sw-days" role="group" aria-label="Choose a forecast day"></div><div class="sw-selected" aria-live="polite"></div></div>
  <footer class="sw-footer"><details><summary>About this forecast</summary><p>Current conditions are modelled weather. Day cards show daily high / low temperatures and precipitation probability. This app respects the active chat’s privacy setting. Free provider access is for noncommercial use.</p><p>Data: <a href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">Open-Meteo</a> · <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer">CC BY 4.0</a> · <a href="https://www.geonames.org/" target="_blank" rel="noopener noreferrer">GeoNames</a></p></details><span class="sw-updated">No forecast loaded</span></footer>`;
  const q = selector => root.querySelector(selector);
  const input = q('input[name=location]');
  input.addEventListener('input',()=>{interacted=true;});
  const status = (message, error=false) => {q('.sw-status').textContent=message;q('.sw-status').dataset.error=String(error);};
  const formatted = value => value == null ? '—' : Math.round(value);
  const temp = value => formatted(temperature(value, weather.units, viewUnits));
  const updateUnits = () => root.querySelectorAll('[data-unit]').forEach(b => b.setAttribute('aria-pressed',String(b.dataset.unit === viewUnits)));
  const weekday = date => dayLabel(date,weather.timezone);
  function freshness() {
    if(!active||!weather)return;
    const first=weather.forecast[0];
    const label=weekday(first.date);
    q('.sw-highlow').textContent=`${label==='Today'?'Today’s':shortDate(first.date)} high ${temp(first.high)}°  ·  Low ${temp(first.low)}°`;
    q('.sw-modeltime').textContent=`Conditions · ${shortDate(weather.current.time.slice(0,10))}, ${weather.current.time.slice(11,16)} in ${weather.location.split(',')[0]}`;
    q('.sw-updated').textContent=`${weather.cached?'Cached · ':''}Fetched ${fetchedLabel(weather.fetched_at,weather.timezone)} · ${ageLabel(weather.fetched_at)}`;
    root.querySelectorAll('.sw-day').forEach((button,i)=>{const d=weather.forecast[i];button.querySelector('.sw-day-name').textContent=weekday(d.date);button.setAttribute('aria-label',`${weekday(d.date)}, ${d.condition}, high ${temp(d.high)} degrees, low ${temp(d.low)} degrees`);});
    const day=weather.forecast[selected];q('.sw-selected-title').textContent=`${weekday(day.date)} · ${day.condition}`;
    root.querySelectorAll('.sw-metric-note')[2].textContent=label==='Today'?'Today’s maximum chance':`${shortDate(first.date)} maximum chance`;
    if(isStale(weather,cacheMinutes)&&root.getAttribute('aria-busy')!=='true')status('This forecast is older. Check weather again after the cache expires.');
  }
  const freshnessTimer=setInterval(freshness,60000);

  function paint() {
    if (!active || !weather) return;
    selected = Math.min(selected, horizon - 1);
    q('.sw-empty').classList.add('sw-hidden');q('.sw-content').classList.remove('sw-hidden');
    const c=weather.current, today=weather.forecast[0], day=weather.forecast[selected];
    const parts=weather.location.split(',');q('.sw-city').textContent=parts[0];q('.sw-region').textContent=parts.slice(1).join(',').trim() || 'Coordinates · '+weather.timezone.replaceAll('_',' ');
    q('.sw-temperature').innerHTML=`${temp(c.temperature)}<sup>°${viewUnits==='imperial'?'F':'C'}</sup>`;
    q('.sw-scene').innerHTML=scene(c.code);q('.sw-condition').textContent=c.condition;
    q('.sw-highlow').textContent=`Today’s high ${temp(today.high)}°  ·  Low ${temp(today.low)}°`;
    q('.sw-modeltime').textContent='Current conditions · '+c.time.slice(11,16)+' local';
    const wind=c.wind==null?null:(weather.units===viewUnits?c.wind:viewUnits==='imperial'?c.wind/1.609344:c.wind*1.609344);
    const precip=c.precipitation==null?null:(weather.units===viewUnits?c.precipitation:viewUnits==='imperial'?c.precipitation/25.4:c.precipitation*25.4);
    const metrics=[
      ['thermometer','Feels like',temp(c.feels_like),'°'+(viewUnits==='imperial'?'F':'C'),'Current conditions'],
      ['wind','Wind',wind==null?'—':Math.round(wind),viewUnits==='imperial'?'mph':'km/h','Current wind speed'],
      ['drop','Rain / snow chance',formatted(today.precipitation_probability),'%','Today’s maximum chance'],
      ['drop','Precipitation',precip==null?'—':Number(precip.toFixed(viewUnits==='imperial'?2:1)),viewUnits==='imperial'?'in':'mm','Provider reporting interval']
    ];
    q('.sw-details').innerHTML=metrics.map(([i,label,value,unit,note])=>`<article class="sw-metric"><div class="sw-metric-head"><span>${label}</span>${icon(i)}</div><div class="sw-metric-value">${value}<small>${unit}</small></div><p class="sw-metric-note">${note}</p></article>`).join('');
    q('.sw-daycount').textContent=`${horizon} ${horizon===1?'day':'days'}`;
    const days=q('.sw-days');days.style.setProperty('--sw-count',horizon);
    days.innerHTML=weather.forecast.slice(0,horizon).map((d,i)=>`<button class="sw-day" data-day="${i}" type="button" aria-pressed="${i===selected}" aria-label="${escape(weekday(d.date,i))}, ${escape(d.condition)}, high ${temp(d.high)} degrees, low ${temp(d.low)} degrees"><span class="sw-day-name">${escape(weekday(d.date,i))}</span><span class="sw-day-date">${escape(shortDate(d.date))}</span><span class="sw-day-icon">${scene(d.code)}</span><span class="sw-day-temps"><span>${temp(d.high)}°</span><span>${temp(d.low)}°</span></span><span class="sw-day-rain">${icon('drop')}${formatted(d.precipitation_probability)}%</span></button>`).join('');
    q('.sw-selected').innerHTML=`<div><div class="sw-selected-title">${escape(weekday(day.date,selected))} · ${escape(day.condition)}</div><p class="sw-selected-copy">${formatted(day.precipitation_probability)}% chance of rain or snow. Select another day to explore.</p></div><div class="sw-range-legend"><span>High <strong>${temp(day.high)}°</strong></span><span>Low <strong>${temp(day.low)}°</strong></span></div>`;
    freshness();
    updateUnits();
  }

  async function load(place=null) {
    const location=input.value.trim();if(!location){input.focus();return;}
    const id=++requestId;controller?.abort();controller=new AbortController();choices=[];
    root.setAttribute('aria-busy','true');q('button[type=submit]').disabled=true;status('Checking the forecast…');q('.sw-choices').classList.add('sw-hidden');
    try {
      await contextPromise;if(!active||id!==requestId)return;if(contextError||!contextToken)throw contextError||new Error('Reload Weather from a public chat.');
      const args=place?{latitude:place.latitude,longitude:place.longitude,units:viewUnits,days:7}:{location,units:viewUnits,days:7};
      args._context=contextToken;
      const response=await fetch('/api/plugin/sapphire-weather/forecast',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name="csrf-token"]')?.content||''},body:JSON.stringify(args),signal:controller.signal});
      const data=await response.json().catch(()=>({error:response.status===401?'Sign in again, then reload Weather.':`Weather request failed (HTTP ${response.status}). Please try again.`}));
      if(!active||id!==requestId)return;
      choices=Array.isArray(data.choices)?data.choices:[];
      if(!response.ok||!data.success)throw new Error(data.error||'Weather is unavailable. Please try again.');
      if(!active||id!==requestId)return;
      weather=data.weather;if(place){weather.location=place.label;input.value=place.label;}selected=0;paint();status('Forecast ready. Tap a day for a closer look.');
    } catch(error) {
      if(!active||id!==requestId||error.name==='AbortError')return;
      status(error.message,true);
      if(choices.length){q('.sw-choices').innerHTML=choices.map((p,i)=>`<button class="sw-quiet" type="button" data-choice="${i}">${icon('pin')}${escape(p.label)}</button>`).join('');q('.sw-choices').classList.remove('sw-hidden');}
      // Never leave an old forecast visible after a privacy/error response.
      weather=null;q('.sw-content').classList.add('sw-hidden');q('.sw-empty').classList.remove('sw-hidden');
      q('.sw-updated').textContent='No current forecast';
    } finally {
      if(active&&id===requestId){root.setAttribute('aria-busy','false');q('button[type=submit]').disabled=false;freshness();}
    }
  }
  q('form').addEventListener('submit',event=>{event.preventDefault();interacted=true;load();});
  q('input[type=range]').addEventListener('input',event=>{interacted=true;horizon=Number(event.target.value);event.target.setAttribute('aria-valuetext',`${horizon} forecast days`);paint();});
  root.addEventListener('click',async event=>{
    const button=event.target.closest('button');if(!button||!root.contains(button))return;
    if(button.dataset.unit){interacted=true;viewUnits=button.dataset.unit;updateUnits();paint();}
    if(button.dataset.day!=null){selected=Number(button.dataset.day);paint();q(`[data-day="${selected}"]`)?.focus({preventScroll:true});}
    if(button.dataset.choice!=null){const choice=choices[Number(button.dataset.choice)];if(choice)load(choice);}
    if(button.dataset.action==='refresh')load();
    if(button.dataset.action==='preferences'){
      const open=q('.sw-preferences').classList.toggle('sw-hidden')===false;button.setAttribute('aria-expanded',String(open));
    }
    if(button.dataset.action==='save'){
      const location=input.value.trim();if(!location){status('Enter a city before saving.',true);input.focus();return;}
      button.disabled=true;
      try{await pluginsAPI.saveSettings('sapphire-weather',{default_location:location,units:viewUnits,forecast_days:horizon});if(active)q('.sw-saving').textContent='  Saved for next visit.';}
      catch(error){if(active)status('Could not save: '+error.message,true);}finally{if(active)button.disabled=false;}
    }
  });
  pluginsAPI.getSettings('sapphire-weather').then(saved=>{
    if(!active)return;
    cacheMinutes=typeof saved.cache_minutes==='number'&&saved.cache_minutes>=1&&saved.cache_minutes<=60?saved.cache_minutes:10;
    if(interacted)return;
    viewUnits=saved.units==='imperial'?'imperial':'metric';
    horizon=Number.isInteger(saved.forecast_days)&&saved.forecast_days>=1&&saved.forecast_days<=7?saved.forecast_days:3;
    q('input[type=range]').value=horizon;q('input[type=range]').setAttribute('aria-valuetext',`${horizon} forecast days`);updateUnits();
    input.value=typeof saved.default_location==='string'?saved.default_location:'';
    if(input.value)load();
  }).catch(()=>{if(active)status('Saved preferences could not load. You can still search for a city.',true);});
  return ()=>{active=false;requestId++;controller?.abort();clearInterval(freshnessTimer);root.remove();link.remove();};
}
