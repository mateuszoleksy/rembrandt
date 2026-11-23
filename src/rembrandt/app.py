import os

from PIL import Image
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static, Switch
from textual.worker import get_current_worker

from rembrandt.render import MODES, TERMINAL_CHAR_ASPECT, parse_size, render_ascii_image, to_ascii

# Baner ASCII w stylu k9s
BANNER = r"""
 ██████╗ ███████╗███╗   ███╗██████╗ ██████╗  █████╗ ███╗   ██╗██████╗ ████████╗
 ██╔══██╗██╔════╝████╗ ████║██╔══██╗██╔══██╗██╔══██╗████╗  ██║██╔══██╗╚══██╔══╝
 ██████╔╝█████╗  ██╔████╔██║██████╔╝██████╔╝███████║██╔██╗ ██║██║  ██║   ██║
 ██╔══██╗██╔══╝  ██║╚██╔╝██║██╔══██╗██╔══██╗██╔══██║██║╚██╗██║██║  ██║   ██║
 ██║  ██║███████╗██║ ╚═╝ ██║██████╔╝██║  ██║██║  ██║██║ ╚████║██████╔╝   ██║
 ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝    ╚═╝
               [ CHIAROSCURO ASCII ENGINE // TERMINAL EDITION by Matteo ]
"""

PREVIEW_DELAY = 0.3  # seconds to wait after the last edit before re-rendering the preview


def art_to_text(art):
    """Build a Rich Text, merging runs of same-colored characters into one span."""
    text = Text(no_wrap=True, overflow="crop")
    for y, (row_chars, row_colors) in enumerate(zip(art.chars, art.colors)):
        if y:
            text.append("\n")
        run_start = 0
        for x in range(1, len(row_chars) + 1):
            if x == len(row_chars) or row_colors[x] != row_colors[run_start]:
                r, g, b = row_colors[run_start]
                text.append(row_chars[run_start:x], style=f"#{r:02x}{g:02x}{b:02x}")
                run_start = x
    return text


class Preview(Static):
    def on_resize(self) -> None:
        self.app.schedule_preview()


class RembrandtApp(App):
    TITLE = "rembrandt"

    CSS = """
    Screen {
        background: #0b0e14;
        color: #00ffcc;
    }
    #banner-box {
        align: center top;
        height: auto;
        padding: 1 0;
        border-bottom: heavy #333c4d;
    }
    /* Center the banner as one block; centering each line separately would skew lines of different lengths */
    #banner {
        width: auto;
        color: #ff9900;
    }
    #body {
        height: 1fr;
    }
    #main-box {
        padding: 1 2;
        width: 64;
        height: 1fr;
        scrollbar-size-vertical: 1;
    }
    .row {
        height: 3;
        align: left middle;
    }
    Label {
        width: 26;
        height: 3;
        content-align: left middle;
        color: #8899aa;
    }
    /* Select draws its box on the inner SelectCurrent, so style that rather than Select itself */
    Input, Select > SelectCurrent, Switch {
        background: #0b0e14;
        border: round #333c4d;
        color: #ffffff;
    }
    Select {
        background: #0b0e14;
    }
    Input, Select {
        width: 33;
    }
    Input:focus, Select:focus > SelectCurrent, Switch:focus {
        border: round #ff9900;
        background-tint: transparent;
    }
    Input:disabled {
        color: #4a5566;
        border: round #1f2633;
    }
    #btn-generate {
        margin-top: 1;
        width: 59;
        background: #ff9900;
        color: #000000;
        text-style: bold;
    }
    #status {
        margin-top: 1;
        padding: 1;
        border: round #333c4d;
        color: #00ffcc;
        width: 59;
    }
    #preview {
        width: 1fr;
        height: 1fr;
        margin: 1 2 1 0;
        border: round #333c4d;
        border-title-color: #ff9900;
        background: #000000;
        content-align: center middle;
        color: #8899aa;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+g", "generate", "Generate Art"),
    ]

    _preview_timer = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="banner-box"):
            yield Static(BANNER, id="banner")
        with Horizontal(id="body"):
            with VerticalScroll(id="main-box"):
                with Horizontal(classes="row"):
                    yield Label("Input Image Path:")
                    yield Input(value="image.jpg", id="input_path")
                with Horizontal(classes="row"):
                    yield Label("Output PNG Path:")
                    yield Input(value="rembrandt_out.png", id="output_path")
                with Horizontal(classes="row"):
                    yield Label("Width (chars):")
                    yield Input(value="160", id="width")
                with Horizontal(classes="row"):
                    yield Label("Color Mode:")
                    yield Select(
                        [(label, key) for key, (label, _) in MODES.items()],
                        value="color",
                        allow_blank=False,
                        id="mode",
                    )
                with Horizontal(classes="row"):
                    yield Label("Shadow Boost (0-100):")
                    yield Input(value="35", id="boost")
                with Horizontal(classes="row"):
                    yield Label("Output Scale (e.g. 1.0):")
                    yield Input(value="1.0", id="scale")
                with Horizontal(classes="row"):
                    yield Label("Output Size (WxH px):")
                    yield Input(placeholder="auto, e.g. 1200x1900", id="size")
                with Horizontal(classes="row"):
                    yield Label("Side-by-Side Original:")
                    yield Switch(value=False, id="side_by_side")

                yield Button("RENDER ASCII [Ctrl+G]", id="btn-generate")
                yield Static("Ready. Enter parameters and press Render.", id="status")
            yield Preview(id="preview")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#preview", Preview).border_title = "Preview"

    # --- live preview ---

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "size":
            # An exact size overrides width and scale
            for field in ("#width", "#scale"):
                self.query_one(field, Input).disabled = bool(event.value.strip())
        if event.input.id in ("input_path", "boost", "size"):
            self.schedule_preview()

    def on_select_changed(self, event: Select.Changed) -> None:
        self.schedule_preview()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if self.query_one("#size", Input).value.strip():
            self.schedule_preview()  # with an exact size, side-by-side changes the ASCII half's proportions

    def _read_size(self):
        """Exact output size from the form, or None for automatic."""
        text = self.query_one("#size", Input).value
        return parse_size(text) if text.strip() else None

    def schedule_preview(self) -> None:
        """Debounce preview renders so typing a path doesn't trigger one per keystroke."""
        if self._preview_timer is not None:
            self._preview_timer.stop()
        self._preview_timer = self.set_timer(PREVIEW_DELAY, self.refresh_preview)

    def refresh_preview(self) -> None:
        preview = self.query_one("#preview", Preview)
        path = self.query_one("#input_path", Input).value
        if not os.path.isfile(path):
            preview.update(Text(f"No image at '{path}'"))
            return
        try:
            boost = int(self.query_one("#boost", Input).value)
        except ValueError:
            preview.update("Shadow boost must be a whole number")
            return
        try:
            out_size = self._read_size()
        except ValueError as e:
            preview.update(Text(str(e)))
            return
        if out_size and self.query_one("#side_by_side", Switch).value:
            out_size = (out_size[0] / 2, out_size[1])
        mode = self.query_one("#mode", Select).value
        size = preview.content_size
        if size.width > 0 and size.height > 0:
            self.render_preview(path, size.width, size.height, mode, boost, out_size)

    @work(thread=True, exclusive=True, group="preview")
    def render_preview(self, path, max_width, max_height, mode, boost, out_size) -> None:
        preview = self.query_one("#preview", Preview)
        try:
            image = Image.open(path)
            # Show the proportions the PNG will have: the exact size if set, else the image's own
            w, h = out_size or image.size
            ratio = h / w * TERMINAL_CHAR_ASPECT
            # Largest width whose resulting height still fits the panel
            width = max(1, min(max_width, int(max_height / ratio)))
            height = max(1, int(width * ratio))
            text = art_to_text(to_ascii(image, width, mode, boost, height=height))
        except Exception as e:
            text = Text(f"Can't preview: {e}")
        if not get_current_worker().is_cancelled:
            self.call_from_thread(preview.update, text)

    # --- PNG rendering ---

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-generate":
            self.action_generate()

    def action_generate(self) -> None:
        status = self.query_one("#status", Static)
        in_path = self.query_one("#input_path", Input).value
        out_path = self.query_one("#output_path", Input).value

        if not os.path.exists(in_path):
            status.update(f"[bold red]ERROR:[/] File '{in_path}' not found!")
            return

        try:
            size = self._read_size()
            boost = int(self.query_one("#boost", Input).value)
            # Width and scale are ignored (and disabled) when an exact size is given
            width = 160 if size else int(self.query_one("#width", Input).value)
            scale = 1.0 if size else float(self.query_one("#scale", Input).value)
        except ValueError as e:
            status.update(f"[bold red]ERROR:[/] {e}")
            return
        mode = self.query_one("#mode", Select).value
        sbs = self.query_one("#side_by_side", Switch).value

        status.update("[yellow]Rendering masterpiece...[/]")
        self.render_png(in_path, out_path, width, mode, boost, sbs, scale, size)

    @work(thread=True, exclusive=True, group="render")
    def render_png(self, in_path, out_path, width, mode, boost, sbs, scale, size) -> None:
        status = self.query_one("#status", Static)
        try:
            res_size = render_ascii_image(in_path, out_path, width, mode, boost, sbs, scale, size)
        except Exception as e:
            self.call_from_thread(status.update, f"[bold red]ERROR:[/] {e}")
            self.call_from_thread(self.notify, str(e), title="Render failed", severity="error", markup=False)
            return
        self.call_from_thread(status.update, f"[bold green]SUCCESS![/] Saved [white]{out_path}[/] ({res_size})")
        self.call_from_thread(
            self.notify, f"{os.path.abspath(out_path)}\n{res_size}", title="ASCII art saved", markup=False, timeout=6
        )
