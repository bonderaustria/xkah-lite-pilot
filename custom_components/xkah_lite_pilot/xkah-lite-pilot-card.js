const CARD_VERSION = "1.0.0";

class XKahLitePilotCard extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this._config) return;
    this._render();
  }

  setConfig(config) {
    if (!config.entity) throw new Error("entity (status sensor) required");
    this._config = config;
  }

  static getStubConfig() {
    return { entity: "" };
  }

  getCardSize() {
    return 4;
  }

  _findEntities() {
    const base = this._config.entity.replace("_status", "");
    return {
      status: this._config.entity,
      progress: `${base}_progress`,
      remaining: `${base}_remaining`,
      session_remaining: `${base}_session_remaining`,
      power: `${base}_current_power`,
      switch_entity: `${base}_steckdose`,
    };
  }

  _getState(entityId) {
    const s = this._hass.states[entityId];
    return s ? s.state : "unavailable";
  }

  _getNumeric(entityId) {
    const val = parseFloat(this._getState(entityId));
    return isNaN(val) ? 0 : val;
  }

  _formatTime(totalSeconds) {
    const m = Math.floor(totalSeconds / 60);
    const s = totalSeconds % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  _toggleSwitch() {
    const e = this._findEntities();
    const state = this._getState(e.switch_entity);
    this._hass.callService("switch", state === "on" ? "turn_off" : "turn_on", {
      entity_id: e.switch_entity,
    });
  }

  _render() {
    const e = this._findEntities();
    const status = this._getState(e.status);
    const progress = this._getNumeric(e.progress);
    const remaining = this._getNumeric(e.remaining);
    const sessionRemaining = this._getNumeric(e.session_remaining);
    const power = this._getNumeric(e.power);
    const switchState = this._getState(e.switch_entity);

    const isOff = status === "off";
    const isPreheating = status === "preheating";
    const isReady = status === "ready";
    const isCooldown = status === "cooldown";

    let statusText, statusColor, timerValue, timerLabel, ringProgress;

    if (isPreheating) {
      statusText = "PreHeat";
      statusColor = "#ff6b35";
      timerValue = this._formatTime(remaining);
      timerLabel = "Verbleibend";
      ringProgress = progress;
    } else if (isReady) {
      statusText = "Session";
      statusColor = "#4caf50";
      timerValue = this._formatTime(sessionRemaining);
      timerLabel = "Session";
      ringProgress = sessionRemaining > 0 ? ((3000 - sessionRemaining) / 3000) * 100 : 100;
    } else if (isCooldown) {
      statusText = "Abkühlen";
      statusColor = "#78909c";
      timerValue = "--:--";
      timerLabel = "";
      ringProgress = 100;
    } else {
      statusText = "Aus";
      statusColor = "#555";
      timerValue = "--:--";
      timerLabel = "";
      ringProgress = 0;
    }

    const circumference = 2 * Math.PI * 54;
    const offset = circumference - (ringProgress / 100) * circumference;

    this.innerHTML = `
      <ha-card>
        <style>
          :host {
            --xkah-bg: var(--card-background-color, #1c1c1e);
            --xkah-text: var(--primary-text-color, #e0e0e0);
            --xkah-muted: var(--secondary-text-color, #888);
          }
          .xkah-card {
            padding: 20px;
            text-align: center;
          }
          .xkah-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
          }
          .xkah-title {
            font-size: 18px;
            font-weight: 600;
            color: var(--xkah-text);
            display: flex;
            align-items: center;
            gap: 8px;
          }
          .xkah-title ha-icon {
            color: ${statusColor};
          }
          .xkah-power-badge {
            font-size: 13px;
            color: var(--xkah-muted);
            background: rgba(255,255,255,0.06);
            padding: 4px 10px;
            border-radius: 12px;
          }
          .xkah-ring-container {
            position: relative;
            width: 140px;
            height: 140px;
            margin: 0 auto 16px;
          }
          .xkah-ring-container svg {
            transform: rotate(-90deg);
            width: 140px;
            height: 140px;
          }
          .ring-bg {
            fill: none;
            stroke: rgba(255,255,255,0.08);
            stroke-width: 8;
          }
          .ring-fg {
            fill: none;
            stroke: ${statusColor};
            stroke-width: 8;
            stroke-linecap: round;
            stroke-dasharray: ${circumference};
            stroke-dashoffset: ${offset};
            transition: stroke-dashoffset 1s ease;
          }
          .xkah-ring-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
          }
          .xkah-timer {
            font-size: 28px;
            font-weight: 700;
            font-variant-numeric: tabular-nums;
            color: var(--xkah-text);
            letter-spacing: 1px;
          }
          .xkah-timer-label {
            font-size: 11px;
            color: var(--xkah-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 2px;
          }
          .xkah-status {
            font-size: 14px;
            font-weight: 600;
            color: ${statusColor};
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 16px;
          }
          .xkah-switch-row {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            padding: 12px;
            background: rgba(255,255,255,0.04);
            border-radius: 12px;
            cursor: pointer;
          }
          .xkah-switch-row:active {
            background: rgba(255,255,255,0.08);
          }
          .xkah-switch-label {
            font-size: 14px;
            color: var(--xkah-text);
          }
          .xkah-switch-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: ${switchState === "on" ? "#4caf50" : "#555"};
            box-shadow: ${switchState === "on" ? "0 0 8px rgba(76,175,80,0.5)" : "none"};
          }
        </style>
        <div class="xkah-card">
          <div class="xkah-header">
            <div class="xkah-title">
              <ha-icon icon="mdi:hookah"></ha-icon>
              XKah Lite
            </div>
            <div class="xkah-power-badge">${power.toFixed(0)} W</div>
          </div>

          <div class="xkah-ring-container">
            <svg viewBox="0 0 120 120">
              <circle class="ring-bg" cx="60" cy="60" r="54"/>
              <circle class="ring-fg" cx="60" cy="60" r="54"/>
            </svg>
            <div class="xkah-ring-text">
              <div class="xkah-timer">${timerValue}</div>
              ${timerLabel ? `<div class="xkah-timer-label">${timerLabel}</div>` : ""}
            </div>
          </div>

          <div class="xkah-status">${statusText}</div>

          <div class="xkah-switch-row" id="xkah-toggle">
            <div class="xkah-switch-dot"></div>
            <div class="xkah-switch-label">Steckdose ${switchState === "on" ? "Ein" : "Aus"}</div>
          </div>
        </div>
      </ha-card>
    `;

    this.querySelector("#xkah-toggle").addEventListener("click", () =>
      this._toggleSwitch()
    );
  }
}

customElements.define("xkah-lite-pilot-card", XKahLitePilotCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "xkah-lite-pilot-card",
  name: "XKah Lite - Pilot",
  description: "Dashboard Card für den XKah Lite",
  preview: true,
});

console.info(`%c XKAH-LITE-PILOT-CARD v${CARD_VERSION} `, "background:#ff6b35;color:#fff;font-weight:bold;");
