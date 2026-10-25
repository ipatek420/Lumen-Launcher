# Home Assistant row: setup

Lumen can show a row of tiles that run Home Assistant automations: toggle lights, run a scene or a script, anything an automation can do. No long-lived access token is needed. Tiles trigger **webhook automations**, and the tile list is a JSON file served from Home Assistant's `www` folder.

![Home Assistant row](screenshots/home-assistant-row.jpg)

## Requirements

- Lumen 2.4 or newer on a rooted LG webOS TV with the Homebrew Channel. Lumen sends the requests through the Homebrew Channel's root service, so the TV browser's cross-origin rules don't get in the way.
- Home Assistant reachable from the TV on your local network.
- The **File Editor** add-on, or any other way to edit files in your Home Assistant config folder.

## How it works

1. Lumen reads `http://<HA_IP>:8123/local/lumen.json`. Files in Home Assistant's `www` folder are served at `/local/` without logging in.
2. Pressing a tile sends `POST http://<HA_IP>:8123/api/webhook/<WEBHOOK_ID>`, which triggers the automation with that webhook ID.

## Step 1: one webhook automation per tile

Settings → Automations & Scenes → Create Automation → Create new automation → ⋮ → Edit in YAML. Paste, adjust, Save.

```yaml
alias: Lumen - Living room lamp
mode: single
triggers:
  - trigger: webhook
    webhook_id: lumen-lamp-CHANGE-ME-TO-SOMETHING-RANDOM
    allowed_methods: [POST]
    local_only: true
actions:
  - action: light.toggle
    target:
      entity_id: light.living_room_lamp
```

**Each automation needs its own webhook ID, and it should be hard to guess,** because it works like a password. If you add the trigger in the visual editor (Add trigger → Webhook), Home Assistant generates a random ID for you. Otherwise use something like `openssl rand -hex 12`. Only letters, numbers, `-` and `_` are allowed.

More action examples:

```yaml
# Run a scene
actions:
  - action: scene.turn_on
    target:
      entity_id: scene.movie_time
```

```yaml
# Run a script
actions:
  - action: script.turn_on
    target:
      entity_id: script.goodnight
```

```yaml
# Toggle several lights together
actions:
  - action: light.toggle
    target:
      entity_id:
        - light.lamp
        - light.ceiling
```

## Step 2: the tile list (`www/lumen.json`)

1. In File Editor, go to your config folder (where `configuration.yaml` is).
2. Create a folder named `www` if it doesn't exist.
3. Inside it, create `lumen.json`:

```json
{
  "title": "Home",
  "tiles": [
    { "name": "Lamp",       "icon": "lamp",  "webhook": "lumen-lamp-CHANGE-ME-TO-SOMETHING-RANDOM" },
    { "name": "Movie time", "icon": "movie", "webhook": "lumen-movie-ANOTHER-RANDOM-ID" },
    { "name": "Goodnight",  "icon": "moon",  "webhook": "lumen-night-YET-ANOTHER-ID",
      "description": "Turns everything off downstairs." }
  ]
}
```

| Field | Required | Meaning |
|---|---|---|
| `title` | no | Row name in Lumen (default "Home") |
| `tiles[].name` | yes | Text on the tile (max 40 characters) |
| `tiles[].webhook` | yes | Must match the automation's `webhook_id` exactly |
| `tiles[].icon` | no | `light`, `lamp`, `fan`, `movie`, `music`, `moon`, `sun`, `power`, `thermostat`, `blinds`, `speaker`, `plug`, `scene` (default) |
| `tiles[].description` | no | Line shown under the title at the top of Lumen |

Up to 30 tiles. Tiles with a missing name or an invalid webhook ID are skipped.

4. **If you just created the `www` folder, restart Home Assistant** (Settings → System → Restart). It only starts serving `/local/` after a restart. Later edits to `lumen.json` don't need one.
5. Check it: open `http://<HA_IP>:8123/local/lumen.json` in a browser. You should see your JSON.

## Step 3: point Lumen at Home Assistant

On the TV: red button → Lumen settings → **Home Assistant** → **Address** → type your Home Assistant IP (for example `192.168.1.20`; Lumen adds `:8123` itself) → OK.

A row with your tiles appears under Inputs. OK on a tile runs it and shows "Lamp ✓". After editing `lumen.json`, use **Reload tiles** on the same page. Lumen also reloads the list whenever it opens.

Give Home Assistant a fixed IP (a DHCP reservation in your router) so the address doesn't change. Use the IP rather than `homeassistant.local`, which the TV may not resolve.

## Security notes

- `local_only: true` (the default for webhook triggers) means Home Assistant only accepts the webhook from your local network.
- Everything in `www` can be read without logging in by anyone who can reach your Home Assistant, **including over the internet if you expose it remotely** (Nabu Casa, a reverse proxy). That would reveal your webhook IDs; `local_only` still stops them being triggered from outside. Never put tokens or passwords in `www`.
- Use tiles for lights, scenes and media. Don't connect locks, garage doors or alarms to an unauthenticated webhook.

## Troubleshooting

| Lumen shows | Meaning / fix |
|---|---|
| "No www/lumen.json found" | The file is missing or misnamed, or Home Assistant wasn't restarted after creating `www` |
| "lumen.json has a mistake" | Invalid JSON, such as a missing comma or quote. Paste it into a JSON validator |
| "Can't reach Home Assistant" | Wrong IP, Home Assistant is down, or the TV can't reach it |
| "Lamp ✓" but nothing happens | Home Assistant answers OK even for unknown webhook IDs. Check the ID matches exactly in the automation and in `lumen.json`, then look at the automation's trace |

A tile only triggers the action. It can't show whether a light is currently on, because that would need an access token.
