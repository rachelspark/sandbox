<script lang="ts">
    import "../app.css";
    import { onMount } from 'svelte';
    import CodeMirror from "svelte-codemirror-editor";
    import { python } from "@codemirror/lang-python";
    import { materialDark } from '@uiw/codemirror-theme-material';
    import { writable } from "svelte/store";

    interface ResultItem {
        id: number;
        code: string;
        result: string;
        loading: boolean;
    }


    let value: string = '';
    let sessionId: string = '';
    let sessionSecret: string = '';
    let workspaceName: string = '';
    let modalEnvironment: string = '';

    let result = '';
    let loading = false;

    onMount(() => {
      loadCpuCode();
      sessionId = localStorage.getItem('sessionId') || '';
      sessionSecret = localStorage.getItem('sessionSecret') || '';
      workspaceName = localStorage.getItem('workspaceName') || '';
      modalEnvironment = localStorage.getItem('modalEnvironment') || '';
    });


    function loadCpuCode(): void {
        const cpuCode: string = `import modal

app = modal.App()

@app.function()
def f(i):
    if i % 2 == 0:
        print("hello", i)
    else:
        print("world", i)

    return i * i

@app.local_entrypoint()
def main():
    # run the function locally
    print(f.local(1000))

    # run the function remotely on Modal
    print(f.remote(1000))

    # run the function in parallel and remotely on Modal
    total = 0
    for ret in f.map(range(20)):
        total += ret

    print(total)`
        value = cpuCode;
    }

    function loadGpuCode(): void {
      const gpuCode: string = `import modal
  
app = modal.App()
  
@app.function(gpu="a100")
def f():
    import subprocess
  
    subprocess.run(["nvidia-smi"])
  
@app.local_entrypoint()
def main():
    f.remote()`;
  
      value = gpuCode;
    }


    async function runCode(): Promise<void> {
        if (!value) return;

        result = '';
        loading = true;
        
        try {
            const response: Response = await fetch('https://modal-labs-rachel-dev--rachel-sandbox-playground.modal.run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    code: value,
                    session_id: sessionId,
                    session_secret: sessionSecret,
                    workspace_name: workspaceName,
                    modal_environment: modalEnvironment
                }),
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const reader = response.body?.getReader();
            let receivedLength = 0; 
            let chunks = [];
    
            while(true) {
                const {done, value} = await reader!.read();

                if (done) {
                    break;
                }

                chunks.push(value);
                receivedLength += value.length;

                let text = new TextDecoder("utf-8").decode(value, {stream: true});
                text.split('\n').forEach(line => {
                    if (line) {
                        try {
                            let json = JSON.parse(line);
                            result += json.text + '\n'; // Append the text property from each JSON object
                        } catch (e) {
                            console.error('Error parsing JSON:', e);
                        }
                        }
                    });
            }
        } catch (error) {
            if (error instanceof Error) {
                result = `Error: ${error.message}`;
            } else {
                result = 'An unknown error occurred';
            }
        } finally {
            loading = false;
        }
    }
  </script>
  
  <main class="mx-auto pt-4 px-4 text-white bg-[#0C0F0B]">
    <div class="text-2xl my-4 text-center">
      Modal Code Playground
    </div>

    <div class="flex flex-col">
        <div class="flex flex-row justify-between h-[800px]">
            <div class="w-1/2 h-full p-2 flex flex-col">
                <div class="flex flex-col mb-2">
                    <input type="text" bind:value={sessionId} placeholder="Session ID" class="text-black text-input my-1 px-1 rounded-sm">
                    <input type="text" bind:value={sessionSecret} placeholder="Session Secret" class="text-black text-input my-1 px-1 rounded-sm">
                    <input type="text" bind:value={workspaceName} placeholder="Workspace Name" class="text-black text-input my-1 px-1 rounded-sm">
                    <input type="text" bind:value={modalEnvironment} placeholder="Modal Environment" class="text-black text-input my-1 px-1 rounded-sm">
                    <div class="flex items-center justify-between my-2">
                        <div>
                            <button on:click={loadCpuCode} class="btn">Hello world</button>
                            <button on:click={loadGpuCode} class="btn">GPU</button>
                        </div>
                        <button on:click={runCode} class="text-sm rounded-sm bg-[#7FEE64] px-2 py-1 text-black hover:bg-[#7FEE64]/80">
                            Run
                        </button>
                    </div>
                </div>
                <div class="flex-grow overflow-hidden"> 
                    <CodeMirror bind:value lang={python()} theme={materialDark} class="h-full" />
                </div>
            </div>
            {#if result || loading}
            <div class="w-1/2 h-full p-2 overflow-auto border border-white/20">
                <div class="h-full p-4">
                    <pre class="text-xs text-white">{result}</pre>
                </div>
            </div>
            {/if}
        </div>
    </div>
</main>

<style>
    :global(body) {
      background-color: #0C0F0B;
      color: white;
    }

    :global(.cm-editor) {
        height: 100%;
    }

    :global(.cm-scroller) {
        overflow: auto;
    }
</style>