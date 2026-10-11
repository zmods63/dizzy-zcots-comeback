const crypto = require("crypto");
const { app } = require("@azure/functions");
const cfg = require("../config");
const ac = require("../enforce");
const android = require("../android");
const quest = require("../quest");

const verifiers = { android: android.verify, quest: quest.verify };

function playfabFunction(name, fn) {
  app.http(name, {
    methods: ["POST"],
    authLevel: "function",
    handler: async (request, context) => {
      try {
        const body = await request.json();
        const playFabId = body?.CallerEntityProfile?.Lineage?.MasterPlayerAccountId;
        if (!playFabId) return { status: 400, jsonBody: { error: "missing_caller" } };
        return { jsonBody: await fn(playFabId, body.FunctionArgument || {}, context) };
      } catch (e) {
        context.error(e);
        return { status: 500, jsonBody: { error: "internal_error" } };
      }
    },
  });
}

playfabFunction("AC_GetChallenge", async (playFabId) => {
  const now = Date.now();
  const s = await ac.loadState(playFabId);
  await ac.lag(s, now);
  const nonce = crypto.randomBytes(30).toString("base64url");
  s.nonce = { v: nonce, exp: now + cfg.nonceTtlMs };
  await ac.saveState(playFabId, s);
  return { nonce };
});

playfabFunction("AC_Attest", async (playFabId, arg, context) => {
  const now = Date.now();
  const s = await ac.loadState(playFabId);
  await ac.lag(s, now);

  if (s.lastAttempt && now - s.lastAttempt < cfg.minAttestIntervalMs) return { ok: false, retry: true, reason: "too_fast" };
  const nonce = s.nonce && s.nonce.exp > now ? s.nonce.v : null;
  s.nonce = null;
  s.lastAttempt = now;

  const platform = String(arg.platform || "");
  const token = arg.token;
  let verdict;
  if (!nonce) {
    await ac.saveState(playFabId, s);
    return { ok: false, retry: true, reason: "challenge_expired" };
  } else if (!cfg.platforms.includes(platform)) {
    verdict = { ok: false, severity: "invalid", reasons: [`platform_not_allowed:${platform}`] };
  } else if (typeof token !== "string" || token.length < 20 || token.length > 20000) {
    verdict = { ok: false, severity: "invalid", reasons: ["missing_token"] };
  } else {
    try {
      verdict = await verifiers[platform](token, nonce, now);
    } catch (e) {
      context.warn(`verifier error for ${playFabId}: ${e.message}`);
      verdict = { ok: false, severity: "error", reasons: ["verifier_unavailable"] };
    }
  }

  if (verdict.ok) {
    s.attestedUntil = now + cfg.attestTtlMs;
    s.platform = platform;
    await ac.saveState(playFabId, s);
    return { ok: true, validForMs: cfg.attestTtlMs };
  }

  if (verdict.severity === "error") {
    if (verdict.raw) context.warn(`unexpected attestation claims: ${JSON.stringify(verdict.raw)}`);
    if (cfg.failOpen) s.attestedUntil = now + cfg.failOpenTtlMs;
    await ac.saveState(playFabId, s);
    return { ok: cfg.failOpen, retry: true, reason: "verifier_unavailable" };
  }

  context.log(`AC violation ${playFabId} ${platform} ${verdict.severity}: ${verdict.reasons.join(",")}`);
  const result = await ac.punish(playFabId, s, verdict, platform, now, context);
  if (result.action === "dry_run") {
    s.attestedUntil = now + cfg.attestTtlMs;
    await ac.saveState(playFabId, s);
    return { ok: true, dryRun: true };
  }
  return { ok: false, kick: true, reason: verdict.severity, banHours: result.banHours };
});

playfabFunction("AC_CheckPlayers", async (playFabId, arg) => {
  const now = Date.now();
  const caller = await ac.loadState(playFabId);
  await ac.lag(caller, now);

  const ids = [...new Set((arg.playFabIds || []).filter((x) => typeof x === "string" && /^[0-9A-F]{8,20}$/i.test(x)))].slice(0, 20);
  const players = {};
  await Promise.all(
    ids.map(async (id) => {
      try {
        const s = await ac.loadState(id);
        if (cfg.dryRun) players[id] = "ok";
        else players[id] = ac.isShadowed(s, now) ? "flagged" : ac.isAttested(s, now) ? "ok" : "unverified";
      } catch {
        players[id] = "unknown";
      }
    })
  );
  if (ac.isShadowed(caller, now)) for (const id of ids) players[id] = "ok";
  return { players };
});
