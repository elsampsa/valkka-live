import asyncio
import time, sys, os, socket, pickle, json
import websockets

async def hello(websocket, path):
    """new websocket connection
    """
    # ipc_file = os.environ["VALKKA_PYRAMID_IPC"]
    ipc_file = sys.argv[1]
    assert(os.path.exists(ipc_file))
    print("websocket requested, path :", path)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)    

    """sync
    try:
        sock.connect(ipc_file)
    except Exception as e:
        print("ws_serve: ipc connect failed with", e)
        return
    while True:
        try:
            incoming = await websocket.recv()
        except Exception as e:
            print("ws_serve: error", e)
            break
        if len(incoming) < 1:
            break
        # message from websocket
        msg = incoming
        print("sending", msg)
        sock.send(pickle.dumps(msg))
    sock.close()
    """

    #"""async
    sock.setblocking(False)
    sock.connect(ipc_file)
    reader, writer = await asyncio.open_connection(sock = sock)

    # schedule tasks
    loop = asyncio.get_event_loop()
    lis = []
    ws_task = loop.create_task(websocket.recv()) # websocket
    lis.append(ws_task)
    us_task = loop.create_task(reader.read()) # unix socket
    lis.append(us_task)

    while True:
        done, pending = await asyncio.wait(lis, return_when = asyncio.FIRST_COMPLETED)
        lis = list(pending)
        print("wait completed")

        if ws_task in done:
            # message from websocket, forward to unix ipc
            msg = ws_task.result()
            print("sending to ipc", msg)
            msg = json.loads(msg)
            writer.write(pickle.dumps(msg))
            await writer.drain()
            # re-schedule
            ws_task = loop.create_task(websocket.recv()) # websocket
            lis.append(ws_task)

        if us_task in done:
            # TODO: incoming messages for IPCQThread 
            # message from unix ipc, forward to websocket
            msg = us_task.result()
            msg = pickle.loads(msg)
            print("sending to ws", msg)
            websocket.send(msg)
            # re-schedule
            us_task = loop.create_task(reader.read()) # unix socket
            lis.append(us_task)

    print("ws_serve: closing ipc socket")
    reader.close()
    writer.close()
    await reader.wait_closed()
    await writer.wait_closed()
    print("ws_serve: closing websocket")

    #"""


def main():
    start_server = websockets.serve(hello, 'localhost', 5001)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()

