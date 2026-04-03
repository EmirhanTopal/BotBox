"""LLM integration service"""

import requests
import json
import logging
import os

logger = logging.getLogger(__name__)

class LLMService:
    """
    Integration with Ollama LLM service
    """
    
    def __init__(self):
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://ollama:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'mistral')
    
    def generate_answer(self, question: str, context: dict) -> dict:
        """
        Generate answer using LLM
        """
        
        # Build prompt with context
        prompt = self._build_prompt(question, context)
        
        try:
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'text': result.get('response', '').strip(),
                    'sources': context.get('sources', []),
                    'confidence': 0.8
                }
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return self._fallback_answer(question, context)
        
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ollama service")
            return self._fallback_answer(question, context)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return self._fallback_answer(question, context)
    
    def _build_prompt(self, question: str, context: dict) -> str:
        """Build prompt with context"""
        
        context_text = "Use the following information to answer the question:\n\n"
        
        if context.get('general_info'):
            info = context['general_info']
            context_text += f"University: {info.get('title', '')}\n"
            context_text += f"Description: {info.get('description', '')}\n"
            if info.get('phone'):
                context_text += f"Contact: {info.get('phone', '')}\n"
            context_text += "\n"
        
        if context.get('programs'):
            context_text += "Available Programs:\n"
            for prog in context['programs'][:3]:
                context_text += f"- {prog['name']} ({prog['level']})\n"
            context_text += "\n"
        
        if context.get('courses'):
            context_text += "Available Courses:\n"
            for course in context['courses'][:3]:
                context_text += f"- {course['code']}: {course['name']}\n"
            context_text += "\n"
        
        if context.get('departments'):
            context_text += "Departments:\n"
            for dept in context['departments'][:3]:
                context_text += f"- {dept['name']}: {dept['email']}\n"
            context_text += "\n"
        
        prompt = f"""You are a helpful assistant for Acibadem University.

{context_text}

Question: {question}

Answer: Be helpful, accurate, and concise. If you don't know the answer based on the provided context, say so."""
        
        return prompt
    
    def _fallback_answer(self, question: str, context: dict) -> dict:
        """Fallback answer when LLM is unavailable"""
        
        if context.get('programs'):
            return {
                'text': f"I found {len(context['programs'])} relevant programs. "
                        f"The programs available are: {', '.join([p['name'] for p in context['programs'][:3]])}",
                'sources': context.get('sources', []),
                'confidence': 0.5
            }
        elif context.get('general_info'):
            return {
                'text': f"Acibadem University is located in Istanbul, Turkey. "
                        f"For more information, please contact: {context['general_info'].get('phone', 'N/A')}",
                'sources': context.get('sources', []),
                'confidence': 0.5
            }
        else:
            return {
                'text': "I don't have enough information to answer this question. "
                        "Please try asking about programs, departments, or courses.",
                'sources': [],
                'confidence': 0.0
            }