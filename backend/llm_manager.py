import os
from huggingface_hub import hf_hub_download
from llama_cpp import Llama

# Define model details
REPO_ID = "Qwen/Qwen2-0.5B-Instruct-GGUF"
FILENAME = "qwen2-0_5b-instruct-q4_k_m.gguf"
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

# Global LLM instance
_llm = None

def download_model():
    """Downloads the GGUF model if it doesn't exist locally."""
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR, exist_ok=True)
    
    model_path = os.path.join(MODELS_DIR, FILENAME)
    if os.path.exists(model_path):
        print(f"Model already exists at {model_path}")
        return model_path

    print(f"Downloading model {FILENAME} from {REPO_ID}...")
    downloaded_path = hf_hub_download(
        repo_id=REPO_ID,
        filename=FILENAME,
        local_dir=MODELS_DIR,
        local_dir_use_symlinks=False
    )
    print(f"Model downloaded to {downloaded_path}")
    return downloaded_path

def load_model():
    """Loads the model into memory."""
    global _llm
    if _llm is not None:
        return _llm
    
    model_path = download_model()
    print("Loading model into memory...")
    
    # Initialize Llama. n_ctx is context window, n_threads is CPU threads
    _llm = Llama(
        model_path=model_path,
        n_ctx=2048,
        n_threads=4,
        verbose=False # Set to True for debugging C++ output
    )
    print("Model loaded successfully.")
    return _llm

def unload_model():
    """Unloads the model to free up memory."""
    global _llm
    if _llm is not None:
        print("Unloading model...")
        del _llm
        _llm = None
        print("Model unloaded.")
    else:
        print("Model is not currently loaded.")

def generate_json(system_prompt: str, user_prompt: str):
    """
    Generates a response enforcing JSON output if possible.
    Qwen-0.5B-Instruct can follow simple JSON formats.
    """
    llm = load_model()
    
    prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n"
    
    response = llm(
        prompt,
        max_tokens=256,
        stop=["<|im_end|>"],
        temperature=0.1,
        # For stricter JSON, you can use grammar or just prompt engineering
    )
    return response["choices"][0]["text"].strip()
