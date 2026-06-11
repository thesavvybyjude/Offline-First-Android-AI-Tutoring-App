"""
LLM Inference Engine
Uses llama-cpp-python for on-device text generation with Phi-3 Mini
"""

import os
from typing import Optional, Generator, Dict
from llama_cpp import Llama
from jinja2 import Template


class InferenceEngine:
    """LLM inference engine using llama-cpp-python"""
    
    def __init__(self, model_path: str = "models/phi-3-mini-q4_k_m.gguf",
                 n_ctx: int = 2048, n_gpu_layers: int = 0):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.model = None
        self.prompt_template = self._get_default_prompt_template()
    
    def _get_default_prompt_template(self) -> str:
        """Default prompt template for Phi-3"""
        return """<|system|>
You are a helpful AI tutor for Nigerian students studying NERDC/WAEC curriculum. 
Provide clear, educational answers appropriate for the student's grade level.
Use simple language and explain concepts step by step.
<|user|>
{% if context %}
Context information:
{{ context }}

{% endif %}
Student Question: {{ query }}

Student Level: {{ grade_level }}

Please provide a helpful answer:
<|assistant|>"""
    
    def load_model(self):
        """Load the LLM model"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        print(f"Loading model from {self.model_path}...")
        self.model = Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_gpu_layers=self.n_gpu_layers,
            verbose=False
        )
        print("Model loaded successfully")
    
    def generate(self, query: str, context: str = "", 
                 grade_level: str = "SS1", max_tokens: int = 512,
                 temperature: float = 0.7, stream: bool = False) -> str:
        """
        Generate response to student query
        query: Student's question
        context: Retrieved context from RAG
        grade_level: Student's grade level (SS1, SS2, SS3)
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0-1.0)
        stream: Whether to stream tokens
        """
        if self.model is None:
            self.load_model()
        
        # Build prompt using template
        template = Template(self.prompt_template)
        prompt = template.render(
            context=context,
            query=query,
            grade_level=grade_level
        )
        
        if stream:
            return self._stream_generate(prompt, max_tokens, temperature)
        else:
            return self._generate(prompt, max_tokens, temperature)
    
    def _generate(self, prompt: str, max_tokens: int, 
                  temperature: float) -> str:
        """Non-streaming generation"""
        output = self.model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["<|user|>", "<|system|>"],
            echo=False
        )
        
        return output['choices'][0]['text'].strip()
    
    def _stream_generate(self, prompt: str, max_tokens: int, 
                        temperature: float) -> Generator[str, None, None]:
        """Streaming generation"""
        stream = self.model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["<|user|>", "<|system|>"],
            echo=False,
            stream=True
        )
        
        for chunk in stream:
            text = chunk['choices'][0]['text']
            if text:
                yield text
    
    def set_prompt_template(self, template: str):
        """Set custom prompt template"""
        self.prompt_template = template
    
    def generate_flashcard(self, chunk_text: str, subject: str) -> Dict[str, str]:
        """
        Generate a flashcard from a knowledge chunk
        Returns dict with 'question' and 'answer'
        """
        if self.model is None:
            self.load_model()
        
        prompt = f"""<|system|>
You are an educational content creator. Create a flashcard from the given text.
<|user|>
Subject: {subject}

Text: {chunk_text}

Create a flashcard with:
1. A clear question
2. A concise answer

Format your response as:
Question: [your question]
Answer: [your answer]
<|assistant|>"""
        
        output = self.model(
            prompt,
            max_tokens=256,
            temperature=0.5,
            stop=["<|user|>", "<|system|>"],
            echo=False
        )
        
        response = output['choices'][0]['text'].strip()
        
        # Parse question and answer
        question = ""
        answer = ""
        
        for line in response.split('\n'):
            if line.lower().startswith('question:'):
                question = line.replace('Question:', '').replace('question:', '').strip()
            elif line.lower().startswith('answer:'):
                answer = line.replace('Answer:', '').replace('answer:', '').strip()
        
        return {
            'question': question,
            'answer': answer
        }


if __name__ == "__main__":
    # Example usage
    engine = InferenceEngine()
    
    # Generate response
    query = "What is the process of photosynthesis?"
    context = "Photosynthesis is the process by which plants convert sunlight into energy."
    
    print("Generating response...")
    response = engine.generate(query, context, grade_level="SS1")
    print(f"\nResponse:\n{response}")
