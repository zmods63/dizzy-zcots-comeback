var AC_DEFAULTS = {
  dryRun: true,
  banHours: null,
  revert: true,
  tag: "ac_cheater",
  currencyCaps: {},
  maxCurrencyGain: {},
  statCaps: {},
  maxStatJump: {},
  forbiddenItems: []
};

function acConfig() {
  var cfg = JSON.parse(JSON.stringify(AC_DEFAULTS));
  var data = server.GetTitleInternalData({ Keys: ["ac_config", "ac_discord_webhook"] }).Data || {};
  if (data.ac_config) {
    var custom = JSON.parse(data.ac_config);
    for (var k in custom) cfg[k] = custom[k];
  }
  cfg.webhook = data.ac_discord_webhook || null;
  return cfg;
}

function acDisplayName(playFabId) {
  try {
    var r = server.GetPlayerProfile({ PlayFabId: playFabId, ProfileConstraints: { ShowDisplayName: true } });
    return (r.PlayerProfile && r.PlayerProfile.DisplayName) || "(no name)";
  } catch (e) {
    return "(unknown)";
  }
}

function acEscape(s, max) {
  return String(s === undefined || s === null ? "" : s).slice(0, max).replace(/[\\`*_~|>]/g, "\\$&") || "-";
}

function acDiscord(cfg, playFabId, name, kind, detail, action) {
  if (!cfg.webhook) return;
  var payload = {
    username: "Anti-Cheat",
    allowed_mentions: { parse: [] },
    embeds: [{
      title: cfg.dryRun ? "Cheater detected (DRY RUN - not punished)" : "Cheater detected & banned",
      color: cfg.dryRun ? 7091440 : 14689316,
      fields: [
        { name: "Name", value: acEscape(name, 100), inline: true },
        { name: "PlayFab ID", value: acEscape(playFabId, 32), inline: true },
        { name: "Cheat", value: acEscape(kind, 50), inline: true },
        { name: "Action", value: acEscape(action, 200) },
        { name: "Details", value: acEscape(detail, 1000) }
      ],
      timestamp: new Date().toISOString()
    }]
  };
  try {
    http.request(cfg.webhook, "post", JSON.stringify(payload), "application/json");
  } catch (e) {
    log.error("discord webhook failed: " + e);
  }
}

function acPunish(cfg, playFabId, kind, detail, undo) {
  var actions = [];
  if (cfg.dryRun) {
    actions.push("none (dry run)");
  } else {
    if (cfg.revert && undo) {
      try { undo(); actions.push("gain reverted"); } catch (e) { log.error("revert failed: " + e); }
    }
    var ban = { PlayFabId: playFabId, Reason: "Cheating detected: " + kind };
    if (cfg.banHours) ban.DurationInHours = cfg.banHours;
    server.BanUsers({ Bans: [ban] });
    server.AddPlayerTag({ PlayFabId: playFabId, TagName: cfg.tag });
    actions.push(cfg.banHours ? "banned " + cfg.banHours + "h" : "banned permanently");
  }
  server.WritePlayerEvent({
    PlayFabId: playFabId,
    EventName: "ac_violation",
    Body: { kind: kind, detail: detail, dryRun: cfg.dryRun }
  });
  acDiscord(cfg, playFabId, acDisplayName(playFabId), kind, detail, actions.join(", "));
  log.info("AC " + kind + " " + playFabId + ": " + detail + " -> " + actions.join(", "));
  return { violation: kind, detail: detail, actions: actions };
}

function acPlayerId(context) {
  var ev = context && context.playStreamEvent;
  return (ev && ev.EntityId) || currentPlayerId;
}

handlers.AC_OnCurrencyChanged = function (args, context) {
  var ev = context.playStreamEvent || {};
  var code = ev.VirtualCurrencyName;
  var balance = Number(ev.VirtualCurrencyBalance);
  var previous = Number(ev.VirtualCurrencyPreviousBalance);
  if (!code || isNaN(balance)) return { skipped: "unexpected event" };
  var cfg = acConfig();
  var id = acPlayerId(context);
  var gain = isNaN(previous) ? 0 : balance - previous;

  var cap = cfg.currencyCaps[code];
  if (cap !== undefined && balance > cap) {
    var target = isNaN(previous) ? cap : Math.min(previous, cap);
    return acPunish(cfg, id, "currency_over_cap",
      code + " balance " + balance + " > cap " + cap,
      function () { server.SubtractUserVirtualCurrency({ PlayFabId: id, VirtualCurrency: code, Amount: balance - target }); });
  }
  var maxGain = cfg.maxCurrencyGain[code];
  if (maxGain !== undefined && gain > maxGain) {
    return acPunish(cfg, id, "currency_gain_too_big",
      code + " +" + gain + " in one change (max " + maxGain + ")",
      function () { server.SubtractUserVirtualCurrency({ PlayFabId: id, VirtualCurrency: code, Amount: gain }); });
  }
  return { ok: true };
};

handlers.AC_OnStatisticChanged = function (args, context) {
  var ev = context.playStreamEvent || {};
  var stat = ev.StatisticName;
  var value = Number(ev.StatisticValue);
  var previous = Number(ev.StatisticPreviousValue);
  if (!stat || isNaN(value)) return { skipped: "unexpected event" };
  var cfg = acConfig();
  var id = acPlayerId(context);

  var cap = cfg.statCaps[stat];
  if (cap !== undefined && value > cap) {
    return acPunish(cfg, id, "stat_over_cap", stat + " = " + value + " > cap " + cap, null);
  }
  var maxJump = cfg.maxStatJump[stat];
  if (maxJump !== undefined && !isNaN(previous) && value - previous > maxJump) {
    return acPunish(cfg, id, "stat_jump_too_big", stat + " " + previous + " -> " + value + " (max jump " + maxJump + ")", null);
  }
  return { ok: true };
};

handlers.AC_OnItemAdded = function (args, context) {
  var ev = context.playStreamEvent || {};
  if (!ev.ItemId) return { skipped: "unexpected event" };
  var cfg = acConfig();
  if (cfg.forbiddenItems.indexOf(ev.ItemId) === -1) return { ok: true };
  var id = acPlayerId(context);
  return acPunish(cfg, id, "forbidden_item", "got " + ev.ItemId + " (" + (ev.DisplayName || "") + ")",
    ev.InstanceId ? function () { server.RevokeInventoryItem({ PlayFabId: id, ItemInstanceId: ev.InstanceId }); } : null);
};
