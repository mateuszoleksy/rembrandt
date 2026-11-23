import argparse
import sys

from rembrandt.render import MODES, parse_size


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="rembrandt",
        description="Generate ASCII art from images. Run without arguments to open the terminal UI.",
    )
    parser.add_argument("input", nargs="?", help="image to convert (omit to open the UI)")
    parser.add_argument("-o", "--output", default="rembrandt_out.png", help="output PNG path (default: %(default)s)")
    parser.add_argument("-w", "--width", type=int, default=160, help="width in characters (default: %(default)s)")
    parser.add_argument("-m", "--mode", choices=MODES, default="color", help="color mode (default: %(default)s)")
    parser.add_argument("-b", "--boost", type=int, default=35, help="shadow boost 0-100 (default: %(default)s)")
    parser.add_argument("-s", "--scale", type=float, default=1.0, help="output scale (default: %(default)s)")
    parser.add_argument(
        "--size",
        type=parse_size,
        metavar="WxH",
        help="exact output size in pixels, e.g. 1200x1900 (overrides --width and --scale)",
    )
    parser.add_argument("--side-by-side", action="store_true", help="put the original image next to the ASCII art")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.input is None:
        # Imported lazily so headless renders don't pay for loading Textual
        from rembrandt.app import RembrandtApp

        RembrandtApp().run()
        return 0

    from rembrandt.render import render_ascii_image

    try:
        size = render_ascii_image(args.input, args.output, args.width, args.mode, args.boost, args.side_by_side, args.scale, args.size)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"Saved {args.output} ({size})")
    return 0
