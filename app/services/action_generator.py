"""
Action Generator Service

Generates ready-to-use action links and templates for tasks.
Supports: Google Search, Email Drafts, WhatsApp Messages, AI Prompts
"""

from typing import Dict, Optional
from urllib.parse import quote_plus


class ActionGenerator:
    """Generates ready-to-use action links and templates."""

    @staticmethod
    def generate_map_link(location: str, query: str = "") -> Dict[str, str]:
        """
        Generate Google Maps URL.

        Args:
            location: The name of the place
            query: Specific search query for the area

        Returns:
            Dict with location details and maps URL
        """
        search_term = query or location
        encoded_query = quote_plus(search_term)
        return {
            "location": location,
            "query": search_term,
            "url": f"https://www.google.com/maps/search/?api=1&query={encoded_query}",
        }

    @staticmethod
    def generate_google_search(query: str) -> Dict[str, str]:
        """
        Generate Google search URL.

        Args:
            query: Search query string

        Returns:
            Dict with query and URL
        """
        encoded_query = quote_plus(query)
        return {
            "query": query,
            "url": f"https://www.google.com/search?q={encoded_query}",
        }

    @staticmethod
    def generate_email_draft(
        to: str, name: str = "", subject: str = "", body: str = ""
    ) -> Dict[str, str]:
        """
        Generate email draft with mailto link.

        Args:
            to: Recipient email address
            name: Recipient name (optional)
            subject: Email subject
            body: Email body template

        Returns:
            Dict with email details and mailto link
        """
        encoded_subject = quote_plus(subject)
        encoded_body = quote_plus(body)
        mailto_link = f"mailto:{to}?subject={encoded_subject}&body={encoded_body}"

        return {
            "to": to,
            "name": name,
            "subject": subject,
            "body": body,
            "mailto_link": mailto_link,
        }

    @staticmethod
    def generate_whatsapp_message(
        phone: str, name: str = "", message: str = ""
    ) -> Dict[str, str]:
        """
        Generate WhatsApp deep link.

        Args:
            phone: Phone number (with country code)
            name: Contact name (optional)
            message: Pre-filled message template

        Returns:
            Dict with WhatsApp details and deep link
        """
        # Clean phone number (remove spaces, dashes, parentheses)
        clean_phone = "".join(filter(str.isdigit, phone))
        encoded_message = quote_plus(message)

        # WhatsApp deep link format
        deeplink = f"https://wa.me/{clean_phone}?text={encoded_message}"

        return {"phone": phone, "name": name, "message": message, "deeplink": deeplink}

    @staticmethod
    def generate_ai_prompt(
        model: str,
        task_description: str,
        context: str = "",
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Generate optimized AI prompt.

        Args:
            model: AI model name (gemini, chatgpt, claude, gpt-4)
            task_description: Task description
            context: Additional context from note
            custom_prompt: Optional custom prompt from LLM

        Returns:
            Dict with model, prompt, and chat URL
        """
        model_lower = model.lower()

        # Use custom prompt if provided, else use template
        if custom_prompt:
            prompt = custom_prompt
        else:
            # Prompt templates optimized for each model
            prompt_templates = {
                "gemini": f"Help me with this task: {task_description}\n\nContext: {context}",
                "chatgpt": f"I need assistance with: {task_description}\n\nAdditional context: {context}",
                "gpt-4": f"I need assistance with: {task_description}\n\nAdditional context: {context}",
                "claude": f"Task: {task_description}\n\nBackground: {context}\n\nPlease provide a detailed approach.",
            }
            prompt = prompt_templates.get(model_lower, prompt_templates["chatgpt"])

        # Chat URLs for each model
        chat_urls = {
            "gemini": "https://gemini.google.com/",
            "chatgpt": "https://chat.openai.com/",
            "gpt-4": "https://chat.openai.com/?model=gpt-4",
            "claude": "https://claude.ai/",
        }

        return {
            "model": model,
            "prompt": prompt,
            "chat_url": chat_urls.get(model_lower, "https://chat.openai.com/"),
        }
