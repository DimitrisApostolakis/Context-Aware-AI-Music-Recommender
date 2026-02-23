import spotipy
from spotipy.oauth2 import SpotifyOAuth

class User():
    
    def __init__(self, config):
        
        self.scopes = [
            "user-read-playback-state",
            "user-modify-playback-state",
            "user-read-currently-playing",
            "user-read-playback-position",
            "user-read-recently-played",
            "user-top-read",
            "user-library-read",
            "playlist-read-private",
            "playlist-read-collaborative",
            "playlist-modify-private",
            "playlist-modify-public"
        ]
        
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=config["CLIENT_ID"],
                                               client_secret=config["CLIENT_SECRET"],
                                               redirect_uri=config["URL"],
                                               scope=self.scopes))
        
        self.name = self.sp.current_user()["display_name"]
        
        self.top_tracks = self.extract_info(max_items=30)
        self.top_artists = self.extract_info(current_type="artists", max_items=15)
        self.playlists = self.extract_info(current_type="playlists", max_items=10)
        
    
    def __str__(self):
        
        return f"Account: {self.name}\nTop Artists: {len(self.top_artists)} retrieved\nTop Tracks: {len(self.top_tracks)} retrieved\nPlaylists: {len(self.playlists)} retrieved"
    
    def extract_info(self, current_type="tracks", max_items=50):
        d = {}
        try:
            if current_type == "tracks":
                itr = self.sp.current_user_top_tracks(limit=20, time_range="medium_term")
            elif current_type == "artists":
                itr = self.sp.current_user_top_artists(limit=20, time_range="medium_term")
            elif current_type == "playlists":
                itr = self.sp.current_user_playlists(limit=50)
            else:
                raise ValueError(f"Invalid type: {current_type}")
            while itr:
                for item in itr["items"]:
                    uri = item["uri"]
                    id = uri.split(":")[2]
                    name = item["name"]
                    
                    context_info = ""
                    
                    if current_type == "tracks":
                        context_info = item["artists"][0]["name"]
                    elif current_type == "playlists":
                        context_info = item.get("description", "")
                    
                    d[id] = {"name": name, "uri": uri, "context": context_info}
                    
                    if len(d) >= max_items:
                        return d
                    
                if itr["next"]:
                    itr = self.sp.next(itr)
                else:
                    itr = None
        except spotipy.exceptions.SpotifyException as e:
            print(f"Spotify API Error: {e}")
            return d
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return d
                
        return d
    
    def get_llm_context(self):
        context_str = f"{self.name}'s music profile\n\n"
        
        context_str += "Favorite Artists\n"
        for id, data in self.top_artists.items():
            context_str += f"- {data['name']}\n"
            
        context_str += f"\n{self.name}'s Playlists\n"
        for id, data in self.playlists.items():
            desc = f" -Vibe: {data['context']}" if data['context'] else ""
            context_str += f"- {data['name']}{desc}\n"
            
        context_str += "\n Favorite Songs\n"
        for id, data in self.top_tracks.items():
            context_str += f"- {data['name']} by {data['context']}\n"
            
        return context_str
            
    def prompt_engineering(self, user_input):
        master_prompt = f""" You are an AI Music Curator. Your goal is to recommend 4 songs based on the mood of the user AND his music taste.

        {self.get_llm_context()}

        The user's request/mood is: "{user_input}"

        INSTRUCTIONS:
        1. Understand the feeling and the rythm needed.
        2. Recommend 2 songs which suit the profile of the user and 2 new songs (discovery)
        3. ANSWER ONLY IN JSON FORMAT. Don't write any else, only the JSON format in this exact form:


        {{
        "detected_mood": "Description of the mood with 2-3 words",
        "recommendations": [
            {{
            "title": "Song name",
            "artist": "Arstis name",
            "reason": "Why do you recommend it based on the mood"
            }}
        ]
        }}
        
        """
        
        return master_prompt