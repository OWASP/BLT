const RANGES = [
  [0, 59],
  [0, 23],
  [1, 31],
  [1, 12],
  [0, 6],
];

function parseField(field, [min, max]) {
  const values = new Set();
  for (const part of field.split(",")) {
    const [range, stepText] = part.split("/");
    const step = stepText === undefined ? 1 : Number(stepText);
    if (!Number.isInteger(step) || step < 1) throw new Error(`bad step in "${field}"`);
    let lo, hi;
    if (range === "*") {
      [lo, hi] = [min, max];
    } else if (range.includes("-")) {
      [lo, hi] = range.split("-").map(Number);
    } else {
      lo = Number(range);
      hi = stepText === undefined ? lo : max;
    }
    if (!Number.isInteger(lo) || !Number.isInteger(hi) || lo < min || hi > max || lo > hi) {
      throw new Error(`bad value in "${field}"`);
    }
    for (let v = lo; v <= hi; v += step) values.add(v);
  }
  return values;
}

// Standard 5-field cron in UTC: minute hour day-of-month month day-of-week (0 or 7 = Sunday).
export function parseCron(expression) {
  const fields = String(expression).trim().split(/\s+/);
  if (fields.length !== 5) throw new Error(`cron needs 5 fields: "${expression}"`);
  const dow = fields[4].replace(/\b7\b/g, "0");
  return {
    minute: parseField(fields[0], RANGES[0]),
    hour: parseField(fields[1], RANGES[1]),
    day: parseField(fields[2], RANGES[2]),
    month: parseField(fields[3], RANGES[3]),
    weekday: parseField(dow, RANGES[4]),
    dayAny: fields[2] === "*",
    weekdayAny: fields[4] === "*",
  };
}

export function cronMatches(expression, date) {
  const c = parseCron(expression);
  if (!c.minute.has(date.getUTCMinutes()) || !c.hour.has(date.getUTCHours())) return false;
  if (!c.month.has(date.getUTCMonth() + 1)) return false;
  const dayOk = c.day.has(date.getUTCDate());
  const weekdayOk = c.weekday.has(date.getUTCDay());
  if (c.dayAny && c.weekdayAny) return true;
  if (c.dayAny) return weekdayOk;
  if (c.weekdayAny) return dayOk;
  return dayOk || weekdayOk;
}
