const FALLBACK_TIMEZONE = 'UTC';

function supportedTimezones() {
  try {
    const values = Intl.supportedValuesOf('timeZone');
    return [...new Set([FALLBACK_TIMEZONE, ...values])];
  } catch (_error) {
    return [FALLBACK_TIMEZONE];
  }
}

export function detectTimezone() {
  const detected = Intl.DateTimeFormat().resolvedOptions().timeZone;
  return supportedTimezones().includes(detected) ? detected : FALLBACK_TIMEZONE;
}

export function populateTimezoneSelect(select, selectedTimezone = FALLBACK_TIMEZONE) {
  const zones = supportedTimezones();
  const selected = zones.includes(selectedTimezone) ? selectedTimezone : FALLBACK_TIMEZONE;
  const groups = new Map();

  for (const zone of zones.filter((value) => value !== FALLBACK_TIMEZONE)) {
    const [region = 'Other'] = zone.split('/');
    const values = groups.get(region) || [];
    values.push(zone);
    groups.set(region, values);
  }

  select.replaceChildren(new Option(FALLBACK_TIMEZONE, FALLBACK_TIMEZONE));

  for (const [region, zonesInRegion] of [...groups.entries()].sort(([left], [right]) => left.localeCompare(right))) {
    const group = document.createElement('optgroup');
    group.label = region;
    for (const zone of zonesInRegion.sort()) {
      group.append(new Option(zone, zone));
    }
    select.append(group);
  }

  select.value = selected;
  return selected;
}
