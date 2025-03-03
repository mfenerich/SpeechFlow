import os
from dotenv import load_dotenv
from speechflow.app.main_app import MainApp

# Load environment variables
load_dotenv(override=True)

if __name__ == "__main__":
    # Display service configuration
    print(f"Using Transcription Service: {os.getenv('TRANSCRIPTION_SERVICE', 'Not Set')}")
    print(f"Using Chat Service: {os.getenv('CHAT_SERVICE', 'Not Set')}")
    
    # Initialize and run app
    app = MainApp()
    app.run()