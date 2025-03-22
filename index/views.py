import os
import json
import logging
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from dotenv import load_dotenv
from openai import OpenAI, APIError
from django.views.generic import CreateView
from django.urls import reverse_lazy
from .models import ChatSession, ChatMessage

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IndexView(LoginRequiredMixin, View):
    # Load environment variables only once when the class is defined
    load_dotenv()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize OpenAI client securely
        try:
            self.client = OpenAI(api_key=os.getenv('omar_ai'))
        except Exception as e:
            logger.error(f"OpenAI Client Initialization Error: {e}")
            self.client = None

    def get(self, request):
        if not self.client:
            return render(request, 'index.html', context={'error': 'OpenAI client not initialized'})

        try:
            # Get or create chat session for the current user
            chat_session, created = ChatSession.objects.get_or_create(
                user=request.user,
                defaults={'last_active': timezone.now()}
            )

            if created:
                # Initial AI greeting
                completion = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{
                        "role": "system",
                        "content": "Greeting Message!"
                    }],
                    max_tokens=50
                )

                greeting_response = completion.choices[0].message.content.strip()

                # Save AI greeting
                ChatMessage.objects.create(
                    session=chat_session,
                    content=greeting_response,
                    role='ai'
                )

            # Get all messages for current session
            messages = chat_session.messages.all()
            return render(request, 'index.html', context={
                'messages': messages,
                'chat_session': chat_session
            })

        except Exception as e:
            logger.error(f"Error in get: {str(e)}")
            return render(request, 'index.html', context={'error': 'Failed to load chat.'})


        except APIError as api_error:
            logger.error(f"OpenAI API Error: {api_error}")
            return render(request, 'index.html', context={'error': 'Failed to Work Correctly.'})

    def post(self, request):
        """
        Handle chat interactions with improved error handling and validation
        """
        def map_role_to_openai(db_role):
            return 'assistant' if db_role == 'ai' else 'user'

        try:
            # Parse JSON data safely
            data = json.loads(request.body)

            chat_session = ChatSession.objects.get(user=request.user)
            chat_session.last_active = timezone.now()
            chat_session.save()

            # Get user message from request
            user_message = data.get('message', '').strip()
            if not user_message:
                return JsonResponse({'error': 'Message cannot be empty'}, status=400)

            # Save user message
            ChatMessage.objects.create(
                session=chat_session,
                content=user_message,
                role='user'
            )

            # Get conversation history for context
            conversation_history = [
                {"role": map_role_to_openai(msg.role), "content": msg.content}
                for msg in chat_session.messages.order_by('timestamp')
            ]

            # Get AI response
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=conversation_history + [{"role": "user", "content": user_message}],
                max_tokens=300
            )

            ai_response = completion.choices[0].message.content.strip()

            # Save AI response
            ai_message = ChatMessage.objects.create(
                session=chat_session,
                content=ai_response,
                role='ai'
            )

            return JsonResponse({
                'bot_response': ai_response,
                'timestamp': ai_message.timestamp.isoformat()
            })



        except APIError as api_error:
                logger.error(f"OpenAI API Error: {api_error}")
                return JsonResponse({"error": "Failed to generate response"}, status=500)

        except json.JSONDecodeError:
            logger.warning("Invalid JSON data received")
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({"error": "An unexpected error occurred"}, status=500)


class SignUpView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'signup.html'


