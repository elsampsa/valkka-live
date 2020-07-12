import asyncio
import time, sys, os, socket, pickle, json
import websockets


"""
::

    Qt main thread <-- Qt signals --> IPCQThread <-- unix domains socket --> Websocket server [THIS ONE]

"""


async def hello(websocket, path):
    """new websocket connection
    """
    # ipc_file = os.environ["VALKKA_PYRAMID_IPC"]
    ipc_file = sys.argv[1]
    assert(os.path.exists(ipc_file))
    print("ws_serve: websocket requested, path :", path)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)    
    print("ws_serve: socket", sock)

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
    us_task = loop.create_task(reader.read(1024)) # unix socket
    lis.append(us_task)

    while True:
        #print("\nws_serve: waiting", lis)
        done, pending = await asyncio.wait(lis, return_when = asyncio.FIRST_COMPLETED)
        lis = list(pending)
        #print("\nws_serve: wait completed: still pending", lis)

        if ws_task in done:
            # message from websocket, forward to unix ipc
            """message is a json:
            {
                "class" : "base",
                "name" : "click",
                "parameters" : null
            }
            """
            msg = ws_task.result()
            #print("ws_serve: sending to ipc", msg)
            msg = json.loads(msg)
            writer.write(pickle.dumps(msg))
            await writer.drain()
            # re-schedule
            ws_task = loop.create_task(websocket.recv()) # websocket
            lis.append(ws_task)

        if us_task in done:
            msg = us_task.result()
            #print("ws_serve: got from ipc raw", msg)
            msg = pickle.loads(msg) # last char is endline
            #print("ws_serve: got from ipc", msg)
            print("ws_serve: sending to ws", msg)
            await websocket.send(json.dumps(msg))
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

