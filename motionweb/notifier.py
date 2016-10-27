import asyncio
import websockets
import multiprocessing
import json
import redis
import types
import signal
from motionweb import utils
from concurrent.futures import ThreadPoolExecutor

listeners = set()

msg_queue = asyncio.Queue()
END_OF_QUEUE = object()

executor = ThreadPoolExecutor(1)

def queue_listener():
    # asyncio.set_event_loop(loop)
    rd = redis.StrictRedis(decode_responses=True)
    ps = rd.pubsub(ignore_subscribe_messages=True)
    ps.subscribe('video:new')
    while True:
        msg = ps.get_message()
        if msg:
            print('Message Received', msg)
            # new_video_handler(msg)
            # new_video_handler(msg)
            msg_queue.put_nowait(msg)


def new_video_handler(msg):
    print(msg)
    filename = msg['data']
    print('Data received: {}'.format(filename))
    video = utils.video_to_dict(filename)
    obj = json.dumps(video)
    print('Data sent: {}'.format(obj))
    for l in listeners:
        asyncio.ensure_future(l.send(obj))

async def setup_redis(loop):
    loop.run_in_executor(executor, queue_listener)
    print('Redis key store ready')
    while True:
        msg = await msg_queue.get()
        print('Message got', msg)
        if msg is END_OF_QUEUE:
            break
        new_video_handler(msg)
        # await asyncio.sleep(0.01)

    # async for msg in generator():
    # while True:
    #     msg = await generator()


async def handler(websocket, path):
    listeners.add(websocket)
    try:
        while True:
            await websocket.recv()
    # except websockets.exceptions.ConnectionClosed:
    #     pass
    finally:
        listeners.remove(websocket)

def run():
    stop_app = asyncio.Event()

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, stop_running, loop)
    loop.add_signal_handler(signal.SIGTERM, stop_running, loop)

    server_config = websockets.serve(handler, 'localhost', 8765)
    ws_server = loop.run_until_complete(server_config)
    loop.run_until_complete(setup_redis(loop))

    try:
        loop.run_forever()
    finally:
        ws_server.close()
        loop.run_until_complete(ws_server.wait_closed())

def stop_running(loop):
    print('Stopping event loop')
    executor.shutdown(wait=True)
    loop.close()

def start():
    proc = multiprocessing.Process(target=run)
    proc.start()

if __name__ == '__main__':
    run()
