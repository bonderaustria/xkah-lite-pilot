class XKahCard extends HTMLElement {
  constructor() {
    super();
    this._iv = null;
    this._prevStatus = null;
    this._sessionStart = null;
    this._preheatStart = null;
    this._built = false;
  }

  connectedCallback() {
    this._startTimer();
  }

  disconnectedCallback() {
    this._stopTimer();
  }

  _startTimer() {
    if (!this._iv) this._iv = setInterval(() => this._tick(), 500);
  }

  _stopTimer() {
    if (this._iv) { clearInterval(this._iv); this._iv = null; }
  }

  set hass(h) {
    this._hass = h;
    if (!this._config) return;
    var e = this._ents();
    var st = this._st(e.status);

    if (st !== this._prevStatus) {
      if (st === "preheating") {
        var r = this._num(e.remaining);
        this._preheatStart = (r > 0 && r < 480) ? Date.now() - (480 - r) * 1000 : Date.now();
      }
      if (st === "ready") {
        var sr = this._num(e.session_remaining);
        this._sessionStart = (sr > 0 && sr < 3000) ? Date.now() - (3000 - sr) * 1000 : Date.now();
      }
      this._prevStatus = st;
      this._build();
    }

    this._tick();
    this._startTimer();
  }

  setConfig(c) { if (!c.entity) throw new Error("entity required"); this._config = c; }
  static getStubConfig() { return { entity: "" }; }
  getCardSize() { return 4; }

  _ents() {
    var name = this._config.entity.replace("sensor.", "").replace("_status", "");
    return {
      status: this._config.entity,
      remaining: "sensor." + name + "_verbleibend",
      session_remaining: "sensor." + name + "_session_verbleibend",
      power: "sensor." + name + "_aktuelle_leistung",
      sw: "switch." + name + "_steckdose"
    };
  }

  _st(id) { var s = this._hass && this._hass.states[id]; return s ? s.state : "off"; }
  _num(id) { var v = parseFloat(this._st(id)); return isNaN(v) ? 0 : v; }

  _fmt(sec) {
    if (sec < 0) sec = 0;
    sec = Math.floor(sec);
    var m = Math.floor(sec / 60), s = sec % 60;
    return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
  }

  _tick() {
    if (!this._hass || !this._config || !this._built) return;
    var e = this._ents();
    var status = this._st(e.status);
    var timer = this.querySelector("#t");
    var ring = this.querySelector("#r");
    var stEl = this.querySelector("#s");
    var pwEl = this.querySelector("#p");
    var icEl = this.querySelector("#i");
    if (!timer || !ring) return;

    var C = 339.292;
    var now = Date.now();

    if (status === "preheating" && this._preheatStart) {
      var elapsed = (now - this._preheatStart) / 1000;
      var rem = Math.max(0, 480 - elapsed);
      var fill = rem / 480;
      timer.textContent = this._fmt(rem);
      ring.setAttribute("stroke-dashoffset", (C * (1 - fill)).toFixed(1));
      ring.setAttribute("stroke", "#ff6b35");
      if (stEl) stEl.style.color = "#ff6b35";
      if (icEl) icEl.style.color = "#ff6b35";
    } else if (status === "ready" && this._sessionStart) {
      var elapsed = (now - this._sessionStart) / 1000;
      var rem = Math.max(0, 3000 - elapsed);
      var fill = rem / 3000;
      var col = fill > 0.5 ? "#4caf50" : fill > 0.3 ? "#ffc107" : "#f44336";
      timer.textContent = this._fmt(rem);
      ring.setAttribute("stroke-dashoffset", (C * (1 - fill)).toFixed(1));
      ring.setAttribute("stroke", col);
      if (stEl) stEl.style.color = col;
      if (icEl) icEl.style.color = col;
    }

    if (pwEl) pwEl.textContent = this._num(e.power).toFixed(0) + " W";

    var dotEl = this.querySelector("#dot");
    var lblEl = this.querySelector("#slbl");
    if (dotEl && lblEl) {
      var swState = this._st(e.sw) === "on";
      dotEl.style.background = swState ? "#4caf50" : "#555";
      dotEl.style.boxShadow = swState ? "0 0 8px rgba(76,175,80,.5)" : "none";
      lblEl.textContent = "Steckdose " + (swState ? "Ein" : "Aus");
    }
  }

  _toggle() {
    var e = this._ents();
    var s = this._st(e.sw);
    this._hass.callService("switch", s === "on" ? "turn_off" : "turn_on", { entity_id: e.sw });
  }

  _build() {
    var e = this._ents();
    var status = this._st(e.status);
    var pw = this._num(e.power);
    var sw = this._st(e.sw) === "on";

    var lbl, col, tv, tl, fill;
    if (status === "preheating") {
      lbl = "PreHeat"; col = "#ff6b35"; tv = "08:00"; tl = "Verbleibend"; fill = 1;
    } else if (status === "ready") {
      lbl = "Session"; col = "#4caf50"; tv = "50:00"; tl = "Session"; fill = 1;
    } else if (status === "cooldown") {
      lbl = "Abkühlen"; col = "#78909c"; tv = "--:--"; tl = ""; fill = 0;
    } else {
      lbl = "Aus"; col = "#555"; tv = "--:--"; tl = ""; fill = 0;
    }

    var C = 339.292;

    this.innerHTML = '<ha-card><style>'
    + '.xc{padding:20px;text-align:center}'
    + '.xh{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}'
    + '.xn{font-size:18px;font-weight:600;color:var(--primary-text-color,#e0e0e0);display:flex;align-items:center;gap:8px}'
    + '.xp{font-size:13px;color:var(--secondary-text-color,#888);background:rgba(255,255,255,.06);padding:4px 10px;border-radius:12px}'
    + '.xw{position:relative;width:160px;height:160px;margin:0 auto 16px}'
    + '.xw svg{transform:rotate(-90deg);width:160px;height:160px}'
    + '.xm{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center}'
    + '.xt{font-size:32px;font-weight:700;font-variant-numeric:tabular-nums;color:var(--primary-text-color,#e0e0e0);letter-spacing:1px}'
    + '.xl{font-size:11px;color:var(--secondary-text-color,#888);text-transform:uppercase;letter-spacing:1px;margin-top:2px}'
    + '.xs{font-size:14px;font-weight:600;text-transform:uppercase;letter-spacing:2px;margin-bottom:16px}'
    + '.xb{display:flex;align-items:center;justify-content:center;gap:12px;padding:12px;background:rgba(255,255,255,.04);border-radius:12px;cursor:pointer}'
    + '.xb:active{background:rgba(255,255,255,.08)}'
    + '.xbl{font-size:14px;color:var(--primary-text-color,#e0e0e0)}'
    + '.xd{width:12px;height:12px;border-radius:50%}'
    + '</style><div class="xc">'
    + '<div class="xh"><div class="xn"><ha-icon id="i" icon="mdi:hookah" style="color:' + col + '"></ha-icon>XKah Lite</div>'
    + '<div class="xp" id="p">' + pw.toFixed(0) + ' W</div></div>'
    + '<div class="xw"><svg viewBox="0 0 120 120">'
    + '<circle fill="none" stroke="rgba(255,255,255,.08)" stroke-width="8" cx="60" cy="60" r="54"/>'
    + '<circle id="r" fill="none" stroke="' + col + '" stroke-width="8" stroke-linecap="round"'
    + ' stroke-dasharray="' + C + '" stroke-dashoffset="' + (C * (1 - fill)).toFixed(1) + '" cx="60" cy="60" r="54"/>'
    + '</svg><div class="xm"><div class="xt" id="t">' + tv + '</div>'
    + (tl ? '<div class="xl">' + tl + '</div>' : '')
    + '</div></div>'
    + '<div class="xs" id="s" style="color:' + col + '">' + lbl + '</div>'
    + '<div class="xb" id="b"><div id="dot" class="xd" style="background:' + (sw ? "#4caf50" : "#555") + ';box-shadow:' + (sw ? "0 0 8px rgba(76,175,80,.5)" : "none") + '"></div>'
    + '<div id="slbl" class="xbl">Steckdose ' + (sw ? "Ein" : "Aus") + '</div></div>'
    + '</div></ha-card>';

    this.querySelector("#b").addEventListener("click", () => this._toggle());
    this._built = true;
  }
}

if (!customElements.get("xkah-card")) {
  customElements.define("xkah-card", XKahCard);
}
window.customCards = window.customCards || [];
window.customCards.push({ type: "xkah-card", name: "XKah Lite - Pilot", description: "Dashboard Card", preview: true });
console.info("%c XKAH v2.6 ", "background:#ff6b35;color:#fff;font-weight:bold");
