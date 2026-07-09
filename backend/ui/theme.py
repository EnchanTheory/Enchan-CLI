from rich.console import Console
from rich.theme import Theme
from rich.progress import Progress, BarColumn, TextColumn, TaskProgressColumn

# ==============================================================================
# 🎨 Enchan CLI Unified Color Palette & Theme Specifications
# ==============================================================================
# Centralized design sheet for the Enchan CLI application.
# All styling, margins, colors, and Rich theme bindings are defined ONLY here
# to prevent visual drift and guarantee seamless maintenance.
# ==============================================================================

# 💎 Unified Color Palette (Amber / Gold / Warm Grays)
DEFAULT_BORDER = "rgb(165,145,100)"  # Classic Enchan Gold Accent
MUTED_BORDER = "rgb(150,150,150)"   # Muted Gray for inactive/system elements
DEFAULT_BODY = "rgb(210,200,200)"     # Soft Beige/Warm Gray for body text
DEFAULT_BG = "rgb(12,10,8)"          # Deepest pitch-black gold backing plate to maximize text selection and legibility contrast

# 🎨 Unified Code Theme Specifications
DEFAULT_CODE_THEME = "zenburn"       # Elegant, low-contrast, eyes-friendly theme

# 🎛️ Shared Console Instance
console = Console()

# ==============================================================================
# 👑 Centralized Enchan Gold Theme for Markdown Rendering
# ==============================================================================
# Pure, elegant, low-color palette optimized for high-end minimalism.
# Fully overrides internal rich.markdown keys to eradicate any default primary hues,
# delivering an ultra-coherent, professional amber-toned terminal output.
# ==============================================================================
ENCHAN_MARKDOWN_THEME = Theme({
    # Body text & Paragraphs (Warm Soft Gray/Beige)
    "markdown.paragraph": DEFAULT_BODY,
    "markdown.text": DEFAULT_BODY,
    
    # Headings (Elegant Gold Gradations with underline for H1)
    "markdown.h1": f"bold {DEFAULT_BORDER} underline",
    "markdown.h2": f"bold {DEFAULT_BORDER}",
    "markdown.h3": f"bold {DEFAULT_BORDER}",
    "markdown.h4": f"bold {DEFAULT_BORDER}",
    "markdown.h5": f"bold {DEFAULT_BORDER}",
    "markdown.h6": f"bold {DEFAULT_BORDER}",
    
    # Lists & Bullets (Eradicates default cyan/blue colors in list numbers and bullets)
    "markdown.list": DEFAULT_BODY,                     # Fixes default cyan on lists
    "markdown.item": DEFAULT_BODY,
    "markdown.item.multiline": DEFAULT_BODY,
    "markdown.item.bullet": f"bold {DEFAULT_BORDER}",  # Fixes default bullets style key
    "markdown.item.number": f"bold {DEFAULT_BORDER}",  # Fixes default cyan 'markdown.item.number' style!
    
    # Links & URLs (Unified Gold with underline to prevent default blue/purple colors)
    "markdown.link": f"underline {DEFAULT_BORDER}",
    "markdown.link_hover": f"bold {DEFAULT_BORDER}",
    "markdown.link_url": f"underline {DEFAULT_BORDER}", # Fixes default blue links
    
    # Tables (Unified Gold to replace default cyan borders and headers)
    "markdown.table.border": DEFAULT_BORDER,
    "markdown.table.header": f"bold {DEFAULT_BORDER}",
    
    # Blockquotes (Muted amber-italic using the identical border variable)
    "markdown.block_quote": f"italic {DEFAULT_BORDER}",
    
    # Inline Code (Styled in Gold text over the centralized dynamic DEFAULT_BG dark plate)
    "markdown.code": f"bold {DEFAULT_BORDER} on {DEFAULT_BG}",
    
    # Code Blocks (Full block with beautiful centralized dynamic DEFAULT_BG backing plate)
    "markdown.code_block": f"{DEFAULT_BODY} on {DEFAULT_BG}",
    
    # Strong & Emphasis (Uses central DEFAULT_BORDER to make bold/italic points stand out in Gold)
    "markdown.strong": f"bold {DEFAULT_BORDER}",
    "markdown.em": f"italic {DEFAULT_BORDER}",
    
    # Horizontal Rules (Identical to default border)
    "markdown.hr": DEFAULT_BORDER,
})


# ==============================================================================
# 📊 Centralized Unified Progress Bar Constructor
# ==============================================================================
# Generates a minimal, ultra-low color progress bar for downloads/updates.
# Uses only gold and gray to maintain a high-end, distraction-free aesthetic.
# ==============================================================================
def get_enchan_progress(description: str = "Processing") -> Progress:
    """
    Returns an ultra-elegant, low-color progress bar matching the Enchan CLI design.
    """
    return Progress(
        TextColumn(f"[bold {DEFAULT_BORDER}]{description}[/]"),
        BarColumn(
            bar_width=35,
            style=MUTED_BORDER,            # Muted gray background track
            complete_style=DEFAULT_BORDER,  # Solid gold completed segments
            finished_style=DEFAULT_BORDER   # Solid gold finished segments
        ),
        TaskProgressColumn(style=f"bold {DEFAULT_BORDER}"),
        console=console,
        transient=False  # Keeps the finalized progress bar in terminal history
    )
