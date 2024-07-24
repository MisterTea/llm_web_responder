import logging
import multiprocessing
import os
import time
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.

import requests
from rich.progress import Progress

logger = logging.getLogger(__name__)

USE_GPU = True

class LargeLanguageModel:
    def llm(self, system_prompt: str, user_prompt: str, stop: List[str] = [], echo: bool = False) -> str:
        raise NotImplementedError()

    def model_name(self):
        raise NotImplementedError()


class LlamaCppLanguageModel:
    MODEL_NAME = "Meta-Llama-3-8B-Instruct-Q5_K_M.gguf"
    #MODEL_NAME = "Meta-Llama-3-8B-Instruct-Q8_0.gguf"
    MODEL_PATH = "https://huggingface.co/lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF/resolve/main"
    
    #MODEL_NAME = "Meta-Llama-3-70B-Instruct-IQ1_M.gguf"
    #MODEL_NAME = "Meta-Llama-3-70B-Instruct-IQ2_XS.gguf"
    #MODEL_NAME = "Meta-Llama-3-70B-Instruct-Q4_K_M.gguf"
    #MODEL_PATH = "https://huggingface.co/lmstudio-community/Meta-Llama-3-70B-Instruct-GGUF/resolve/main"

    #MODEL_NAME = "Meta-Llama-3-8B-Instruct-fp16.gguf"
    #MODEL_PATH = "https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main"
    
    CHAT_FORMAT = "llama-3"

    #MODEL_NAME = "Phi-3-mini-4k-instruct-fp16.gguf"
    #MODEL_PATH = "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main"
    #CHAT_FORMAT = "phi3"

    def __init__(self):
        self.llm_model = None

    def model_name(self):
        return LlamaCppLanguageModel.MODEL_NAME

    def model_path(self):
        return LlamaCppLanguageModel.MODEL_PATH

    def llm(self, system_prompt: Optional[str], user_prompt: str, stop: List[str] = [], echo: bool = False) -> str:
        if self.llm_model == None:
            model_path = f"gpt_models/{self.model_name()}"
            if not os.path.exists(model_path):
                if not os.path.exists("gpt_models"):
                    os.makedirs("gpt_models")
                    logger.warning(
                        'gpt_models path is missing.  Did you forget to add "-v gpt_models:/gpt_models" to your docker run?'
                    )
                # Download the model
                download_file(
                    #f"https://huggingface.co/TheBloke/koala-13B-GPTQ-4bit-128g-GGML/resolve/main/{self.model_name()}"
                    f"{self.model_path()}/{self.model_name()}"
                )
            from llama_cpp import Llama

            self.llm_model = Llama(
                model_path=model_path,
                n_gpu_layers=-1 if USE_GPU else 0, # Use gpu
                n_ctx=4000,
                n_threads=multiprocessing.cpu_count(),
                embedding=True,
                verbose=True,
                #chat_format="llama-3",
            )

        if LlamaCppLanguageModel.CHAT_FORMAT == "phi3":
            user_prompt = system_prompt + "\n\n" + user_prompt
            system_prompt = None
        retval = self.llm_model.create_chat_completion(messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            },
        ], stop=stop)["choices"][0]

        print(type(retval))
        print(retval)
        print(retval.keys())

        return retval["message"]["content"]  # type: ignore


class OpenAiLanguageModel:
    def __init__(self):
        from openai import OpenAI

        self.client = OpenAI()

    def model_name(self):
        return "gpt-4o-mini-2024-07-18"
        #return "gpt-3.5-turbo"

    def llm(self, system_prompt: str, user_prompt: str, stop: Optional[List[str]] = None, echo: bool = False) -> str:
        import openai

        if stop is not None and len(stop) == 0:
            stop = None

        for x in range(0, 5):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name(),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    stop=stop,
                )
                print(response)
                return response.choices[0].message.content
            except openai.RateLimitError as ex:
                logger.debug("Rate limit error: " + str(ex))
                time.sleep(5.0)
        raise Exception("OpenAI Rate Limit 5 times")



def download_file(url):
    local_filename = url.split("/")[-1]
    # NOTE the stream=True parameter below
    try:
        with requests.get(url, stream=True) as r:
            content_length = int(r.headers["Content-Length"])
            with Progress() as progress:
                task1 = progress.add_task(
                    "[light_green]Downloading GPT model (this only happens once)...",
                    total=content_length,
                )

                r.raise_for_status()
                with open("gpt_models/" + local_filename, "wb") as f:
                    total_downloaded = 0
                    for chunk in r.iter_content(chunk_size=64 * 1024 * 1024):
                        # If you have chunk encoded response uncomment if
                        # and set chunk_size parameter to None.
                        # if chunk:
                        f.write(chunk)
                        total_downloaded += len(chunk)
                        # print(f"Downloaded {int((total_downloaded*100.0)/content_length)}%")
                        progress.update(task1, completed=total_downloaded)
        return local_filename
    except:
        logger.warning("Error downloading file")
        if os.path.exists("gpt_models/" + local_filename):
            os.remove("gpt_models/" + local_filename)
        raise


#llm = LlamaCppLanguageModel()
llm = OpenAiLanguageModel()

if __name__ == "__main__":
    retval = llm.llm("Answer in a github flavored markdown table with columns \"question\" and \"answer\"", "What is the capital of France?", stop=[], echo=True)

    questions = [
        "Is the message about applying to work at Latitude?  Begin your answer with either \"yes\" or \"no\" followed by an explanation.",
        "Is the message a candidate referral for a position at Jason's company?  Begin your answer with either \"yes\" or \"no\" followed by an explanation.",
        "Is the message about job opportunities?  Begin your answer with either \"yes\" or \"no\" followed by an explanation.",
        "Does the message ask if Jason is hiring?  Begin your answer with either \"yes\" or \"no\" followed by an explanation.",
        "Is the message asking whether Latitude is hiring?  Begin your answer with either \"yes\" or \"no\" followed by an explanation.",
        "Is the message about asking someone to a meeting or consulation?  Begin your answer with either \"yes\" or \"no\" followed by an explanation.",
        "Is the message about recruitment services?  Begin your answer with either \"yes\" or \"no\" followed by an explanation."
        "Is the message about hiring development teams?  Begin your answer with either \"yes\" or \"no\" followed by an explanation."
    ]
    for question in questions:
        retval = llm.llm(question,
                        
                        """
    Hi Jason,

    I wanted to bring the attached candidate to your attention. She has just come on to the market and comes highly recommended from a reliable contact.

    Let me know if her profile could be of interest to you and your team?

    Thanks!

    Chris Hopkins
    Vice President I USA | Tech Podcast Host | Entrepreneur | 🐍 Python Recruitment Specialist
    """, stop=[], echo=True)

        print(retval)
        print(retval.startswith("yes"))
