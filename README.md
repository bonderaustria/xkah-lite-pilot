# XKah Lite - Pilot

Custom Home Assistant Integration für den **XKah Lite** E-Shisha-Heater. Macht deinen XKah smart — ganz ohne WiFi oder Bluetooth am Gerät selbst.

Die Integration nutzt eine smarte Steckdose mit Leistungsmessung (z.B. IKEA INSPELNING via Zigbee2MQTT), um anhand des Stromverbrauchs automatisch zu erkennen, in welcher Phase sich der XKah gerade befindet.

---

## Features

- **Automatische Phasenerkennung** über Stromverbrauch (kein Eingriff am Gerät nötig)
- **PreHeat-Timer** — 8 Minuten Countdown mit Benachrichtigung wenn fertig
- **Session-Timer** — 50 Minuten Countdown nach dem PreHeat
- **Dashboard Card** — Ring-Timer mit Farbverlauf, Leistungsanzeige, Steckdosen-Toggle
- **Lernfähig** — merkt sich PreHeat-Zeiten und passt sich an
- **Benachrichtigungen** — frei wählbar pro XKah-Instanz (z.B. Push aufs Handy)

---

## Voraussetzungen

- Home Assistant 2024.1+
- Smarte Steckdose mit **Leistungsmessung (Watt)** — z.B.:
  - IKEA INSPELNING (Zigbee)
  - Shelly Plug S
  - Jede Steckdose mit `sensor.*_power` Entity
- [HACS](https://hacs.xyz/) (empfohlen) oder manuelle Installation

---

## Installation

### Über HACS (empfohlen)

1. HACS öffnen → **Integrationen** → **⋮** (oben rechts) → **Benutzerdefinierte Repositories**
2. URL eingeben: `https://github.com/bonderaustria/xkah-lite-pilot`
3. Kategorie: **Integration**
4. **Herunterladen** und Home Assistant **neustarten**

### Manuell

1. Den Ordner `custom_components/xkah_lite_pilot` in dein HA-Konfigurationsverzeichnis kopieren
2. Home Assistant neustarten

---

## Einrichtung

1. **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen**
2. Nach **"XKah Lite - Pilot"** suchen
3. **Steckdose auswählen** — der Leistungssensor wird automatisch erkannt
4. **Benachrichtigung konfigurieren** — Dienst aus der Dropdown-Liste wählen (z.B. `notify.mobile_app_iphone`)
5. Fertig — die Integration erstellt alle Sensoren und die Dashboard Card wird automatisch als Lovelace-Resource registriert

---

## Dashboard Card

Die Card wird automatisch als Resource registriert. Zum Hinzufügen:

1. Dashboard bearbeiten → **Karte hinzufügen** → **Manuell (YAML)**
2. Folgendes einfügen:

```yaml
type: custom:xkah-lite-pilot-card
entity: sensor.xkah_lite_status
```

> Den Entity-Namen findest du unter **Einstellungen → Geräte & Dienste → XKah Lite - Pilot → Entitäten** (die Status-Entity verwenden).

### Card Features

| Feature | Beschreibung |
|---|---|
| **Ring-Timer** | Startet voll, leert sich über die Zeit |
| **Farbverlauf** | Grün (>50%) → Gelb (50-30%) → Rot (≤30%) |
| **PreHeat** | Orange Ring, 8 Min Countdown |
| **Leistung** | Aktuelle Wattzahl oben rechts |
| **Steckdose** | Ein/Aus Toggle unten |

---

## Funktionsweise

Der XKah Lite durchläuft vier Phasen, die über den Stromverbrauch erkannt werden:

```
OFF → PREHEATING → READY (Session) → COOLDOWN → OFF
```

| Phase | Erkennung | Dauer |
|---|---|---|
| **OFF** | < 3 W | — |
| **PreHeating** | > 15 W für 10 Sekunden | 8 Minuten (Standard) |
| **Ready / Session** | Nach PreHeat-Ablauf | 50 Minuten Countdown |
| **Cooldown** | < 3 W | Nach 2 Min unter 3 W → OFF |

**Wichtig:** Solange der XKah läuft (auch wenn die Leistung schwankt), bleibt die Session aktiv. Erst wenn der Verbrauch 2 Minuten durchgehend unter 3 W liegt, wird der Cooldown abgeschlossen.

### Typischer Stromverbrauch

| Zustand | Leistung |
|---|---|
| Aus / Standby | 0–1 W |
| PreHeat | 20–30 W |
| Betrieb (285°C) | ~13 W |

---

## Entities

Die Integration erstellt folgende Entities (Beispiel-Prefix: `xkah_lite`):

| Entity | Typ | Beschreibung |
|---|---|---|
| `sensor.*_status` | Sensor | Aktuelle Phase (off/preheating/ready/cooldown) |
| `sensor.*_fortschritt` | Sensor | PreHeat-Fortschritt in % |
| `sensor.*_verbleibend` | Sensor | PreHeat verbleibend in Sekunden |
| `sensor.*_session_verbleibend` | Sensor | Session verbleibend in Sekunden |
| `sensor.*_aktuelle_leistung` | Sensor | Momentane Leistung in W |
| `sensor.*_gelernte_dauer` | Sensor | Gelernte PreHeat-Dauer |
| `sensor.*_session_anzahl` | Sensor | Anzahl aufgezeichneter Sessions |
| `binary_sensor.*_aktiv` | Binary Sensor | Ob der XKah gerade läuft |
| `switch.*_steckdose` | Switch | Steckdose ein/aus |
| `button.*_preheat_fertig` | Button | PreHeat manuell abschließen |

---

## Konfiguration

Die Benachrichtigungseinstellungen können jederzeit über die Integrationsoptionen angepasst werden:

**Einstellungen** → **Geräte & Dienste** → **XKah Lite - Pilot** → **Konfigurieren**

| Option | Standard | Beschreibung |
|---|---|---|
| Benachrichtigungsdienst | — | z.B. `notify.mobile_app_iphone` |
| Titel | XKah Lite | Titel der Push-Nachricht |
| Nachricht | XKah Lite - PreHeat abgeschlossen! | Nachrichtentext |

---

## Mehrere XKah

Du kannst die Integration mehrfach einrichten — einfach erneut hinzufügen und eine andere Steckdose wählen. Jeder XKah hat eigene Sensoren, Timer und Benachrichtigungseinstellungen.

---

## Lizenz

MIT
