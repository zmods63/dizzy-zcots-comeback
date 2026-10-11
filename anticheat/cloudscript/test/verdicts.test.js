const test = require("node:test");
const assert = require("node:assert");
const android = require("../src/android");
const quest = require("../src/quest");
const { normDigest } = require("../src/digest");

const HEX = "AB:CD:EF:01:23:45:67:89:AB:CD:EF:01:23:45:67:89:AB:CD:EF:01:23:45:67:89:AB:CD:EF:01:23:45:67:89";
const B64 = Buffer.from(HEX.replace(/:/g, ""), "hex").toString("base64url");
const NOW = 1_700_000_000_000;
const NONCE = "abcdefghijklmnopqrstuvwxyz0123456789ABCD";

const acfg = {
  packageName: "com.test.game",
  certSha256: [HEX],
  requirePlayRecognized: true,
  requireStrong: false,
  requireLicensed: false,
  blockControllingApps: true,
  maxTokenAgeMs: 120_000,
};

const cleanAndroid = () => ({
  requestDetails: { requestPackageName: "com.test.game", nonce: NONCE, timestampMillis: String(NOW - 5000) },
  appIntegrity: { appRecognitionVerdict: "PLAY_RECOGNIZED", packageName: "com.test.game", certificateSha256Digest: [B64] },
  deviceIntegrity: { deviceRecognitionVerdict: ["MEETS_BASIC_INTEGRITY", "MEETS_DEVICE_INTEGRITY"] },
  accountDetails: { appLicensingVerdict: "LICENSED" },
});

test("hex and base64url digests normalize equal", () => {
  assert.strictEqual(normDigest(HEX), normDigest(B64));
  assert.strictEqual(normDigest(HEX), normDigest(Buffer.from(HEX.replace(/:/g, ""), "hex").toString("base64")));
});

test("android: clean device passes", () => {
  assert.deepStrictEqual(android.judge(cleanAndroid(), NONCE, NOW, acfg), { ok: true, severity: undefined, reasons: [] });
});

test("android: re-signed APK (frida gadget) is tamper", () => {
  const p = cleanAndroid();
  p.appIntegrity = { appRecognitionVerdict: "UNRECOGNIZED_VERSION", packageName: "com.test.game", certificateSha256Digest: ["other"] };
  const v = android.judge(p, NONCE, NOW, acfg);
  assert.strictEqual(v.severity, "tamper");
  assert.ok(v.reasons.includes("cert_mismatch"));
  assert.ok(v.reasons.includes("app_unrecognized_version"));
});

test("android: sideload mode still catches wrong cert", () => {
  const p = cleanAndroid();
  p.appIntegrity.appRecognitionVerdict = "UNRECOGNIZED_VERSION";
  assert.strictEqual(android.judge(p, NONCE, NOW, { ...acfg, requirePlayRecognized: false }).ok, true);
  p.appIntegrity.certificateSha256Digest = ["other"];
  assert.strictEqual(android.judge(p, NONCE, NOW, { ...acfg, requirePlayRecognized: false }).severity, "tamper");
});

test("android: rooted device is device severity", () => {
  const p = cleanAndroid();
  p.deviceIntegrity.deviceRecognitionVerdict = ["MEETS_BASIC_INTEGRITY"];
  const v = android.judge(p, NONCE, NOW, acfg);
  assert.strictEqual(v.severity, "device");
});

test("android: no integrity at all + unevaluated app is device severity", () => {
  const p = cleanAndroid();
  p.appIntegrity = { appRecognitionVerdict: "UNEVALUATED" };
  p.deviceIntegrity = {};
  const v = android.judge(p, NONCE, NOW, acfg);
  assert.strictEqual(v.severity, "device");
  assert.ok(v.reasons.includes("device_no_integrity"));
});

test("android: strong integrity mode rejects plain device integrity", () => {
  assert.strictEqual(android.judge(cleanAndroid(), NONCE, NOW, { ...acfg, requireStrong: true }).severity, "device");
});

test("android: replayed token (wrong nonce / stale) is invalid", () => {
  assert.strictEqual(android.judge(cleanAndroid(), "different", NOW, acfg).severity, "invalid");
  const p = cleanAndroid();
  p.requestDetails.timestampMillis = String(NOW - 10 * 60_000);
  assert.strictEqual(android.judge(p, NONCE, NOW, acfg).severity, "invalid");
});

test("android: controlling app detected", () => {
  const p = cleanAndroid();
  p.environmentDetails = { appAccessRiskVerdict: { appsDetected: ["KNOWN_INSTALLED", "UNKNOWN_CONTROLLING"] } };
  assert.strictEqual(android.judge(p, NONCE, NOW, acfg).severity, "device");
});

const qcfg = { packageName: "com.test.game", certSha256: [], allowBasicDevice: true, maxTokenAgeMs: 120_000 };
const cleanQuest = () => ({
  request_details: { nonce: NONCE, timestamp: Math.floor((NOW - 5000) / 1000) },
  app_state: { app_integrity_state: "StoreRecognized", package_id: "com.test.game" },
  device_state: { device_integrity_state: "Advanced" },
});

test("quest: clean passes, sideloaded is tamper, untrusted device is device", () => {
  assert.strictEqual(quest.judge(cleanQuest(), NONCE, NOW, qcfg).ok, true);
  const side = cleanQuest();
  side.app_state.app_integrity_state = "NotRecognized";
  assert.strictEqual(quest.judge(side, NONCE, NOW, qcfg).severity, "tamper");
  const dev = cleanQuest();
  dev.device_state.device_integrity_state = "NotTrusted";
  assert.strictEqual(quest.judge(dev, NONCE, NOW, qcfg).severity, "device");
});

test("quest: unknown claims shape is error, never a ban", () => {
  assert.strictEqual(quest.judge({ foo: 1 }, NONCE, NOW, qcfg).severity, "error");
});
