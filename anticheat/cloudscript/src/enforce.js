const cfg = require("./config");
const pf = require("./playfab");
const discord = require("./discord");

const STATE_KEY = "ac_state";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function loadState(playFabId) {
  const raw = await pf.getInternal(playFabId, STATE_KEY);
  try {
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

const saveState = (playFabId, s) => pf.setInternal(playFabId, STATE_KEY, JSON.stringify(s));

const isShadowed = (s, now) => !cfg.dryRun && (s.shadowUntil || 0) > now;
const isAttested = (s, now) => (s.attestedUntil || 0) > now;

async function lag(s, now) {
  if (!isShadowed(s, now)) return;
  await sleep(cfg.lagMinMs + Math.random() * (cfg.lagMaxMs - cfg.lagMinMs));
}

async function notifyDiscord(playFabId, details, context) {
  try {
    const name = await pf.displayName(playFabId).catch(() => "(unknown)");
    await discord.reportCheater({ playFabId, name, dryRun: cfg.dryRun, ...details });
  } catch (e) {
    if (context) context.warn(`discord notify failed: ${e.message}`);
  }
}

async function punish(playFabId, s, verdict, platform, now, context) {
  const log = { platform, severity: verdict.severity, reasons: verdict.reasons, dryRun: cfg.dryRun };
  if (cfg.dryRun) {
    await Promise.all([
      pf.event(playFabId, "ac_violation", log),
      notifyDiscord(playFabId, { ...log, action: "dry_run" }, context),
    ]);
    return { action: "dry_run" };
  }

  s.strikes = (s.strikes || 0) + 1;
  s.attestedUntil = 0;
  s.shadowUntil = now + cfg.shadowDays * 86_400_000;
  s.history = [...(s.history || []).slice(-9), { t: now, severity: verdict.severity, reasons: verdict.reasons }];

  const ladder = cfg.banLadderHours;
  const hours = verdict.severity === "tamper" ? cfg.banHoursTamper : ladder[Math.min(s.strikes, ladder.length) - 1];
  const reason =
    verdict.severity === "device"
      ? "Rooted or untrusted device detected"
      : verdict.severity === "tamper"
        ? "Modified game client detected"
        : "Anti-cheat verification failed";

  await saveState(playFabId, s);
  await Promise.all([
    pf.ban(playFabId, hours, reason),
    pf.addTag(playFabId, "ac_cheater"),
    pf.event(playFabId, "ac_violation", { ...log, strikes: s.strikes, banHours: hours }),
    notifyDiscord(playFabId, { ...log, action: "banned", banHours: hours, strikes: s.strikes }, context),
  ]);
  return { action: "banned", banHours: hours };
}

async function requireAttested(playFabId) {
  const now = Date.now();
  const s = await loadState(playFabId);
  await lag(s, now);
  if (!cfg.dryRun && !isAttested(s, now)) {
    const err = new Error("not_attested");
    err.code = "not_attested";
    throw err;
  }
  return s;
}

module.exports = { loadState, saveState, isShadowed, isAttested, lag, punish, requireAttested };
