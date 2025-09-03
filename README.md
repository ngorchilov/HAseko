# haseko — Home Assistant Aseko Integration

Read‑only integration for Aseko cloud devices. One HA device per paired unit (serial number), with sensors/binary_sensors only. Generated with ChatGPT 5

## Install (HACS custom repository)

1. In HACS → Integrations → **Custom repositories** → URL: this repo, Category: **Integration**.
2. Install **haseko** and **restart** Home Assistant.
3. Settings → Devices & Services → **Add Integration** → search **Haseko**.
4. Enter your **Aseko Cloud API key**.

> **Where do I get the API key?**  
> Create one at: https://account.aseko.cloud/profile/settings/api-keys

## Features

-   60s polling via DataUpdateCoordinator
-   Probe awareness: Redox _or_ Free Chlorine (never both)
-   Text sensor: which disinfection probe is installed
-   Status messages sensor (latest message text)
-   Read‑only (no writes)

## Entities (per device)

**Sensors (numeric)**: Water temperature (°C), pH, Redox (mV) _or_ Free chlorine (mg/l), their targets, Salinity (kg/m³), Filter flow (m³/h), Filter pressure (bar), Electrolyzer production (g/h), Water level (cm).  
**Sensors (text/enums)**: Mode, Filtration speed, Pool flow, Electrolyzer direction, Water level state, Upcoming filtration period, **Disinfection probe**, **Status (latest)**.  
**Binary sensors**: Online, Filtration running, Water flow to probes, Electrolyzer running, Heating running, Solar running, Water filling running.
