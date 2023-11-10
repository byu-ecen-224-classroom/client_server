import argparse
import asyncio
import functools
import logging
import logging.handlers
from pathlib import Path
import re

from aiohttp import web
import aiohttp_jinja2
import arrow
import jinja2

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(level=logging.INFO)

# Set up output to file
LOGGER.addHandler(
    logging.handlers.TimedRotatingFileHandler("client_lab_server.log", when="midnight")
)
# Set up output to terminal
LOGGER.addHandler(logging.StreamHandler())


HOMEWORK_ID_LENGTH = 9
IMAGE_SIZE = 49206
ROOT_DIR = "photos"


async def send_error(writer, message):
    writer.write(message)
    await writer.drain()
    writer.close()
    await writer.wait_closed()
    LOGGER.info("\n\n")


async def handle_client(reader, writer, delay=0, timeout=5):
    LOGGER.info("Client connected...")

    # Read in homework ID
    try:
        homework_id = await asyncio.wait_for(
            reader.readexactly(HOMEWORK_ID_LENGTH), timeout=timeout
        )
    except TimeoutError:
        LOGGER.info("Receiving homework ID took too long...")
        await send_error(writer, b"ERROR: Did not receive enough data")
        return
    except asyncio.IncompleteReadError:
        LOGGER.info("Incomplete read error for homework ID")
        await send_error(writer, b"Unable to read homework ID")
        return

    try:
        homework_id = homework_id.decode()
    except UnicodeDecodeError:
        LOGGER.info(f"Unable to decode homework_id: {homework_id[:50]}")
        await send_error(
            writer, f"ERROR: Invalid homework ID {homework_id[:50]}".encode()
        )
        return

    if not re.fullmatch("[A-F0-9]{9}", homework_id):
        LOGGER.info(f"Invalid homework_id: {homework_id[:50]}")
        await send_error(
            writer, f"ERROR: Invalid homework ID {homework_id[:50]}".encode()
        )
        return

    LOGGER.info(
        f"Received valid homework ID {homework_id}. Now receiving image data..."
    )

    if delay:
        LOGGER.info(f"Sleeping for {delay} seconds...")
        await asyncio.sleep(delay)

    try:
        image_data = await asyncio.wait_for(
            reader.readexactly(IMAGE_SIZE), timeout=timeout
        )
    except TimeoutError:
        LOGGER.info("Receiving image data took too long")
        await send_error(writer, b"ERROR: Did not receive enough data")
        return
    except asyncio.IncompleteReadError:
        LOGGER.info("Incomplete read error for image data")
        await send_error(writer, b"ERROR: Unable to read image data")
        return

    LOGGER.info(f"Received data from {homework_id}: {image_data[:50]}")

    # Make sure the data starts with the right bytes
    if image_data[:2] != b"BM":
        LOGGER.info(f"Invalid BMP file: It doesn't start with BM.")
        await send_error(writer, b"ERROR: BMP file does not start with BM")
        return

    path = Path(ROOT_DIR) / homework_id
    path.mkdir(parents=True, exist_ok=True)

    file_name = path / f"{arrow.now()}.bmp"
    LOGGER.info(f"Saving image to {file_name}...")

    with open(file_name, "wb") as f:
        f.write(image_data)

    LOGGER.info("Done!\n\n")
    writer.write(b"SUCCESS")
    await writer.drain()

    writer.close()
    await writer.wait_closed()


async def image_server(port, delay, timeout):
    server = await asyncio.start_server(
        functools.partial(handle_client, delay=delay, timeout=timeout), "0.0.0.0", port
    )

    print(f"======== Running on tcp://0.0.0.0:{port} with {delay} s of delay ========")

    async with server:
        await server.serve_forever()


@aiohttp_jinja2.template("index.html")
async def index(request):
    homework_id = request.match_info["homework_id"]

    # Get a list of all the files in the folder
    path = Path(ROOT_DIR) / homework_id
    files = sorted(path.glob("*.bmp"), reverse=True)

    return {"homework_id": homework_id, "file_names": files}


async def start_background_tasks(app):
    app["image_server"] = asyncio.create_task(
        image_server(app["image_port"], app["delay"], app["timeout"])
    )


async def cleanup_background_tasks(app):
    app["image_server"].cancel()
    await app["image_server"]


def get_time(input):
    try:
        return arrow.get(input.stem).to("US/Mountain").format("MMM D, YYYY h:mm A")
    except arrow.parser.ParserError:
        return ""


def get_relative_time(input):
    try:
        return arrow.get(input.stem).humanize()
    except arrow.parser.ParserError:
        return ""


def run(image_port=2240, web_port=2241, delay=0, timeout=5):
    app = web.Application()

    # Set some custom configuration
    app["image_port"] = image_port
    app["delay"] = delay
    app["timeout"] = timeout

    # Setup templates
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader("templates"),
        filters=[
            ("get_time", get_time),
            ("get_relative_time", get_relative_time),
        ],
    )

    # Setup application
    app.add_routes([web.get("/{homework_id:[A-F0-9]{9}}", index)])
    app.router.add_static("/photos", path="photos/")
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    web.run_app(app, port=web_port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-server-port", type=int, default=2240)
    parser.add_argument("--web-server-port", type=int, default=2241)
    parser.add_argument(
        "--delay",
        type=float,
        default=0,
        help="How long (in seconds) to delay the response. We are trying to "
        "lead up to why you need a threaded client, but if the server is too "
        "fast, then it might look like its instantaneous, which negates the "
        "need for a threaded client.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="How long to wait (in seconds) to receive data from the client "
        "before timing out. If a client does not send all of the data the "
        "server expects, but starts receiving data, then there can be a "
        "deadlock of the client and server both waiting to receive. If the "
        "timeout expires before receiving all the expected data, then the "
        "server sends back and error message.",
    )
    args = parser.parse_args()

    run(args.image_server_port, args.web_server_port, args.delay, args.timeout)
