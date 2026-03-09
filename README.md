# Nucleares — Home Assistant Integration

A custom Home Assistant integration that connects to the
[Nucleares Bridge](https://github.com/tyler919/nucleares-bridge)
and exposes all reactor sensor data as native HA entities.

---

## How it works

```
Nucleares game (localhost:8080)
        ↓
  nucleares-bridge  (runs on gaming PC, exposes LAN API)
        ↑  HA polls every 5 seconds
  This integration
        ↓
  Sensor entities in Home Assistant
```

The integration never talks to the game directly — it only talks to the bridge.
No credentials for Home Assistant are stored on the gaming PC.

---

## Requirements

- Home Assistant 2024.1 or later
- The [Nucleares Bridge](https://github.com/tyler919/nucleares-bridge)
  running on your gaming PC and reachable from your HA server

---

## Installation

### Option A — HACS (recommended)

1. In HACS, go to **Integrations → Custom Repositories**
2. Add this repo URL with category **Integration**
3. Install **Nucleares**
4. Restart Home Assistant

### Option B — Manual

1. Copy the `custom_components/nucleares/` folder into your HA
   `config/custom_components/` directory
2. Restart Home Assistant

---

## Setup

1. Go to **Settings → Integrations → Add Integration**
2. Search for **Nucleares**
3. Enter:
   - **Bridge URL** — e.g. `http://192.168.1.100:8765`
   - **API Key** — the `HA_API_KEY` value from the bridge `.env` file
4. HA will test the connection. If it succeeds, all sensor entities are created.

---

## What you get

A single device called **Nucleares Reactor** with one entity per polled variable:

| Entity | Description |
|---|---|
| `sensor.nucleares_core_temperature` | Core temperature (°C) |
| `sensor.nucleares_core_pressure` | Core pressure (bar) |
| `sensor.nucleares_core_integrity` | Core integrity (%) |
| `sensor.nucleares_core_wear` | Core wear (%) |
| `sensor.nucleares_core_state` | Core state |
| `sensor.nucleares_imminent_fusion_warning` | Fusion warning flag |
| `sensor.nucleares_rod_position_actual` | Actual rod position (%) |
| `sensor.nucleares_rod_temperature` | Rod temperature (°C) |
| `sensor.nucleares_coolant_vessel_temperature` | Coolant temperature (°C) |
| `sensor.nucleares_generator_1_power` | Generator 1 output (kW) |
| `sensor.nucleares_turbine_1_rpm` | Turbine 1 RPM |
| ... | (all variables in bridge `variables.yaml`) |

All entities show as **unavailable** when:
- The bridge is unreachable (gaming PC is off, script isn't running)
- The game is running but the webserver isn't activated

---

## Automations & Alerts

Once the sensors exist, use them in standard HA automations.

### Overheat notification

```yaml
automation:
  - alias: "Nucleares — Overheat Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.nucleares_core_temperature
        above: 380
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "Reactor Alert"
          message: "Core temp at {{ states('sensor.nucleares_core_temperature') }}°C"
```

### Auto SCRAM (emergency rod insertion)

Add this to `configuration.yaml`:

```yaml
rest_command:
  nucleares_scram:
    url: "http://192.168.1.100:8765/control"
    method: POST
    headers:
      X-API-Key: !secret nucleares_api_key
    payload: '{"variable": "RODS_ALL_POS_ORDERED", "value": 0}'
    content_type: "application/json"

  nucleares_set_rods:
    url: "http://192.168.1.100:8765/control"
    method: POST
    headers:
      X-API-Key: !secret nucleares_api_key
    payload: '{"variable": "RODS_ALL_POS_ORDERED", "value": {{ position }}}'
    content_type: "application/json"
```

Add this to `secrets.yaml`:

```yaml
nucleares_api_key: "your-api-key-here"
```

Then the automation:

```yaml
automation:
  - alias: "Nucleares — Auto SCRAM"
    trigger:
      - platform: numeric_state
        entity_id: sensor.nucleares_core_temperature
        above: 450
    action:
      - service: rest_command.nucleares_scram
      - service: notify.mobile_app_your_phone
        data:
          message: "Auto SCRAM triggered — rods fully inserted."
```

---

## Sensor availability

| Situation | Entity state |
|---|---|
| Game running, webserver on, bridge running | Live values |
| Bridge running but game webserver off | `unavailable` |
| Bridge script not running | `unavailable` |
| Gaming PC off | `unavailable` |

---

## Security notes

- The API key is stored in HA's `secrets.yaml`, not in automation YAML
- The bridge only accepts requests from HA's IP (if configured)
- No HA credentials are ever sent to or stored on the gaming PC
- Do not expose the bridge port to the internet
