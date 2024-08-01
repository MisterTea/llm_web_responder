import base64
import io

import requests
from PIL import Image
from PIL.Image import Image as ImageType
from transformers import AutoModelForCausalLM, AutoProcessor


class VisionLanguageModel:
    def __init__(self):
        pass

    def model_name(self) -> str:
        raise ValueError("Not implemented")
    
    def vlm(self, image:ImageType, prompt:str, system_prompt:str) -> str:
        raise ValueError("Not implemented")

# Open the image file and encode it as a base64 string
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

class GptVisionLanguageModel(VisionLanguageModel):
    def __init__(self):
        super().__init__()
        from openai import OpenAI

        self.client = OpenAI()

    def model_name(self) -> str:
        return "gpt-4o-2024-05-13"

    def vlm(self, image:ImageType, prompt:str, system_prompt:str) -> str:
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        response = self.client.chat.completions.create(
        model=self.model_name(),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{img_str}"}
                }
            ]}
        ],
        temperature=0.0,
        )

        print("GPT VLM",prompt,"->",response.choices[0].message.content)
        return response.choices[0].message.content

class Phi3VisionLanguageModel(VisionLanguageModel):
    def __init__(self):
        super().__init__()
        self.model = None
        self.processor = None

    def model_name(self) -> str:
        return "microsoft/Phi-3-vision-128k-instruct"
    
    def vlm(self, image:ImageType, prompt:str, system_prompt:str) -> str:
        if self.model is None:
            self.model = AutoModelForCausalLM.from_pretrained(self.model_name(), device_map="cuda", trust_remote_code=True, torch_dtype="auto", _attn_implementation='flash_attention_2') # use _attn_implementation='eager' to disable flash attention

            self.processor = AutoProcessor.from_pretrained(self.model_name(), trust_remote_code=True) 
        assert self.processor is not None

        messages = [
            {"role": "user", "content": prompt},
            {"role": "system", "content": system_prompt},
        ]

        prompt = self.processor.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

        inputs = self.processor(prompt, [image], return_tensors="pt").to("cuda:0") 

        generation_args = { 
            "max_new_tokens": 500, 
            #"temperature": 0.0, 
            #"do_sample": False, 
        } 

        generate_ids = self.model.generate(**inputs, eos_token_id=self.processor.tokenizer.eos_token_id, **generation_args) 

        # remove input tokens 
        generate_ids = generate_ids[:, inputs['input_ids'].shape[1]:]
        responses = self.processor.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        assert len(responses) == 1

        response = responses[0]

        print("VLM", messages, " -> ", response)
        return response
