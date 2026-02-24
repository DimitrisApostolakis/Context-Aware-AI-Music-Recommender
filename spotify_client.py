import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import MemoryCacheHandler

import requests
import random
import time

import os, json
import re

from typing import *

CACHE_FILE = "user_cache.json"
TOKEN_CACHE_FILE = ".token_cache"

class User():
    
    def __init__(self, config:dict[str, str]) -> None:
        
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
            "playlist-modify-public",
        ]
        scope_str = " ".join(self.scopes)
        print(scope_str)

        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=config["CLIENT_ID"],
                client_secret=config["CLIENT_SECRET"],
                redirect_uri=config["URL"],
                scope=scope_str,
                # cache_handler=MemoryCacheHandler(),
                show_dialog=True,
                cache_path=TOKEN_CACHE_FILE
            )
        )

        self.user_name = self.sp.me()["display_name"]
        self.user_id = self.sp.me()['id']
        
        print(self.user_name, self.user_id)


        self.top_tracks: Dict[str, Any] = {}
        self.top_artists: Dict[str, Any] = {}
        self.playlists: Dict[str, Any] = {}

        self.load_data()
        
    
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

    def _get_access_token(self) -> str:
        token = self.sp.auth_manager.get_access_token(as_dict=False)
        if isinstance(token, dict):
            return token.get("access_token", "")
        return token or ""
    
    def get_tracks_from_playlists(self, playlist_id:str, max_items:int) -> List[Dict[str, Any]]:
        limit = min(100, max(1, int(max_items)))
        offset = 0
        tracks: List[Dict[str, Any]] = []

        while True:
            try:
                data = self.sp.playlist_items(
                    playlist_id,
                    limit=limit,
                    offset=offset,
                    additional_types=("track", "episode"),
                )
            except spotipy.exceptions.SpotifyException as e:
                if getattr(e, "http_status", None) == 429:
                    retry_after = 1
                    headers = getattr(e, "headers", None) or {}
                    if isinstance(headers, dict):
                        retry_after = int(headers.get("Retry-After", 1))
                    print(f"Rate limited, retrying after {retry_after}s")
                    time.sleep(retry_after + 0.5)
                    continue

                if getattr(e, "http_status", None) == 403:
                    print("Skipping playlist due to error: 403 (forbidden)")
                    return []

                print(f"Spotify API Error (playlist_items): {e}")
                return []
            except Exception as e:
                print(f"An unexpected error occurred (playlist_items): {e}")
                return []

            items = (data or {}).get("items", [])
            for item in items:
                track_obj = None
                if isinstance(item, dict):
                    track_obj = item.get("track")
                if isinstance(track_obj, dict) and track_obj.get("type") == "track":
                    tracks.append(track_obj)
                    if len(tracks) >= max_items:
                        return tracks

            if not (data or {}).get("next"):
                return tracks

            offset += limit
            time.sleep(0.2)
        
    
    def get_llm_context(self) -> str:
        context_str = f"{self.user_name}'s music profile\n\n"
        
        context_str += "Favorite Artists\n"
        for id, data in self.top_artists.items():
            context_str += f"- {data['name']}\n"
            
        context_str += f"\n{self.user_name}'s Playlists\n"
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
        3. ANSWER ONLY IN JSON FORMAT. Don't write anything else, only the JSON format in this exact form (exactly 4 items in recommendations).
        4. If you don't know the Spotify URI, set "uri" to an empty string.


        {{
        "detected_mood": "Description of the mood with 2-3 words",
        "recommendations": [
            {{
            "title": "Song name",
            "artist": "Arstis name",
            "uri": "Song uri",
            "reason": "Why do you recommend it based on the mood"
            }},
            {{
            "title": "Song name",
            "artist": "Arstis name",
            "uri": "Song uri",
            "reason": "Why do you recommend it based on the mood"
            }},
            {{
            "title": "Song name",
            "artist": "Arstis name",
            "uri": "Song uri",
            "reason": "Why do you recommend it based on the mood"
            }},
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

    def _is_track_uri(self, uri: Optional[str]) -> bool:
        if not uri or not isinstance(uri, str):
            return False
        return bool(re.match(r"^spotify:track:[A-Za-z0-9]+$", uri.strip()))

    def find_track_uri(self, title: str, artist: str = "") -> Optional[str]:
        title = (title or "").strip()
        artist = (artist or "").strip()
        if not title:
            return None

        if artist:
            query = f"track:{title} artist:{artist}"
        else:
            query = f"track:{title}"

        try:
            results = self.sp.search(q=query, type="track", limit=1)
            items = (results or {}).get("tracks", {}).get("items", [])
            if not items:
                return None
            return items[0].get("uri")
        except spotipy.exceptions.SpotifyException as e:
            print(f"Spotify API Error (search): {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred (search): {e}")
            return None

    def ensure_recommendation_uris(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for rec in recommendations:
            if not isinstance(rec, dict):
                continue
            if self._is_track_uri(rec.get("uri")):
                continue
            uri = self.find_track_uri(rec.get("title", ""), rec.get("artist", ""))
            if uri:
                rec["uri"] = uri
        return recommendations
    
    def create_playlist(self, playlist_name:str, description:str, wantID:bool = True) -> Optional[str]:
        desc_text = (description or "") + "\nPlaylist based on the sentiment recommendation app."
        try:
            new_playlist = self.sp.user_playlist_create(
                self.user_id,
                name=playlist_name or "AI-Generated Playlist",
                public=False,
                collaborative=False,
                description=desc_text,
            )
        except spotipy.exceptions.SpotifyException as e:
            print(f"Spotify API Error (create_playlist): {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred (create_playlist): {e}")
            return None

        playlist_id = new_playlist.get("id")
        return playlist_id if wantID else playlist_id
    
    def push_track(self, playlist_id:str, song_uri: List[str]) -> Dict[str, Any]:
        return self.sp.playlist_add_items(playlist_id, song_uri)