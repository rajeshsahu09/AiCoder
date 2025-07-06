# android_code_ai/rag_system.py
import openai
from typing import Dict
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import torch

class AndroidRAGSystem:
    MAX_CONTEXT_TOKENS = 4000  # Max tokens for context
    
    def __init__(self, context_engine):
        self.context_engine = context_engine
        # Define the save directory
        save_directory = "./deepseek-ai/deepseek-coder-1.3b-base-saved"

        self.tokenizer = AutoTokenizer.from_pretrained(
            "deepseek-ai/deepseek-coder-1.3b-base", trust_remote_code=True)
        self.bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            save_directory, 
            device_map='auto',
            trust_remote_code=True,
            # quantization_config= self.bnb_config
            )
        print(f"model size {self.model.get_memory_footprint()/1024/1024/1024} GB")
        self.model.config.pad_token_id = self.model.config.eos_token_id
        self.tokenizer.pad_token = self.tokenizer.eos_token
        # Save the model
        self.model.save_pretrained(save_directory)
        self.tokenizer.save_pretrained(save_directory)
    
    def generate_response(self, query: str) -> str:
        """Generate an AI response with automatically retrieved context"""
        # Step 1: Automatically retrieve relevant context
        context = self.context_engine.get_context(query)
        
        # Step 2: Format the prompt with context
        prompt = self._build_prompt(query, context)

        print("*****", prompt)
        
        # Step 3: Call the LLM
        response = self._call_llm(prompt)
        
        return response
    
    def _build_prompt(self, query: str, context: Dict) -> str:
        """Build a comprehensive prompt with automatically retrieved context"""
        prompt_parts = [
            "You are an expert Android developer assistant. Use the following context from the codebase to answer the question.",
            f"Question: {query}\n\n"
        ]
        
        # Add chunk context
        if context['chunks']:
            prompt_parts.append("Most Relevant Code Snippets:")
            for i, chunk in enumerate(context['chunks']):
                prompt_parts.append(f"### Snippet {i+1} ({chunk['metadata']['type']})")
                prompt_parts.append(f"File: {chunk['metadata']['file_path']}")
                prompt_parts.append(chunk['document'])
                prompt_parts.append("")
        
        # Add file context for the top files
        if context['files']:
            prompt_parts.append("\nRelevant Files:")
            for file_path, chunks in context['files'].items():
                prompt_parts.append(f"### File: {file_path}")
                # Include only the chunk contents
                for chunk in chunks:
                    prompt_parts.append(f"- {chunk['type']}:")
                    prompt_parts.append(chunk['content'])
                prompt_parts.append("")
        
        prompt_parts.append("\nProvide a comprehensive answer with code examples when applicable:")
        return '\n'.join(prompt_parts)
    
    def _call_llm(self, prompt: str) -> str:
        """Call the language model"""
        # response = openai.ChatCompletion.create(
        #     model="gpt-3.5-turbo",
        #     messages=[
        #         {"role": "system", "content": "You are an expert Android developer assistant."},
        #         {"role": "user", "content": prompt}
        #     ],
        #     temperature=0.7,
        #     max_tokens=1500
        # )
        # return response.choices[0].message.content

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        outputs = self.model.generate(**inputs, max_new_tokens=140)
        return self.tokenizer.decode(outputs[0])
