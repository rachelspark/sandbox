import json
import os
from pathlib import Path

import modal
from fastapi import FastAPI
from fastapi.responses import StreamingResponse


app = modal.App("rachel-sandbox")

# Should the token id/secret be in the request headers/cookies?
# @modal.web_endpoint()
# , modal_token_id: str, modal_token_secret: str, modal_environment: str):

@app.function()
async def run_user_code(code: str, session_id: str, session_secret: str, workspace_name: str, modal_environment: str):
    import aiostream

    # Write code into user_code.py
    with open("user_code.py", "w") as f:
        f.write(code)

    user_credentials = {
        "MODAL_SESSION_ID": session_id,
        "MODAL_SESSION_SECRET": session_secret,
        "MODAL_WORKSPACE": workspace_name,
        "MODAL_ENVIRONMENT": modal_environment,
    }

    sb = app.spawn_sandbox(
        "modal",
        "run",
        "/app/user_code.py",
        image=modal.Image.debian_slim().apt_install("git").run_commands("git clone -b rachel/add-session-creds https://github.com/modal-labs/modal-client.git /modal").run_commands("pip install -e /modal"),
        mounts=[modal.Mount.from_local_file("user_code.py", "/app/user_code.py")],
        secrets=[modal.Secret.from_dict(user_credentials)],
    )

    async for line in aiostream.stream.merge(sb.stdout, sb.stderr):
        print("yield line: ", line)
        yield line

    sb.wait()

@app.function()
@modal.web_endpoint(method="POST")
async def playground(data: dict):
    session_id = data.get("session_id")
    session_secret = data.get("session_secret")
    workspace_name = data.get("workspace_name")
    modal_environment = data.get("modal_environment")

    code = data.get("code")

    print(f"session id {session_id}")
    print(f"session secret {session_secret}")
    print(f"workspace name {workspace_name}")
    print(f"modal environment {modal_environment}")
    print(code)

    async def stream():
        async for line in run_user_code.remote_gen.aio(code, session_id, session_secret, workspace_name, modal_environment):
            yield f"{json.dumps(dict(text=line), ensure_ascii=False)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")

@app.function()
@modal.asgi_app(label="playground")
def api():
    from fastapi import FastAPI
    from fastapi.responses import StreamingResponse

    web_app = FastAPI()

    @web_app.post("/execute")
    async def execute(data: dict):
        session_id = data.get("session_id")
        session_secret = data.get("session_secret")
        workspace_name = data.get("workspace_name")
        modal_environment = data.get("modal_environment")

        code = data.get("code")

        print(code)

        async def stream():
            async for line in run_user_code.remote_gen.aio(code, session_id, session_secret, workspace_name, modal_environment):
                yield f"data: {json.dumps(dict(text=line), ensure_ascii=False)}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")




# frontend_path = Path(__file__).parent / "frontend"


# @app.function(
#     mounts=[modal.Mount.from_local_dir(frontend_path, remote_path="/assets")],
#     allow_concurrent_inputs=20,
#     keep_warm=2,
# )
# @modal.asgi_app(label="exec")
# def api():
#     from fastapi import FastAPI
#     from fastapi.responses import StreamingResponse
#     from fastapi.staticfiles import StaticFiles

#     web_app = FastAPI()

#     @web_app.get("/execute")
#     async def execute(code: str):
#         print(code)

#         async def stream():
#             async for line in run_user_code.remote_gen.aio(code, ):
#                 yield f"data: {json.dumps(dict(text=line), ensure_ascii=False)}\n\n"

#         return StreamingResponse(stream(), media_type="text/event-stream")

#     web_app.mount("/", StaticFiles(directory="/assets", html=True))
#     return web_app


test_text = """import time

import modal

app = modal.App()

@app.function()
def main():
    print(time.time())"""


@app.local_entrypoint()
def main():
    run_user_code.remote(test_text, session_id="se-GIuIP6IJMtjX8zenoVn85J", session_secret="xx-XmRxtq4tVdBlqJxLPN4rra", workspace_name="rachelspark", modal_environment="main")
