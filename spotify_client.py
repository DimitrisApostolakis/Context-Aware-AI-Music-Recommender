import spotipy
from spotipy.oauth2 import SpotifyOAuth

import requests
import random
import time

import os, json

from typing import *

CACHE_FILE = "user_cache.json"

class User():
    
    def __init__(self, config:dict[str, str]) -> str:
        
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
        
        self.token = self.sp.auth_manager.get_access_token(as_dict=False)

        self.user_name = self.sp.current_user()["display_name"]
        self.user_id = self.sp.current_user()["id"]
        
        self.top_tracks = self.extract_info(max_items=30)
        self.top_artists = self.extract_info(current_type="artists", max_items=15)
        self.playlists = self.extract_info(current_type="playlists", max_items=10)
        
    
    def __str__(self) -> str:
        
        return f"Account: {self.user_name}\nTop Artists: {len(self.top_artists)} retrieved\nTop Tracks: {len(self.top_tracks)} retrieved\nPlaylists: {len(self.playlists)} retrieved."
    
    def load_data(self) -> None:
        if os.path.exists(CACHE_FILE):
            print("Loading data from cache...")
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            print("Fetching data from Spotify API...")
            data = {
                "top_tracks": self.extract_info("tracks", max_items=30),
                "top_artists": self.extract_info("artists", max_items=15),
                "playlists": self.extract_info("playlists", max_items=10)
            }
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.top_tracks = data["top_tracks"]
        self.top_artists = data["top_artists"]
        self.playlists = data["playlists"]
        
        
    def extract_info(self, current_type:str="tracks", max_items:int=50, random_samples:int=10, track_limit:int=20, artists_limit:int=20, playlists_limit:int=20) -> Dict[str, Any]:
        d = {}
        try:
            if current_type == "tracks":
                itr = self.sp.current_user_top_tracks(limit=track_limit, time_range="medium_term")
            elif current_type == "artists":
                itr = self.sp.current_user_top_artists(limit=artists_limit, time_range="medium_term")
            elif current_type == "playlists":
                itr = self.sp.current_user_playlists(limit=playlists_limit)
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
                        playlist_tracks = []
                        context_info = item.get("description", "")

                        tracks = self.get_tracks_from_playlists(id, max_items)
                        if len(tracks) == 0:
                            print(f"No tracks available for playlist {name}")
                            continue

                        sample_size = min(random_samples, len(tracks))
                        random_tracks = random.sample(tracks, sample_size)
                        playlist_tracks = [
                            t["name"] + " - " + t["artists"][0]["name"]
                            for t in random_tracks if t and t.get("artists")
                        ]

                        d[id] = {
                            "name": name,
                            "uri": uri,
                            "description": context_info,
                            "playlist_tracks": playlist_tracks
                        }
                        continue  

                    d[id] = {
                        "name": name,
                        "uri": uri,
                        "context": context_info
                    }

                    if len(d) >= max_items:
                        return d

                itr = self.sp.next(itr) if itr["next"] else None

        except spotipy.exceptions.SpotifyException as e:
            print(f"Spotify API Error: {e}")
            return d
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return d

        return d

    
    def get_tracks_from_playlists(self, playlist_id:str, max_items:int) -> List[Dict[str, Any]]:
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/items" # Spotipy didn't change the endpoints 
        headers = {
                "Authorization": f"Bearer {self.token}"
            }
        params = {
            "limit": max_items,
            "offset": 0
        }
        
        tracks = []
        while url:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 1))
                print(f"Rate limited, retrying after {retry_after}s")
                time.sleep(retry_after + 0.5)
                continue
            elif response.status_code != 200:
                print("Skipping playlist due to error: ", response.status_code)
                return []
            
            data = response.json()
            tracks.extend([item["track"] for item in data["items"] if item["track"]])
            url = data["next"]
            params = None
            time.sleep(0.2)
            
        return tracks
        
    
    def get_llm_context(self) -> str:
        context_str = f"{self.name}'s music profile\n\n"
        
        context_str += "Favorite Artists\n"
        for id, data in self.top_artists.items():
            context_str += f"- {data['name']}\n"
            
        context_str += f"\n{self.name}'s Playlists\n"
        for id, data in self.playlists.items():
            desc = f" -Vibe: {data['description']}" if data['description'] else ""
            context_str += f"- {data['name']}{desc}\n"
            context_str += "Tracks in playlist:\n"
            for track in data["playlist_tracks"]:
                context_str += f"- {track}\n"
            
        context_str += "\n Favorite Songs\n"
        for id, data in self.top_tracks.items():
            context_str += f"- {data['name']} by {data['context']}\n"
            
        return context_str
            
    def prompt_engineering(self, user_input:str) -> str:
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
            "uri": "Song uri",
            "reason": "Why do you recommend it based on the mood"
            }}
        ]
        }}
        
        """
        
        return master_prompt
    
    def create_playlist(self, playlist_name:str, description:str, wantID:bool = True) -> Optional[str]:
        desc_text = (description or "") + "\nPlaylist based on the sentiment recommendation app."
        new_playlist = self.sp.user_playlist_create(self.user_id, name=playlist_name or "AI-Generated Playlist", public=True, collaborative=False, description=desc_text)
        if wantID:
            return new_playlist["id"]
        else:
            new_playlist
    
    def push_track(self, playlist_id:str, song_uri: List[str]) -> Dict[str, Any]:
        self.sp.playlist_add_items(playlist_id, song_uri)