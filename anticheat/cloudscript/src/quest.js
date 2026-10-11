const cfg = require("./config");
const { certMatches } = require("./digest");

async function fetchClaims(token) {
  const q = cfg.quest;
  const url = new URL("https://graph.oculus.com/platform_integrity/verify");
  url.searchParams.set("token", token);
  url.searchParams.set("access_token", `OC|${q.appId}|${q.appSecret}`);
  const res = await fetch(url);
  const json = await res.json().catch(() => ({}));
  const entry = (json.data && json.data[0]) || {};
  if (entry.message && entry.message !== "success") return { invalid: true, detail: entry.message };
  if (!res.ok || !entry.claims) throw new Error(`Quest verify failed: ${res.status} ${JSON.stringify(json)}`);
  return { claims: JSON.parse(Buffer.from(entry.claims, "base64url").toString("utf8")) };
}

function judge(claims, expectedNonce, now, c = cfg.quest) {
  const rd = claims.request_details;
  const app = claims.app_state;
  const dev = claims.device_state;
  if (!rd || !app || !dev) return { ok: false, severity: "error", reasons: ["unexpected_claims_format"], raw: claims };

  const reasons = { tamper: [], invalid: [], device: [] };
  if (rd.nonce !== expectedNonce) reasons.invalid.push("nonce_mismatch");
  const ts = Number(rd.timestamp) * 1000;
  if (!(now - ts > -60_000 && now - ts < c.maxTokenAgeMs)) reasons.invalid.push("token_stale");

  if (app.app_integrity_state !== "StoreRecognized") reasons.tamper.push("app_not_store_recognized");
  if (c.packageName && app.package_id !== c.packageName) reasons.tamper.push("package_mismatch");
  if (!certMatches(app.package_cert_sha256_digest, c.certSha256)) reasons.tamper.push("cert_mismatch");

  const allowed = c.allowBasicDevice ? ["Advanced", "Basic"] : ["Advanced"];
  if (!allowed.includes(dev.device_integrity_state)) reasons.device.push(`device_${dev.device_integrity_state || "unknown"}`);

  const severity = ["tamper", "invalid", "device"].find((k) => reasons[k].length);
  return { ok: !severity, severity, reasons: [...reasons.tamper, ...reasons.invalid, ...reasons.device] };
}

async function verify(token, expectedNonce, now) {
  const { claims, invalid } = await fetchClaims(token);
  if (invalid) return { ok: false, severity: "invalid", reasons: ["token_rejected_by_meta"] };
  return judge(claims, expectedNonce, now);
}

module.exports = { verify, judge };
