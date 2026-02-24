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

    if not recommendations or "detected_mood" not in recommendations or "recommendations" not in recommendations:
        print("\nJSON file coundn't be parsed from the LLM.")
        return

    if isinstance(recommendations.get("recommendations"), list):
        myUser.ensure_recommendation_uris(recommendations["recommendations"])
    
    print(f"\nMood Detected: {recommendations['detected_mood']}")
    for track in recommendations["recommendations"]:
        print(f"Track: {track['title']} - {track['artist']}")
        print(f"Reason: {track['reason']}\n")
    
    answer = input("Do you want to make a playlist[y/N]: ").lower()
    while answer not in ["y", "n", ""]:
        answer = input("Invalid answer, please try again [y/N]: ").lower()
    
    if answer == "y":
        name = input("Give a name: ")
        new_playlist_id = myUser.create_playlist(name, description=f"Mood: {recommendations['detected_mood']}.")
        if not new_playlist_id:
            print("Couldn't create a Spotify playlist.")
            return
        track_uri = [track.get("uri") for track in recommendations["recommendations"] if track.get("uri")]
        if not track_uri:
            print("Didn't find any uri to add songs.")
            return
        myUser.push_track(new_playlist_id, track_uri)
        
    
        

if __name__ == "__main__":
    mainApp(config)