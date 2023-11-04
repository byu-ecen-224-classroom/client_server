import asyncio
from pathlib import Path
from datetime import datetime

from aiohttp import web
import aiohttp_jinja2
import arrow
import jinja2

HOMEWORK_ID_LENGTH = 9
ROOT_DIR = "photos"

# TODO: Implement read_all...


async def handle_client(reader, writer):
    print("Client connected...")
    # Read in homework ID
    homework_id = await reader.read(HOMEWORK_ID_LENGTH)

    try:
        homework_id = homework_id.decode()
    except UnicodeDecodeError:
        print("Unable to decode homework_id")
        writer.write(f"Invalid homework ID: {homework_id}")
        await writer.drain()
        return

    # Read image data
    image_data = await reader.read()
    print(f"Received data from {homework_id}: {image_data[:10]}")

    path = Path(ROOT_DIR) / homework_id
    path.mkdir(parents=True, exist_ok=True)

    file_name = path / f"{arrow.now()}.bmp"
    print(f"Saving image to {file_name}...")

    with open(file_name, "wb") as f:
        f.write(image_data)

    print("Done!\n\n")


async def image_server():
    server = await asyncio.start_server(handle_client, "", 2240)

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"Serving on {addrs}")

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
    app["image_server"] = asyncio.create_task(image_server())


async def cleanup_background_tasks(app):
    app["image_server"].cancel()
    await app["image_server"]


def get_time(input):
    return arrow.get(input.stem).format("MMM D, YYYY h:mm A")


def get_relative_time(input):
    return arrow.get(input.stem).humanize()


def run():
    app = web.Application()

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
    web.run_app(app, port=2241)


if __name__ == "__main__":
    run()
