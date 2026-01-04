import os
import frappe
import openai
import anthropic

class LLMAdapter:
    def __init__(self, provider=None):
        self.provider = provider or frappe.conf.get("ai_provider", "openai")
        self.api_key = frappe.conf.get(f"{self.provider}_api_key")

    def generate_soap_notes(self, transcript_text):
        """
        Generates structured SOAP notes from a consultation transcript.
        """
        prompt = f"""
        You are a medical transcription assistant. Based on the following transcript of a doctor-patient 
        consultation, generate a structured SOAP (Subjective, Objective, Assessment, Plan) note.
        
        Transcript:
        {transcript_text}
        
        Format the output as a JSON object with keys: subjective, objective, assessment, plan.
        """
        
        if self.provider == "openai":
            return self._call_openai(prompt)
        elif self.provider == "anthropic":
            return self._call_anthropic(prompt)
        else:
            return None

    def _call_openai(self, prompt):
        client = openai.OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

    def _call_anthropic(self, prompt):
        client = anthropic.Anthropic(api_key=self.api_key)
        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content
