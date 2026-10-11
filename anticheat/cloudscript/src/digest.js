function normDigest(s) {
  const raw = String(s).trim();
  const hex = raw.replace(/:/g, "");
  if (/^[0-9a-f]{64}$/i.test(hex)) return Buffer.from(hex, "hex").toString("base64url");
  return raw.replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
}

function certMatches(got, allowed) {
  if (!allowed.length) return true;
  const want = allowed.map(normDigest);
  return (got || []).map(normDigest).some((d) => want.includes(d));
}

module.exports = { normDigest, certMatches };
