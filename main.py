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
        print(f"Reason: {track['reason']}")
    
    answer = input("Do you want to make a playlist[y/N]: ").lower()
    while answer not in ["y", "n", ""]:
        answer = input("Invalid answer, please try again [y/N]: ").lower()
    
    if answer == "y":
        name = input("Give a name: ")
        new_playlist_id = myUser.create_playlist(name, description=f"Mood: {recommendations['detected_mood']}.")
        track_uri = [track["uri"] for track in recommendations["recommendations"]]
        myUser.push_track(new_playlist_id, track_uri)
        
    
        
mainApp(config)