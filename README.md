# garrison-plugin-rust

Rust dedicated server WebRCON plugin for [Garrison](https://github.com/ProfessorZ/garrison).

## Protocol

Rust uses **WebSocket RCON** (not Source RCON):

- Connect: `ws://host:rconport/<password>`
- Send: `{"Identifier": <int>, "Message": "<command>", "Name": "Garrison"}`
- Receive: `{"Identifier": <int>, "Message": "<response>", "Type": "Generic"}`

## Configuration

| Field | Default | Description |
|-------|---------|-------------|
| `host` | — | Server hostname/IP |
| `rcon_port` | `28016` | RCON WebSocket port |
| `rcon_password` | — | RCON password |

> On the Profszone Rust01 instance the RCON port is **5678**.

## Commands used

| Action | Command |
|--------|---------|
| Player list | `playerlist` (returns JSON array) |
| Status | `status` |
| Kick | `kick <steamid> "<reason>"` |
| Ban | `banid <steamid> "" "<reason>"` |
| Unban | `unban <steamid>` |
| Say | `say "<message>"` |

## Player fields (from `playerlist`)

- `SteamID` → `player_id`
- `DisplayName` / `Username` → `name`
- `Ping` → `ping`
- `Health`, `ConnectedSeconds`, `VoiP` → `extra`

## Dependencies

```
websockets>=12.0
```
