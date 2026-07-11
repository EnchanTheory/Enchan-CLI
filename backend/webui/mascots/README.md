# Enchan Mascot Creation Guide

Enchan WebUI allows you to display, drag, and interact with desktop mascots (compatible with Codex Pets). These mascots change their active animations based on the AI's current state (e.g., thinking, working, greeting).

This directory is the storage path for default, built-in system mascots (such as the bundled `tikta`). Below is a comprehensive guide on how to design, configure, and register your own custom mascots for the Enchan WebUI.

---

## 1. Spritesheet (Contact Sheet) Specifications

Mascot images must follow the **Codex Pets v4 contact-sheet contract** as a single transparent PNG or WebP image.

- **Overall Image Dimensions**: `1536 x 1872` pixels
- **Grid Layout**: `8 columns × 9 rows` (72 frames total)
- **Single Frame Size**: `192 x 208` pixels per frame
- **Transparent Border Rule**: To prevent rendering clips, sprite overflows, and registration errors, **keep at least 6 transparent pixels (completely transparent border padding) inside the outer edges of every 192x208 cell**.
  - Spritesheets failing to meet this margin requirement will be rejected by the WebUI registration validator (`validatePetSheet`).

### 🎨 Animation Rows & System Triggers
Each of the 9 rows (Row 0 to 8) represents a specific animation state. Frame indexes run sequentially from left to right within each row.

| Row Index (0-8) | Animation Name | Trigger Timing / Purpose |
| :--- | :--- | :--- |
| **Row 0** | `idle` | Quiet resting state (when the AI is not generating) |
| **Row 1** | `running-right` | Played when dragging the mascot to the right |
| **Row 2** | `running-left` | Played when dragging the mascot to the left |
| **Row 3** | `waving` | Greeting / Played on successful generation completed |
| **Row 4** | `jumping` | Played when starting a New Chat or upon initial click/grab |
| **Row 5** | `failed` | Played on generation errors or connection failures |
| **Row 6** | `waiting` | Played during normal chat generation (Thinking) |
| **Row 7** | `running` | Played during active Agent Mode/tool executions (Working) |
| **Row 8** | `review` | Played when analyzing logs, documents, or history |

---

## 2. Mascot Configuration Files

A mascot is bundled as a single subdirectory named after its unique alphanumeric ID (lowercase letters, numbers, hyphens, and underscores only). It must contain the following files:

### 📂 Example Directory Layout: `your-mascot-id/`
```text
backend/webui/mascots/your-mascot-id/
├── pet.json            # Manifest configuration file
└── spritesheet.png     # 1536x1872 px transparent PNG/WebP spritesheet
```

### 📄 `pet.json` Schema Reference
```json
{
  "id": "your-mascot-id",
  "displayName": "Mascot Display Name",
  "description": "A brief description of your mascot.",
  "spritesheetPath": "spritesheet.png",
  "frame": {
    "width": 192,
    "height": 208,
    "columns": 8,
    "rows": 9
  },
  "personality": "You are [Name], ... (Character personality system prompt. WebUI appends this text to the end of the conversation system prompt to define the AI's speaking voice, demeanor, tone, and character values.)",
  "animations": {
    "idle": {
      "frames": [0, 1, 2, 3, 4, 5],
      "loop": true
    },
    "running-right": { "row": 1, "count": 8, "frameDuration": 120, "finalDuration": 220, "repeats": 3 },
    "running-left": { "row": 2, "count": 8, "frameDuration": 120, "finalDuration": 220, "repeats": 3 },
    "waving": { "row": 3, "count": 4, "frameDuration": 140, "finalDuration": 280, "repeats": 3 },
    "jumping": { "row": 4, "count": 5, "frameDuration": 140, "finalDuration": 280, "repeats": 3 },
    "failed": { "row": 5, "count": 8, "frameDuration": 140, "finalDuration": 240, "repeats": 3 },
    "waiting": { "row": 6, "count": 6, "frameDuration": 150, "finalDuration": 260, "repeats": 3 },
    "running": { "row": 7, "count": 6, "frameDuration": 120, "finalDuration": 220, "repeats": 3 },
    "review": { "row": 8, "count": 6, "frameDuration": 150, "finalDuration": 280, "repeats": 3 }
  }
}
```

---

## 3. Installation & Registration

There are two ways to load custom mascots into Enchan WebUI.

### Method A: Upload via the WebUI Settings (Recommended for Users)
1. Open the Enchan WebUI in your browser.
2. Click the **⚙️ (Mascot settings)** icon in the header navigation bar.
3. Click the **"＋ Add mascot"** button at the bottom left of the settings grid.
4. Fill out the form (ID, Name, Description, Personality Prompt).
5. Choose and upload your local `spritesheet.png` contact sheet. A live interactive animation preview will automatically load if the sheet is valid.
6. Click **"Save and select"** to finalize registration.
- 💡 **Note**: Mascots created through this GUI are saved locally inside `data/mascots/` (which is git-ignored). This is the best approach for private, personal, or testing mascots.

### Method B: Direct Folder Placement (For Repository Built-ins / Developers)
1. Create a new folder under this directory (`backend/webui/mascots/`) matching your mascot ID (e.g., `my-cool-mascot/`).
2. Save your validated `pet.json` and `spritesheet.png` inside that folder.
- 💡 **Note**: Mascots saved here are bundled directly inside the Enchan CLI repository and will be tracked by Git. Use this method if you plan to share the mascot built-in with the community as a pull request.
