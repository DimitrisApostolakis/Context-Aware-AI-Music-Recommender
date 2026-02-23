from spotify_client import User
from llm_client import LLM

from dotenv import dotenv_values

config = dotenv_values(".env")

def mainApp(config):
    
    myUser = User(config)
    llm = LLM(config)
    
    user_input = input("What's the mood today? ")
    
    prompt = myUser.prompt_engineering(user_input)
    
    recommendations = llm.get_response(prompt)
    
    print(f"\nMood Detected: {recommendations['detected_mood']}")
    for track in recommendations["recommendations"]:
        print(f"Track: {track['title']} - {track['artist']}")
        
mainApp(config)