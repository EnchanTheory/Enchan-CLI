import time
import sys
from pathlib import Path

# Add the parent directories to the Python search path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.ui.stream_renderer import RichStreamRenderer
from backend.ui.theme import get_enchan_progress

def run_test():
    print("=== RichStreamRenderer Streaming Test ===")
    print("Verifying multi-platform compatibility (Windows, macOS, Linux)...")
    time.sleep(1)

    renderer = RichStreamRenderer(title="Enchan Prototyping Tester")
    renderer.start()

    # 1. Thinking Process Phase
    thinking_tokens = [
        "Analyzing...", " First, let's review the novel setup and character sheets.", 
        "\n- Character 'Lethe' is a librarian of the Tower of Time, tasked with historical attunement.",
        "\n- According to Chapter 2's outline, this scene is 'The Calm Before the Storm'.",
        "\nDesigning an engaging magical trigger logic for the next plot progression...",
        "\nFormulating structured Markdown output now."
    ]
    for token in thinking_tokens:
        renderer.update_thinking(token)
        time.sleep(0.3)

    # 2. Transition delay
    time.sleep(0.5)

    # 3. Main Content (Markdown) Streaming Phase
    content_tokens = [
        "# Chapter 2: The Boundary between Silence and Storm\n\n",
        "At the peak of the Tower of Time, Lethe gently brushed their fingers against the ancient parchment.\n",
        "Outside the tall window, the burning crimson twilight was slowly being swallowed by the jaws of night.\n\n",
        "### 🔮 Active Mana Trigger Circuits\n\n",
        "Currently, the magic-induction circuits linked to the tower show the following telemetry:\n\n",
        "| Circuit Name | Mana Ratio | Status | Danger Level |\n",
        "| :--- | :---: | :---: | :---: |\n",
        "| Gears of Chronos | 85% | Stable | Low |\n",
        "| Void Gate | 120% | Active | [bold red]CRITICAL[/] |\n",
        "| Astral Chain | 45% | Dormant | None |\n\n",
        "> \"The wind feels colder than usual tonight...\"\n",
        "> Lethe whispered to the empty room. The storm was already upon them.\n\n",
        "### 💻 Automated Overload Detection Script\n\n",
        "```python\n",
        "# Auto-detect Void Gate overload and trigger historical attunement\n",
        "def check_gate_overload(mana_ratio: float) -> bool:\n",
        "    if mana_ratio >= 1.0:\n",
        "        # Raise emergency alert when threshold is exceeded\n",
        "        return True\n",
        "    return False\n",
        "\n",
        "print('Overload alert active:', check_gate_overload(1.2)) # True\n",
        "```\n\n",
        "Once the mana ratio exceeds 100% (`1.0`), the system triggers an emergency attunement.\n",
        "This serves as the catalyst for the rising action of the impending storm."
    ]

    for token in content_tokens:
        renderer.update_content(token)
        time.sleep(0.15)

    # 4. Finalize Render
    renderer.finish()
    print("\n=== Test Completed ===")
    print("Please verify that the layout and the Markdown tables/code blocks are rendered beautifully.")
    
    # 5. Minimalist Progress Bar Demonstration
    print("\n=== Minimalist Progress Bar Demonstration ===")
    time.sleep(0.5)
    with get_enchan_progress("Downloading Enchan Update") as progress:
        task = progress.add_task("Downloading", total=100)
        while not progress.finished:
            # Advance progress smoothly
            progress.update(task, advance=5)
            time.sleep(0.08)
    print("Download completed successfully!")

if __name__ == "__main__":
    run_test()
