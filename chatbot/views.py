from django.shortcuts import render, redirect
from django.http import JsonResponse
import google.generativeai as genai
from django.contrib import auth
from django.contrib.auth.models import User
from .models import Chat
from django.utils import timezone
from cryptography.fernet import Fernet

# Configure the Gemini API
genai.configure(api_key="GEMINI_API_KEY")

# Create the model configuration
generation_config = {
    "temperature": 0,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction="You are an expert at giving therapy, let's say you're a psychiatrist, and you deal with people with mental health issues. Your task is to engage in conversations about stress, depression, mental health issues and provide appropriate solutions e.g., When a user mentions anxiety, suggest deep breathing exercises and affirmations. Ask questions so that you can better understand the user and improve their mood. Remember to use a polite tone that aligns with the user's mood and you can use any language or the one that user prompts you with...",
)

# Generate a key for encryption
key = Fernet.generate_key()
cipher = Fernet(key)

# Function to encrypt the message
def encrypt_message(message):
    encrypted_message = cipher.encrypt(message.encode('utf-8')).decode('utf-8')
    return encrypted_message

# Function to decrypt the message
def decrypt_message(encrypted_message):
    decrypted_message = cipher.decrypt(encrypted_message.encode('utf-8')).decode('utf-8')
    return decrypted_message

# Function to ask Gemini and get a response
def ask_gemini(message):
    chat_session = model.start_chat()
    response = chat_session.send_message(message)
    model_response = response.text
    return model_response

def chatbot(request):
    chats = Chat.objects.filter(user=request.user).order_by('created_at')
    
    if request.method == 'POST':
        message = request.POST.get('message', '')
        response = ask_gemini(message)
        
        # Encrypt the message and response
        encrypted_message = encrypt_message(message)
        encrypted_response = encrypt_message(response)
        
        # Save the chat to the database
        chat = Chat(user=request.user, message=encrypted_message, response=encrypted_response, created_at=timezone.now())
        chat.save()

        # Return the response as JSON
        return JsonResponse({'message': message, 'response': response})
    
    # Decrypt the chats for display
    decrypted_chats = []
    for chat in chats:
        decrypted_message = decrypt_message(chat.message)
        decrypted_response = decrypt_message(chat.response)
        decrypted_chats.append({'message': decrypted_message, 'response': decrypted_response})
    
    # Render the chatbot template for GET requests
    return render(request, 'chatbot.html', {'chats': decrypted_chats})

def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = auth.authenticate(request, username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return redirect('chatbot')
        else:
            error_message = "Invalid credentials"
            return render(request, 'login.html', {'error_message': error_message})
    else:
        return render(request, 'login.html')
  
def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        if password1 == password2:
            try:
                user = User.objects.create_user(username=username, email=email, password=password1)
                user.save() 
                auth.login(request, user)
                return redirect('chatbot')  
            except:
                error_message = "Username already exists"
                return render(request, 'register.html', {'error_message': error_message})
        else:
            error_message = "Passwords do not match"
            return render(request, 'register.html', {'error_message': error_message})
    else:
        return render(request, 'register.html')

def logout(request):
    if request.method == 'POST':
        auth.logout(request)
        return render(request, 'logout.html')
