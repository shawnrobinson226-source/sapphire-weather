import test from 'node:test';
import assert from 'node:assert/strict';
import {locationDate,dayLabel,ageLabel,isStale} from '../app/weather-format.js';

test('Today follows the location date across midnight',()=>{
 const before=Date.parse('2026-10-18T06:50:00Z'),after=Date.parse('2026-10-18T07:20:00Z');
 assert.equal(locationDate('America/Los_Angeles',before),'2026-10-17');
 assert.equal(dayLabel('2026-10-17','America/Los_Angeles',before),'Today');
 assert.notEqual(dayLabel('2026-10-17','America/Los_Angeles',after),'Today');
 assert.equal(dayLabel('2026-10-18','America/Los_Angeles',after),'Today');
});
test('daylight saving boundary uses the named location timezone',()=>{
 assert.equal(locationDate('America/Los_Angeles',Date.parse('2026-11-01T08:30:00Z')),'2026-11-01');
 assert.equal(locationDate('America/Los_Angeles',Date.parse('2026-11-01T09:30:00Z')),'2026-11-01');
});
test('an overnight forecast is stale even inside its cache lifetime',()=>{
 const weather={timezone:'America/Los_Angeles',fetched_at:'2026-10-18T06:50:00Z',forecast:[{date:'2026-10-17'}]};
 assert.equal(isStale(weather,60,Date.parse('2026-10-18T07:20:00Z')),true);
 assert.equal(ageLabel(weather.fetched_at,Date.parse('2026-10-18T07:20:00Z')),'30 min ago');
});
test('cache age is visible and expires at the configured lifetime',()=>{
 const weather={timezone:'UTC',fetched_at:'2026-10-17T12:00:00Z',forecast:[{date:'2026-10-17'}]};
 assert.equal(isStale(weather,10,Date.parse('2026-10-17T12:09:00Z')),false);
 assert.equal(isStale(weather,10,Date.parse('2026-10-17T12:10:00Z')),true);
});
