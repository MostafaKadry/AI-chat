import os
import json
import logging
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.contrib.auth.forms import UserCreationForm



from dotenv import load_dotenv
from openai import OpenAI, APIError
from .models import ChatSession, ChatMessage

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IndexView(LoginRequiredMixin, View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if not api_key:
            logger.error("OpenAI API key not found in environment variables")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=api_key)
            except Exception as e:
                logger.error(f"OpenAI Client Initialization Error: {e}")
                self.client = None
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        api_key = os.getenv('iti_open_ai_secret_key')
        if not api_key:
            logger.error("OpenAI API key not found")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=api_key)
                # Create or reuse an Assistant (do this once, e.g., in setup or first call)
                self.assistant = self.client.beta.assistants.create(
                    name="Chat Assistant",
                    instructions="You are a helpful assistant that can summarize files and answer questions based on their content.",
                    model="gpt-4o-mini"  # Switch to "gpt-4o" for vision if needed
                )
                logger.info(f"Created Assistant: {self.assistant.id}")
            except Exception as e:
                logger.error(f"OpenAI Client/Assistant Initialization Error: {e}")
                self.client = None
                self.assistant = None
    def get(self, request):
        if not self.client:
            return render(request, 'index.html', context={'error': 'OpenAI client not initialized'})

        try:
            chat_session, created = ChatSession.objects.get_or_create(
                user=request.user,
                defaults={'last_active': timezone.now()}
            )

            if created:
                completion = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "Greeting Message!"}],
                    max_tokens=50
                )
                greeting_response = completion.choices[0].message.content.strip()
                ChatMessage.objects.create(
                    session=chat_session,
                    content=greeting_response,
                    role='ai'
                )

            messages = chat_session.messages.all()
            return render(request, 'index.html', context={
                'messages': messages,
                'chat_session': chat_session
            })

        except APIError as api_error:
            logger.error(f"OpenAI API Error: {api_error}")
            return render(request, 'index.html', context={'error': 'Failed to Work Correctly.'})
        except Exception as e:
            logger.error(f"Error in get: {str(e)}")
            return render(request, 'index.html', context={'error': 'Failed to load chat.'})

    def post(self, request):
        if not self.client:
            logger.error("OpenAI client not initialized")
            return JsonResponse({"error": "AI service unavailable"}, status=500)

        def map_role_to_openai(db_role):
            return 'assistant' if db_role == 'ai' else 'user'

        try:
            # Get or create chat session
            chat_session, created = ChatSession.objects.get_or_create(
                user=request.user,
                defaults={'last_active': timezone.now()}
            )
            if not created:
                chat_session.last_active = timezone.now()
                chat_session.save()

            # Get data from FormData
            user_message = request.POST.get('message', '').strip()
            file = request.FILES.get('file')

            if not user_message and not file:
                return JsonResponse({'error': 'Message or file required'}, status=400)

            # Save user message if provided
            if user_message:
                ChatMessage.objects.create(
                    session=chat_session,
                    content=user_message,
                    role='user'
                )

            # Handle file upload to OpenAI Files API
            file_content = None
            file_id = None
            if file:
                # Read file bytes and prepare for OpenAI
                file_bytes = file.read()  # Get raw bytes from Django file
                file_tuple = (file.name, file_bytes, file.content_type)  # (filename, bytes, mimetype)

                # Upload file to OpenAI
                file_obj = self.client.files.create(
                    file=file_tuple,
                    purpose="assistants"
                )
                file_id = file_obj.id
                logger.info(f"Uploaded file to OpenAI: {file_id}")

                # Retrieve file content (for text-based files)
                try:
                    file_data = self.client.files.content(file_id)
                    file_content = file_data.text if hasattr(file_data, 'text') else file_data.read().decode('utf-8', errors='ignore')
                except Exception as e:
                    logger.warning(f"Could not retrieve file content: {e}")
                    file_content = f"[Uploaded file: {file.name} ({file.content_type}) - content not directly readable]"

                # Save file reference/content in chat
                ChatMessage.objects.create(
                    session=chat_session,
                    content=f"Uploaded file: {file.name}\nContent: {file_content}",
                    role='user'
                )

            # Build conversation history
            conversation_history = [
                {"role": map_role_to_openai(msg.role), "content": msg.content}
                for msg in chat_session.messages.order_by('timestamp')
            ]

            # Construct AI prompt
            ai_prompt = []
            if user_message and file:
                ai_prompt.append({
                    "role": "user",
                    "content": f"{user_message}\n\nFile content: {file_content}"
                })
            elif user_message:
                ai_prompt.append({"role": "user", "content": user_message})
            elif file:
                ai_prompt.append({
                    "role": "user",
                    "content": f"I uploaded a file: {file.name}. Please describe or summarize its content.\n\nFile content: {file_content}"
                })

            # Get AI response
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=conversation_history + ai_prompt,
                max_tokens=300
            )
            ai_response = completion.choices[0].message.content.strip()

            # Save AI response
            ai_message = ChatMessage.objects.create(
                session=chat_session,
                content=ai_response,
                role='ai'
            )

            # Clean up: Delete the file from OpenAI
            if file_id:
                self.client.files.delete(file_id)
                logger.info(f"Deleted file from OpenAI: {file_id}")

            return JsonResponse({
                'bot_response': ai_response,
                'timestamp': ai_message.timestamp.isoformat()
            })

        except APIError as api_error:
            logger.error(f"OpenAI API Error: {api_error}")
            return JsonResponse({"error": "Failed to generate response"}, status=500)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({"error": str(e)}, status=500)
             


class SignUpView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'signup.html'


