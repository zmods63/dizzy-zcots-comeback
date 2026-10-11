var AC_DEFAULTS = {
  dryRun: true,
  banHours: null,
  revert: true,
  wipeCurrency: true,
  tag: "ac_cheater",
  moderators: [],
  modCurrencyCap: 1000000,
  bannedIds: [],
  forbiddenItems: [],
  currencyCaps: {},
  maxCurrencyGain: {},
  statCaps: {},
  maxStatJump: {}
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

function acIsMod(cfg, id) {
  return cfg.moderators.indexOf(id) !== -1;
}

function acIsBlocked(cfg, id) {
  return cfg.bannedIds.indexOf(id) !== -1;
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

function acDiscord(cfg, title, color, fields) {
  if (!cfg.webhook) return;
  var payload = {
    username: "Anti-Cheat",
    allowed_mentions: { parse: [] },
    embeds: [{ title: title, color: color, fields: fields, timestamp: new Date().toISOString() }]
  };
  try {
    http.request(cfg.webhook, "post", JSON.stringify(payload), "application/json");
  } catch (e) {
    log.error("discord webhook failed: " + e);
  }
}

function acReport(cfg, playFabId, kind, detail, actions, title) {
  acDiscord(cfg,
    title || (cfg.dryRun ? "Cheater detected (DRY RUN - not punished)" : "Cheater detected & banned"),
    cfg.dryRun ? 7091440 : 14689316,
    [
      { name: "Name", value: acEscape(acDisplayName(playFabId), 100), inline: true },
      { name: "PlayFab ID", value: acEscape(playFabId, 32), inline: true },
      { name: "Cheat", value: acEscape(kind, 50), inline: true },
      { name: "Action", value: acEscape(actions.join(", "), 300) },
      { name: "Details", value: acEscape(detail, 1000) }
    ]);
}

function acWipeCurrency(playFabId, balances) {
  var wiped = [];
  for (var code in balances) {
    if (balances[code] > 0) {
      server.SubtractUserVirtualCurrency({ PlayFabId: playFabId, VirtualCurrency: code, Amount: balances[code] });
      wiped.push(code + " " + balances[code]);
    }
  }
  return wiped;
}

function acPunish(cfg, playFabId, kind, detail, undo, balances) {
  var actions = [];
  if (cfg.dryRun) {
    actions.push("none (dry run)");
  } else {
    if (cfg.revert && undo) {
      try { var undone = undo(); if (undone) actions.push(undone); } catch (e) { log.error("revert failed: " + e); }
    }
    if (cfg.wipeCurrency) {
      try {
        var wiped = acWipeCurrency(playFabId, balances || server.GetUserInventory({ PlayFabId: playFabId }).VirtualCurrency || {});
        if (wiped.length) actions.push("wiped " + wiped.join(", "));
      } catch (e) { log.error("wipe failed: " + e); }
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
  acReport(cfg, playFabId, kind, detail, actions);
  log.info("AC " + kind + " " + playFabId + ": " + detail + " -> " + actions.join(", "));
  return { violation: kind, detail: detail, actions: actions };
}

function acModAlert(cfg, playFabId, kind, detail, actions) {
  acDiscord(cfg, "Moderator account over limit (not banned)", 16096779, [
    { name: "Name", value: acEscape(acDisplayName(playFabId), 100), inline: true },
    { name: "PlayFab ID", value: acEscape(playFabId, 32), inline: true },
    { name: "Issue", value: acEscape(kind, 50), inline: true },
    { name: "Action", value: acEscape(actions.join(", ") || "none", 300) },
    { name: "Details", value: acEscape(detail, 1000) }
  ]);
  return { modAlert: kind, detail: detail, actions: actions };
}

function acPlayerId(context) {
  var ev = context && context.playStreamEvent;
  return (ev && ev.EntityId) || currentPlayerId;
}

function acCheckPlayer(cfg, id) {
  var inv = server.GetUserInventory({ PlayFabId: id });
  var items = inv.Inventory || [];
  var balances = inv.VirtualCurrency || {};
  var isMod = acIsMod(cfg, id);
  var reasons = [];

  if (acIsBlocked(cfg, id)) reasons.push("blocked PlayFab ID");

  var bad = [];
  if (!isMod) {
    for (var i = 0; i < items.length; i++) {
      if (cfg.forbiddenItems.indexOf(items[i].ItemId) !== -1) bad.push(items[i]);
    }
  }
  if (bad.length) reasons.push("owns staff-only cosmetic: " + bad.map(function (x) { return x.ItemId; }).join(", "));

  var over = [];
  for (var code in balances) {
    var cap = isMod ? cfg.modCurrencyCap : cfg.currencyCaps[code];
    if (cap !== undefined && cap !== null && balances[code] > cap) over.push({ code: code, amount: balances[code], cap: cap });
  }

  if (isMod && !reasons.length) {
    if (!over.length) return { ok: true, moderator: true };
    var modActions = [];
    if (!cfg.dryRun && cfg.revert) {
      over.forEach(function (o) {
        server.SubtractUserVirtualCurrency({ PlayFabId: id, VirtualCurrency: o.code, Amount: o.amount - o.cap });
        modActions.push(o.code + " trimmed to " + o.cap);
      });
    }
    return acModAlert(cfg, id, "mod_currency_over_cap",
      over.map(function (o) { return o.code + " " + o.amount + " > " + o.cap; }).join(", "), modActions);
  }

  if (over.length) reasons.push("coins over cap: " + over.map(function (o) { return o.code + " " + o.amount + " > " + o.cap; }).join(", "));
  if (!reasons.length) return { ok: true };

  var detail = reasons.join(" | ");
  var kind = acIsBlocked(cfg, id) ? "blocked_id" : bad.length ? "staff_cosmetic" : "currency_over_cap";
  return acPunish(cfg, id, kind, detail, function () {
    if (!bad.length) return null;
    server.RevokeInventoryItems({
      Items: bad.slice(0, 25).map(function (x) { return { PlayFabId: id, ItemInstanceId: x.ItemInstanceId }; })
    });
    return "revoked " + bad.map(function (x) { return x.ItemId; }).join(", ");
  }, balances);
}

handlers.AC_OnLogin = function (args, context) {
  return acCheckPlayer(acConfig(), acPlayerId(context));
};

handlers.AC_SweepBlockedIds = function (args, context) {
  var cfg = acConfig();
  var stored = server.GetTitleInternalData({ Keys: ["ac_swept"] }).Data || {};
  var done = stored.ac_swept ? JSON.parse(stored.ac_swept) : {};
  var todo = cfg.bannedIds.filter(function (id) { return !done[id]; }).slice(0, 5);
  if (!todo.length) return { swept: [] };

  var banned = [], failed = [];
  if (!cfg.dryRun) {
    todo.forEach(function (id) {
      var b = { PlayFabId: id, Reason: "Cheating detected: blocked_id" };
      if (cfg.banHours) b.DurationInHours = cfg.banHours;
      try {
        server.BanUsers({ Bans: [b] });
        done[id] = Date.now();
        banned.push(id);
      } catch (e) {
        failed.push(id);
        log.error("sweep ban failed for " + id + ": " + e);
      }
    });
    server.SetTitleInternalData({ Key: "ac_swept", Value: JSON.stringify(done) });
  }

  var list = (cfg.dryRun ? todo : banned).map(function (id) { return acEscape(acDisplayName(id), 60) + " - " + acEscape(id, 32); });
  if (list.length) {
    acDiscord(cfg,
      cfg.dryRun ? "Blocked IDs found (DRY RUN - not banned)" : "Blocked IDs banned",
      cfg.dryRun ? 7091440 : 14689316,
      [
        { name: "Players", value: list.join("\n").slice(0, 1000) },
        { name: "Action", value: cfg.dryRun ? "none (dry run)" : (cfg.banHours ? "banned " + cfg.banHours + "h" : "banned permanently") }
      ]);
  }
  return {
    swept: banned,
    failed: failed,
    wouldBan: cfg.dryRun ? todo : [],
    remaining: cfg.bannedIds.filter(function (id) { return !done[id]; }).length
  };
};

handlers.AC_OnCurrencyChanged = function (args, context) {
  var ev = context.playStreamEvent || {};
  var code = ev.VirtualCurrencyName;
  var balance = Number(ev.VirtualCurrencyBalance);
  var previous = Number(ev.VirtualCurrencyPreviousBalance);
  if (!code || isNaN(balance)) return { skipped: "unexpected event" };
  var cfg = acConfig();
  var id = acPlayerId(context);
  if (acIsBlocked(cfg, id)) return acCheckPlayer(cfg, id);
  var gain = isNaN(previous) ? 0 : balance - previous;

  if (acIsMod(cfg, id)) {
    if (balance <= cfg.modCurrencyCap) return { ok: true, moderator: true };
    var modActions = [];
    if (!cfg.dryRun && cfg.revert) {
      server.SubtractUserVirtualCurrency({ PlayFabId: id, VirtualCurrency: code, Amount: balance - cfg.modCurrencyCap });
      modActions.push(code + " trimmed to " + cfg.modCurrencyCap);
    }
    return acModAlert(cfg, id, "mod_currency_over_cap", code + " " + balance + " > " + cfg.modCurrencyCap, modActions);
  }

  var cap = cfg.currencyCaps[code];
  if (cap !== undefined && balance > cap) {
    var target = isNaN(previous) ? cap : Math.min(previous, cap);
    return acPunish(cfg, id, "currency_over_cap",
      code + " balance " + balance + " > cap " + cap,
      function () { server.SubtractUserVirtualCurrency({ PlayFabId: id, VirtualCurrency: code, Amount: balance - target }); return "removed " + (balance - target) + " " + code; });
  }
  var maxGain = cfg.maxCurrencyGain[code];
  if (maxGain !== undefined && gain > maxGain) {
    return acPunish(cfg, id, "currency_gain_too_big",
      code + " +" + gain + " in one change (max " + maxGain + ")",
      function () { server.SubtractUserVirtualCurrency({ PlayFabId: id, VirtualCurrency: code, Amount: gain }); return "removed " + gain + " " + code; });
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
  if (acIsBlocked(cfg, id)) return acCheckPlayer(cfg, id);
  if (acIsMod(cfg, id)) return { ok: true, moderator: true };

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
  var id = acPlayerId(context);
  if (acIsBlocked(cfg, id)) return acCheckPlayer(cfg, id);
  if (acIsMod(cfg, id) || cfg.forbiddenItems.indexOf(ev.ItemId) === -1) return { ok: true };
  return acPunish(cfg, id, "staff_cosmetic", "got " + ev.ItemId + " (" + (ev.DisplayName || "") + ")",
    ev.InstanceId ? function () {
      server.RevokeInventoryItem({ PlayFabId: id, ItemInstanceId: ev.InstanceId });
      return "revoked " + ev.ItemId;
    } : null);
};
