# Rcode
import os
import uuid
import sys
import hashlib
import platform
import asyncio
from websockets import server
import json
import dotenv
import subprocess

import clients
import context

dotenv.load_dotenv()

Clients: dict[uuid.UUID, clients.ClientExtention] = {}

TARGET, SCHEME, CONF = range(3)

async def getProjectList(project: str, search_type: int) -> tuple[bool, list[str] | str]:
    cmd = f"xcodebuild -list -project {project}"
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        return (False, str(stderr))
    else:
        result = "\n".join(str(stdout).split(f"Infomation about project \"")[1].splitlines()[1:])
        r = result.splitlines()
        challenge = False
        results: list[str] = []
        if search_type == TARGET:
            search = "Targets:"
        elif search_type == SCHEME:
            search = "Schemes:"
        elif search_type == CONF:
            search = "Build Configurations:"
        else:
            return (False, "Invalid search type")
        for i in range(len(result.splitlines())):
            if not challenge:
                if r[i].strip().startswith(search):
                    for j in r[i:]:
                        if j.strip() == "":
                            challenge = True
                            break
                        else:
                            results.append(j.strip())
            else:
                break
        return (True, results)


async def serve_handler(websocket: server.WebSocketServerProtocol, path: str):
    async for message in websocket:
        if websocket.id not in Clients:
            try:
                data = json.loads(message)
                if data["type"] != "handshake":
                    await websocket.send(json.dumps({"error": "Handshake required"}))
                    await websocket.close()
                    return
                if hashlib.md5(data["item"]["password"].encode()).hexdigest() != os.environ["RCODE_HASHPASS"]:
                    await websocket.send(json.dumps({"error": "Invalid password"}))
                    await websocket.close()
                    return
                client = clients.ClientExtention(websocket)
                Clients[websocket.id] = client
                await client.send(json.dumps({"type": "handshake", "item": {"message": "Handshake successful"}}))
            except Exception as e:
                await websocket.send(json.dumps({"error": str(e)}))
                await websocket.close()
                return
        else:
            try:
                client = Clients[websocket.id]
                ctx = context.Context(json.loads(message))
                if ctx.type == "handshake":
                    await client.send(json.dumps(
                        {"type": "handshake", "item": {"message": "Handshake already done"}}
                    ))
                elif ctx.type == "command":
                    if ctx.command == "ping":
                        await client.send(json.dumps(
                            {"type": "pong", "item": {"command": "pong", "arguments": {"time": websocket.latency}}}
                        ))
                    elif ctx.command == "ls":
                        _path = os.path.join(client.ospath, str(ctx.arguments["path"]))
                        if not os.path.exists(_path):
                            await client.send(json.dumps(
                                {"type": "ls", "item": {"command": "ls", "arguments": {"error": "Path does not exist"}}}
                            ))
                        else:
                            files = [file for file in os.listdir(_path) if os.path.isfile(os.path.join(_path, file))]
                            directories = [directory for directory in os.listdir(_path) if os.path.isdir(os.path.join(_path, directory))]
                            await client.send(json.dumps(
                                {"type": "ls", "item": {"command": "ls", "arguments": {"files": files, "directories": directories}}}
                            ))
                    elif ctx.command == "cd":
                        _path = os.path.join(client.ospath, str(ctx.arguments["path"]))
                        if not os.path.exists(_path):
                            await client.send(json.dumps(
                                {"type": "cd", "item": {"command": "cd", "arguments": {"error": "Path does not exist"}}}
                            ))
                        else:
                            client.ospath = _path
                            await client.send(json.dumps(
                                {"type": "cd", "item": {"command": "cd", "arguments": {"message": "Changed directory", "path": client.ospath}}}
                            ))
                    elif ctx.command == "pwd":
                        await client.send(json.dumps(
                            {"type": "pwd", "item": {"command": "pwd", "arguments": {"path": client.ospath}}}
                        ))
                    elif ctx.command == "select_project":
                        _project = os.path.join(client.ospath, str(ctx.arguments["project"]))
                        if not os.path.exists(_project):
                            await client.send(json.dumps(
                                {"type": "select_project", "item": {"command": "select_project", "arguments": {"error": "Project does not exist"}}}
                            ))
                        else:
                            if _project.split(".")[-1] != "xcodeproj":
                                await client.send(json.dumps(
                                    {"type": "select_project", "item": {"command": "select_project", "arguments": {"error": "Project is not an Xcode project"}}}
                                ))
                            else:
                                client.project = _project
                                await client.send(json.dumps(
                                    {"type": "select_project", "item": {"command": "select_project", "arguments": {"message": "Selected project", "project": client.project}}}
                                ))
                    elif ctx.command == "get_project":
                        await client.send(json.dumps(
                            {"type": "get_project", "item": {"command": "get_project", "arguments": {"project": client.project}}}
                        ))
                    elif ctx.command == "get":
                        if ctx.arguments["type"] == "schemes":
                            result, schemes = await getProjectList(client.project, SCHEME)
                            if result:
                                await client.send(json.dumps(
                                    {"type": "get", "item": {"command": "get", "arguments": {"type": "schemes", "schemes": schemes}}}
                                ))
                            else:
                                if client.scheme == "":
                                    client.scheme = schemes[0]
                                await client.send(json.dumps(
                                    {"type": "get", "item": {"command": "get", "arguments": {"type": "schemes", "error": schemes}}}
                                ))
                        elif ctx.arguments["type"] == "targets":
                            result, targets = await getProjectList(client.project, TARGET)
                            if result:
                                await client.send(json.dumps(
                                    {"type": "get", "item": {"command": "get", "arguments": {"type": "schemes", "schemes": targets}}}
                                ))
                            else:
                                if client.target == "":
                                    client.target = targets[0]
                                await client.send(json.dumps(
                                    {"type": "get", "item": {"command": "get", "arguments": {"type": "schemes", "error": targets}}}
                                ))
                        elif ctx.arguments["type"] == "configurations":
                            result, confs = await getProjectList(client.project, CONF)
                            if result:
                                await client.send(json.dumps(
                                    {"type": "get", "item": {"command": "get", "arguments": {"type": "schemes", "schemes": confs}}}
                                ))
                            else:
                                if client.conf == "":
                                    client.conf = confs[0]
                                await client.send(json.dumps(
                                    {"type": "get", "item": {"command": "get", "arguments": {"type": "schemes", "error": confs}}}
                                ))
                    elif ctx.command == "build":
                        cmd = f"xcodebuild -target {client.target} -sdk {client.sdk} -configuration {client.conf} -scheme {client.scheme} build"

                await websocket.send(message)
            except Exception as e:
                await websocket.send(json.dumps({"error": str(e)}))
                await websocket.close()
                del Clients[websocket.id]

async def main(port: int = 8765):
    print(f"Rcode WebSocket Server is listening on port {port}")
    async with server.serve(serve_handler, "0.0.0.0", port):
        await asyncio.Future()

if __name__ == "__main__":
    # if platform.system() != "Darwin":
    #     print("Rcode WebSocket Server is not supported on Windows or Linux")
    #     exit(1)
    os.environ["RCODE_HASHPASS"] = hashlib.md5(os.environ["RCODE_PASSWORD"].encode()).hexdigest()
    asyncio.run(main(
        port=int(os.environ.get("RCODE_PORT", 8765))
    ))
