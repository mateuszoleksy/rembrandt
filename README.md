```
 ██████╗ ███████╗███╗   ███╗██████╗ ██████╗  █████╗ ███╗   ██╗██████╗ ████████╗
 ██╔══██╗██╔════╝████╗ ████║██╔══██╗██╔══██╗██╔══██╗████╗  ██║██╔══██╗╚══██╔══╝
 ██████╔╝█████╗  ██╔████╔██║██████╔╝██████╔╝███████║██╔██╗ ██║██║  ██║   ██║
 ██╔══██╗██╔══╝  ██║╚██╔╝██║██╔══██╗██╔══██╗██╔══██║██║╚██╗██║██║  ██║   ██║
 ██║  ██║███████╗██║ ╚═╝ ██║██████╔╝██║  ██║██║  ██║██║ ╚████║██████╔╝   ██║
 ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝    ╚═╝
               [ CHIAROSCURO ASCII ENGINE // TERMINAL EDITION by Matteo ]
```

Modern tool for generating ASCII art, a terminal UI (built with [Textual](https://textual.textualize.io/)) that turns any image into a colored ASCII-art PNG, with a live preview right in your terminal. Also works as a plain command-line tool for scripts and batch jobs.

# Demo
<img width="1710" height="918" alt="image" src="https://github.com/user-attachments/assets/3f78a51e-5425-46cf-aa62-5ebf4e9d0f2c" />


## Quick start

You only need [uv](https://docs.astral.sh/uv/) installed:

```sh
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# or: brew install uv
```

### Run without cloning (one command)

```sh
uvx --from git+https://github.com/mateuszoleksy/rembrandt rembrandt
```

uv downloads Python and the dependencies automatically, then opens the app.

### Install as a global command

```sh
uv tool install git+https://github.com/mateuszoleksy/rembrandt
rembrandt
```

Update later with `uv tool upgrade rembrandt`.

### Run from a local clone

```sh
git clone https://github.com/mateuszoleksy/rembrandt
cd rembrandt
uv run rembrandt
```

## Usage

### Terminal UI

Run `rembrandt` with no arguments. The preview panel on the right updates as you change the input image, color mode or shadow boost. Fill in the form and press **RENDER ASCII** (or `Ctrl+G`) to save the PNG:

| Field | Description |
| --- | --- |
| Input Image Path | Image to convert (JPG, PNG, …), relative to the directory you launched from |
| Output PNG Path | Where the rendered ASCII art is saved |
| Width (chars) | Number of characters per row — higher means more detail |
| Color Mode | True Color, CRT Green, Amber Terminal, or Monochrome B&W |
| Shadow Boost (0-100) | Brightens dark areas |
| Output Scale | Resize factor for the final PNG (e.g. `0.5`, `2.0`) |
| Output Size (WxH px) | Exact PNG size, e.g. `1200x1900`. Overrides Width and Scale (they're greyed out while it's set). The image is stretched if its proportions differ; the preview shows the result |
| Side-by-Side Original | Puts the original image next to the ASCII version |

A notification pops up when the PNG is saved (or if rendering fails). Press `q` to quit.

### Command line

Pass an image to render it directly, without opening the UI:

```sh
rembrandt photo.jpg                                  # saves rembrandt_out.png
rembrandt photo.jpg -o art.png -w 200 -m amber
rembrandt photo.jpg --side-by-side -s 0.5
rembrandt photo.jpg --size 1200x1900                 # exact output size in pixels
```

| Option | Default | Description |
| --- | --- | --- |
| `-o`, `--output` | `rembrandt_out.png` | Output PNG path |
| `-w`, `--width` | `160` | Width in characters |
| `-m`, `--mode` | `color` | `color`, `green`, `amber` or `bw` |
| `-b`, `--boost` | `35` | Shadow boost (0-100) |
| `-s`, `--scale` | `1.0` | Output scale |
| `--size` | — | Exact output size in pixels, e.g. `1200x1900` (overrides `--width` and `--scale`) |
| `--side-by-side` | off | Put the original image next to the ASCII art |

Run `rembrandt --help` for the full list.

## Development

```sh
uv sync          # create .venv and install dependencies
uv run rembrandt # run the app
uv run pytest    # run the tests
uv add <pkg>     # add a dependency
```

Project layout:

```
src/rembrandt/
  render.py    # image → ASCII conversion and PNG output (no UI code)
  app.py       # Textual terminal UI
  cli.py       # command-line entry point
  __main__.py  # enables `python -m rembrandt`
tests/         # pytest suite for the renderer and CLI
```

## License

Apache 2.0, see [LICENSE](LICENSE).
