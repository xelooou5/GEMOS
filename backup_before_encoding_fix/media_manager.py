#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Media Manager (core/media_manager.py)
Manages audio and video playback, playlists, and media control.

Responsibilities
----------------
- Control media playback (play, pause, stop, volume).
- Manage simple playlists.
- Interact with underlying audio/video playback systems.
- Expose media control capabilities as tools for the LLM.
- Publish media-related events.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Awaitable

import simpleaudio as sa # Para reprodução simples de áudio
from pydub import AudioSegment # Para carregar e manipular arquivos de áudio
from pydub.playback import play # Funções de reprodução da pydub (bloqueante)

from core.plugins import BasePlugin, CommandExecutor, GEMVoiceAssistant
from core.notification_manager import NotificationManager, NOTIFICATION_INFO, NOTIFICATION_SUCCESS, NOTIFICATION_WARNING

# Forward declarations for type hinting
class EventManager:
    async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        pass

class TTSModule:
    async def speak(self, text: str) -> None:
        pass

class Storage:
    async def get_setting(self, key: str, default: Any = None) -> Any:
        pass
    async def set_setting(self, key: str, value: Any) -> bool:
        pass

# --- Dataclass para Item de Mídia ---
@dataclass
class MediaItem:
    path: Path
    title: str
    artist: Optional[str] = None
    album: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": str(self.path),
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MediaItem:
        return cls(
            path=Path(data["path"]),
            title=data["title"],
            artist=data.get("artist"),
            album=data.get("album"),
        )

# --- Media Manager como um Plugin ---
class MediaManager(BasePlugin):
    """
    Manages media playback and related functionalities for GEM OS.
    """
    STORAGE_PLAYLIST_KEY = "media_playlists"

    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("MediaManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.storage: Storage = gem_instance.storage
        self.tts_module: TTSModule = gem_instance.tts_module

        self._current_playback: Optional[sa.PlayObject] = None
        self._current_media_item: Optional[MediaItem] = None
        self._is_playing: bool = False
        self._is_paused: bool = False
        self._volume: float = 0.5 # Default volume (0.0 to 1.0)
        self._playback_future: Optional[asyncio.Future] = None # Para controlar a reprodução assíncrona

        self._playlist: List[MediaItem] = []
        self._playlist_index: int = -1
        self._shuffle: bool = False

        self._loaded_playlists: Dict[str, List[MediaItem]] = {} # {playlist_name: [MediaItem]}
        self._playlists_loaded = asyncio.Event() # Evento para sinalizar que as playlists foram carregadas

    async def initialize(self) -> None:
        """Loads playlists from storage and prepares the manager."""
        await self._load_playlists_from_storage()
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self.logger.info("MediaManager inicializado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event to gracefully stop media playback."""
        self.logger.info("Recebido GEM_SHUTDOWN. A parar a reprodução de mídia.")
        await self._stop_playback_internal()
        self.shutdown()

    async def _load_playlists_from_storage(self) -> None:
        """Loads saved playlists from persistent storage."""
        try:
            playlists_data = await self.storage.get_setting(self.STORAGE_PLAYLIST_KEY, {})
            for name, items_data in playlists_data.items():
                self._loaded_playlists[name] = [MediaItem.from_dict(item_dict) for item_dict in items_data]
            self.logger.info(f"Carregadas {len(self._loaded_playlists)} playlists do armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao carregar playlists do armazenamento: {e}", exc_info=True)
        finally:
            self._playlists_loaded.set()

    async def _save_playlists_to_storage(self) -> None:
        """Saves current playlists to persistent storage."""
        try:
            playlists_data_to_save = {}
            for name, items in self._loaded_playlists.items():
                playlists_data_to_save[name] = [item.to_dict() for item in items]
            await self.storage.set_setting(self.STORAGE_PLAYLIST_KEY, playlists_data_to_save)
            self.logger.debug(f"Salvas {len(self._loaded_playlists)} playlists para o armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao salvar playlists no armazenamento: {e}", exc_info=True)

    async def _play_media_item(self, media_item: MediaItem) -> Dict[str, Any]:
        """Internal method to handle playback of a single media item."""
        await self._stop_playback_internal() # Stop any current playback

        try:
            audio = AudioSegment.from_file(media_item.path)
            # Ajustar o volume
            if self._volume != 0.5: # 0.5 é o ponto médio para AudioSegment
                audio = audio + (20 * (self._volume - 0.5)) # Ajuste de dB, 20dB é aprox. 10x
            
            self.logger.info(f"A reproduzir: {media_item.title} ({media_item.path})")
            await self.event_manager.publish("MEDIA_STARTED", media_item.to_dict())
            await self.notification_manager.add_notification(
                f"A reproduzir: {media_item.title}", level=NOTIFICATION_INFO, vocalize=False
            )
            await self.tts_module.speak(f"A reproduzir {media_item.title}.")

            # simpleaudio é bloqueante, então executamos num thread separado
            # Usamos uma Future para poder cancelar/monitorar
            loop = asyncio.get_event_loop()
            self._playback_future = loop.run_in_executor(
                None, lambda: sa.play_buffer(audio.raw_data, audio.channels, audio.sample_width, audio.frame_rate)
            )
            self._current_media_item = media_item
            self._is_playing = True
            self._is_paused = False

            play_obj = await self._playback_future # Espera a PlayObject ser retornada
            self._current_playback = play_obj

            await asyncio.to_thread(self._wait_for_playback_completion, play_obj) # Wait for it to finish blocking

            self._is_playing = False
            self._current_playback = None
            self._current_media_item = None
            self.logger.info(f"Reprodução de {media_item.title} concluída.")
            await self.event_manager.publish("MEDIA_ENDED", {"item": media_item.to_dict()})

            # Auto-play next item in playlist if not stopped/paused
            if self._playlist and not self._is_paused and not self._playback_future.done(): # Check if not explicitly stopped
                next_item = self._get_next_playlist_item()
                if next_item:
                    asyncio.create_task(self._play_media_item(next_item))

            return {"success": True, "output": f"A reproduzir {media_item.title}", "error": None}

        except FileNotFoundError:
            error_msg = f"Ficheiro de mídia não encontrado: {media_item.path}"
            self.logger.error(error_msg)
            await self.tts_module.speak(error_msg)
            await self.notification_manager.add_notification(error_msg, level=NOTIFICATION_WARNING)
            return {"success": False, "output": "", "error": error_msg}
        except Exception as e:
            error_msg = f"Erro ao reproduzir {media_item.title}: {e}"
            self.logger.error(error_msg, exc_info=True)
            await self.tts_module.speak(error_msg)
            await self.notification_manager.add_notification(error_msg, level=NOTIFICATION_WARNING)
            return {"success": False, "output": "", "error": error_msg}

    def _wait_for_playback_completion(self, play_obj: sa.PlayObject):
        """Bloqueia até que o objeto de reprodução termine."""
        play_obj.wait_done()
        self.logger.debug("simpleaudio playback finished.")

    async def _stop_playback_internal(self) -> None:
        """Internal helper to stop playback gracefully."""
        if self._current_playback:
            self._current_playback.stop()
            self._current_playback = None
            self.logger.info("Reprodução de mídia parada internamente.")
        if self._playback_future and not self._playback_future.done():
            self._playback_future.cancel()
            self.logger.debug("Future de reprodução cancelada.")
            try:
                await self._playback_future # Aguarda para garantir que a tarefa de executor terminou
            except asyncio.CancelledError:
                pass # Esperado
        self._is_playing = False
        self._is_paused = False
        await self.event_manager.publish("MEDIA_STOPPED", {"item": self._current_media_item.to_dict() if self._current_media_item else None})


    def _get_next_playlist_item(self) -> Optional[MediaItem]:
        """Calcula o próximo item da playlist, considerando o shuffle."""
        if not self._playlist:
            return None
        
        if self._shuffle:
            self._playlist_index = random.randint(0, len(self._playlist) - 1)
        else:
            self._playlist_index = (self._playlist_index + 1) % len(self._playlist)
        
        return self._playlist[self._playlist_index]


    # --------------------------------------------------------------------- Commands

    async def _play_media_command(self, path: Optional[str] = None, playlist_name: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
        """
        Inicia a reprodução de um ficheiro de mídia ou de uma playlist.
        Se nenhum caminho for fornecido, retoma a reprodução atual ou toca o próximo item da playlist.
        """
        if self._is_paused and not path and not playlist_name and not title:
            return await self._resume_media_command()
        
        if path:
            media_path = Path(path)
            if not media_path.exists():
                message = f"Ficheiro de mídia não encontrado em: {path}"
                await self._speak_response(message)
                await self.notification_manager.add_notification(message, level=NOTIFICATION_WARNING)
                return {"success": False, "output": message, "error": "File not found"}
            
            item_title = title if title else media_path.stem
            media_item = MediaItem(path=media_path, title=item_title)
            self._playlist = [media_item] # Clear current playlist and add this one
            self._playlist_index = 0
            return await self._play_media_item(media_item)
        
        elif playlist_name:
            await self._playlists_loaded.wait()
            if playlist_name not in self._loaded_playlists:
                message = f"Playlist '{playlist_name}' não encontrada."
                await self._speak_response(message)
                await self.notification_manager.add_notification(message, level=NOTIFICATION_WARNING)
                return {"success": False, "output": message, "error": "Playlist not found"}
            
            self._playlist = list(self._loaded_playlists[playlist_name]) # Make a copy
            if self._shuffle:
                random.shuffle(self._playlist)
            self._playlist_index = 0
            
            if self._playlist:
                return await self._play_media_item(self._playlist[self._playlist_index])
            else:
                message = f"Playlist '{playlist_name}' está vazia."
                await self._speak_response(message)
                await self.notification_manager.add_notification(message, level=NOTIFICATION_WARNING)
                return {"success": False, "output": message, "error": "Empty playlist"}
        
        elif self._playlist and self._current_media_item: # Try to play next in current playlist
            next_item = self._get_next_playlist_item()
            if next_item:
                return await self._play_media_item(next_item)
            else:
                message = "Fim da playlist. Nenhuma mídia para reproduzir."
                await self._speak_response(message)
                return {"success": True, "output": message, "error": None}

        message = "Nenhum arquivo ou playlist especificada, e nada em reprodução ou pausado."
        await self._speak_response(message)
        return {"success": False, "output": message, "error": "No media specified"}

    async def _pause_media_command(self) -> Dict[str, Any]:
        """Pausa a reprodução de mídia atual."""
        if self._current_playback and self._is_playing and not self._is_paused:
            self._current_playback.pause()
            self._is_paused = True
            message = "Reprodução pausada."
            await self._speak_response(message)
            await self.event_manager.publish("MEDIA_PAUSED", {"item": self._current_media_item.to_dict() if self._current_media_item else None})
            return {"success": True, "output": message, "error": None}
        message = "Nenhuma mídia em reprodução para pausar."
        await self._speak_response(message)
        return {"success": False, "output": message, "error": "No media playing"}

    async def _resume_media_command(self) -> Dict[str, Any]:
        """Retoma a reprodução de mídia pausada."""
        if self._current_playback and self._is_paused:
            self._current_playback.play()
            self._is_paused = False
            message = "Reprodução retomada."
            await self._speak_response(message)
            await self.event_manager.publish("MEDIA_RESUMED", {"item": self._current_media_item.to_dict() if self._current_media_item else None})
            return {"success": True, "output": message, "error": None}
        message = "Nenhuma mídia pausada para retomar."
        await self._speak_response(message)
        return {"success": False, "output": message, "error": "No media paused"}

    async def _stop_media_command(self) -> Dict[str, Any]:
        """Para completamente a reprodução de mídia atual."""
        if self._is_playing or self._is_paused:
            await self._stop_playback_internal()
            message = "Reprodução de mídia parada."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_INFO)
            return {"success": True, "output": message, "error": None}
        message = "Nenhuma mídia em reprodução ou pausada para parar."
        await self._speak_response(message)
        return {"success": False, "output": message, "error": "No media playing/paused"}

    async def _set_volume_command(self, level: float) -> Dict[str, Any]:
        """Define o volume de reprodução (0.0 a 1.0)."""
        if not (0.0 <= level <= 1.0):
            message = "O nível de volume deve estar entre 0.0 e 1.0."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Invalid volume level"}
        
        self._volume = level
        message = f"Volume definido para {int(level * 100)}%."
        await self._speak_response(message)
        await self.event_manager.publish("MEDIA_VOLUME_CHANGED", {"level": level})
        # Note: Volume change on currently playing simpleaudio object requires re-creating AudioSegment
        # For simplicity, apply on next track or when playing.
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _current_media_status_command(self) -> Dict[str, Any]:
        """Reporta o status da mídia atual em reprodução."""
        if self._current_media_item:
            status = "reproduzindo" if self._is_playing else "pausada" if self._is_paused else "parada"
            message = f"Atualmente {status}: {self._current_media_item.title}. Volume: {int(self._volume * 100)}%."
            if self._current_media_item.artist:
                message += f" Artista: {self._current_media_item.artist}."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}
        message = "Nenhuma mídia em reprodução no momento."
        await self._speak_response(message)
        return {"success": True, "output": message, "error": None} # Not an error, just no media

    async def _add_to_playlist_command(self, playlist_name: str, path: str, title: str, artist: Optional[str] = None) -> Dict[str, Any]:
        """Adiciona um ficheiro de mídia a uma playlist."""
        await self._playlists_loaded.wait()
        
        media_path = Path(path)
        if not media_path.exists():
            message = f"Ficheiro de mídia não encontrado para adicionar à playlist: {path}"
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "File not found"}
        
        media_item = MediaItem(path=media_path, title=title, artist=artist)
        
        if playlist_name not in self._loaded_playlists:
            self._loaded_playlists[playlist_name] = []
            self.logger.info(f"Nova playlist '{playlist_name}' criada.")
        
        self._loaded_playlists[playlist_name].append(media_item)
        await self._save_playlists_to_storage()
        
        message = f"'{title}' adicionado à playlist '{playlist_name}'."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_INFO)
        return {"success": True, "output": message, "error": None}

    async def _list_playlists_command(self) -> Dict[str, Any]:
        """Lista todas as playlists guardadas."""
        await self._playlists_loaded.wait()
        
        if not self._loaded_playlists:
            message = "Nenhuma playlist guardada encontrada."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}
        
        output_lines = ["Playlists guardadas:"]
        for name, items in self._loaded_playlists.items():
            output_lines.append(f"- {name} ({len(items)} itens)")
        
        message = "\n".join(output_lines)
        await self._speak_response(f"Suas playlists foram listadas. Verifique o ecrã para os detalhes.")
        return {"success": True, "output": message, "error": None}

    async def _remove_from_playlist_command(self, playlist_name: str, title_or_path: str) -> Dict[str, Any]:
        """Remove um item de mídia de uma playlist pelo título ou caminho."""
        await self._playlists_loaded.wait()

        if playlist_name not in self._loaded_playlists:
            message = f"Playlist '{playlist_name}' não encontrada."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Playlist not found"}

        playlist = self._loaded_playlists[playlist_name]
        item_removed = False
        for i, item in enumerate(playlist):
            if title_or_path.lower() in item.title.lower() or title_or_path.lower() in str(item.path).lower():
                removed_item = playlist.pop(i)
                item_removed = True
                message = f"'{removed_item.title}' removido da playlist '{playlist_name}'."
                await self._save_playlists_to_storage()
                await self._speak_response(message)
                await self.notification_manager.add_notification(message, level=NOTIFICATION_INFO)
                return {"success": True, "output": message, "error": None}
        
        message = f"Item '{title_or_path}' não encontrado na playlist '{playlist_name}'."
        await self._speak_response(message)
        return {"success": False, "output": message, "error": "Item not found in playlist"}

    async def _toggle_shuffle_command(self) -> Dict[str, Any]:
        """Ativa ou desativa o modo aleatório para a reprodução da playlist."""
        self._shuffle = not self._shuffle
        message = f"Modo aleatório {'ativado' if self._shuffle else 'desativado'}."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_INFO)
        return {"success": True, "output": message, "error": None}

    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers media management commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin MediaManager...")
        executor.register_command("play_media", self._play_media_command)
        executor.register_command("pause_media", self._pause_media_command)
        executor.register_command("resume_media", self._resume_media_command)
        executor.register_command("stop_media", self._stop_media_command)
        executor.register_command("set_media_volume", self._set_volume_command)
        executor.register_command("get_media_status", self._current_media_status_command)
        executor.register_command("add_to_playlist", self._add_to_playlist_command)
        executor.register_command("list_playlists", self._list_playlists_command)
        executor.register_command("remove_from_playlist", self._remove_from_playlist_command)
        executor.register_command("toggle_shuffle", self._toggle_shuffle_command)
        self.logger.info("Comandos MediaManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for media management features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "play_media",
                    "description": "Inicia a reprodução de um ficheiro de mídia ou de uma playlist. Se nada for especificado e a mídia estiver pausada, retoma a reprodução. Pode tocar o próximo item de uma playlist.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "O caminho completo para o ficheiro de mídia (áudio ou vídeo). Opcional se for uma playlist ou retomar.",
                            },
                            "playlist_name": {
                                "type": "string",
                                "description": "O nome da playlist a ser reproduzida. Opcional.",
                            },
                             "title": {
                                "type": "string",
                                "description": "O título do ficheiro de mídia, se for diferente do nome do ficheiro. Opcional.",
                            }
                        },
                        "required": [], # path ou playlist_name (ou retomar) são opcionais
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "pause_media",
                    "description": "Pausa a reprodução de mídia atual.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "resume_media",
                    "description": "Retoma a reprodução de mídia pausada.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "stop_media",
                    "description": "Para completamente a reprodução de mídia atual.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "set_media_volume",
                    "description": "Define o nível de volume para a reprodução de mídia. O nível deve ser um valor entre 0.0 (mudo) e 1.0 (máximo).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "level": {
                                "type": "number",
                                "format": "float",
                                "description": "O nível de volume (0.0 a 1.0).",
                            }
                        },
                        "required": ["level"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_media_status",
                    "description": "Reporta o status da mídia atualmente em reprodução (título, artista, estado de reprodução, volume).",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "add_to_playlist",
                    "description": "Adiciona um ficheiro de mídia a uma playlist existente ou cria uma nova. Requer o nome da playlist e o caminho para o ficheiro.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "playlist_name": {
                                "type": "string",
                                "description": "O nome da playlist à qual adicionar o item.",
                            },
                            "path": {
                                "type": "string",
                                "description": "O caminho completo para o ficheiro de mídia.",
                            },
                            "title": {
                                "type": "string",
                                "description": "O título da mídia. Use o nome do ficheiro se não tiver um título específico.",
                            },
                            "artist": {
                                "type": "string",
                                "description": "O artista da mídia. Opcional.",
                            }
                        },
                        "required": ["playlist_name", "path", "title"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_playlists",
                    "description": "Lista todas as playlists de mídia guardadas pelo usuário.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "remove_from_playlist",
                    "description": "Remove um item específico de uma playlist pelo nome da playlist e pelo título ou caminho do item.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "playlist_name": {
                                "type": "string",
                                "description": "O nome da playlist de onde remover o item.",
                            },
                            "title_or_path": {
                                "type": "string",
                                "description": "O título ou o caminho do ficheiro do item de mídia a ser removido.",
                            }
                        },
                        "required": ["playlist_name", "title_or_path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "toggle_shuffle",
                    "description": "Ativa ou desativa o modo aleatório (shuffle) para a reprodução da playlist.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
        ]

    async def _speak_response(self, text: str) -> None:
        """Helper para vocalizar respostas através do módulo TTS principal do GEM."""
        if self.tts_module:
            await self.tts_module.speak(text)
        else:
            self.logger.warning(f"Módulo TTS não disponível para falar: '{text}'")

    def shutdown(self) -> None:
        """Stops any ongoing playback and performs cleanup."""
        self.logger.info("MediaManager a ser desligado. A parar reprodução de mídia ativa.")
        if self._current_playback:
            self._current_playback.stop()
            self._current_playback = None
        if self._playback_future:
            self._playback_future.cancel()
        self._is_playing = False
        self._is_paused = False


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    import tempfile
    import wave
    import numpy as np
    
    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestMediaManager")

    # --- Dummy Implementations for testing ---
    class DummyEventManager:
        def __init__(self, logger):
            self.logger = logger
        async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
            self.logger.info(f"Dummy EventManager: Publicado '{event_type}' com {data}")

    class DummyNotificationManager:
        def __init__(self, logger):
            self.logger = logger
            self._history: Deque[Dict[str, Any]] = deque()
        async def add_notification(self, message: str, level: str = NOTIFICATION_INFO, vocalize: bool = True) -> None:
            self.logger.info(f"Dummy Notification: [{level.upper()}] {message} (Vocalize: {vocalize})")
            self._history.append({"message": message, "level": level})
            await asyncio.sleep(0.01)
        def get_notification_history(self, limit: int = 10):
            return list(self._history)[-limit:]

    class DummyStorage:
        def __init__(self, logger):
            self.logger = logger
            self._data: Dict[str, Any] = {}
        async def get_setting(self, key: str, default: Any = None) -> Any:
            self.logger.info(f"Dummy Storage: A obter '{key}'")
            return self._data.get(key, default)
        async def set_setting(self, key: str, value: Any) -> bool:
            self.logger.info(f"Dummy Storage: A salvar '{key}'")
            self._data[key] = value
            return True

    class DummyTTSModule:
        def __init__(self, logger):
            self.logger = logger
        async def speak(self, text: str) -> None:
            self.logger.info(f"Dummy TTS: A falar: '{text}'")
            await asyncio.sleep(0.01)

    class DummyCommandExecutor:
        def __init__(self, logger):
            self.logger = logger
            self.commands = {}
        def register_command(self, name: str, func: Callable[..., Awaitable[Dict[str, Any]]], **kwargs) -> None:
            self.commands[name] = (func, kwargs)
            self.logger.info(f"Dummy CommandExecutor: Registou comando '{name}'.")
        async def execute(self, command_name: str, *args, **kwargs) -> Dict[str, Any]:
            self.logger.info(f"Dummy CommandExecutor: A executar '{command_name}' com args={args}, kwargs={kwargs}")
            if command_name in self.commands:
                func, default_kwargs = self.commands[command_name]
                merged_kwargs = {**default_kwargs, **kwargs}
                return await func(*args, **merged_kwargs)
            return {"success": False, "output": "", "error": "Comando desconhecido simulado."}

    class DummyConfigManager:
        def __init__(self):
            self.config = type('GEMConfig', (), {
                'general': type('GeneralConfig', (), {
                    'max_notification_history': 5,
                    'enable_audio_notifications': True
                })()
            })()
        def get_config(self) -> Any:
            return self.config

    class DummyGEM:
        def __init__(self, logger_instance: logging.Logger):
            self.logger = logger_instance
            self.event_manager = DummyEventManager(logger_instance)
            self.notification_manager = DummyNotificationManager(logger_instance)
            self.storage = DummyStorage(logger_instance)
            self.tts_module = DummyTTSModule(logger_instance)
            self.config_manager = DummyConfigManager()
            self.command_executor = DummyCommandExecutor(logger_instance)

    # --- Helper to create a dummy WAV file for testing ---
    def create_dummy_wav(file_path: Path, duration_s: float = 1.0, freq: int = 440, sample_rate: int = 44100):
        t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
        amplitude = np.iinfo(np.int16).max * 0.5
        data = (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.int16)
        
        with wave.open(str(file_path), 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2) # 2 bytes for int16
            wf.setframerate(sample_rate)
            wf.writeframes(data.tobytes())
        logger.info(f"Ficheiro WAV dummy criado: {file_path}")
        return file_path

    async def run_media_manager_tests():
        print("\n--- Iniciando Testes do MediaManager ---")

        dummy_gem = DummyGEM(logger)
        media_manager = MediaManager(dummy_gem, logger)
        
        # Register commands for the CommandExecutor to be able to call them
        media_manager.register_commands(dummy_gem.command_executor)

        # Create dummy media files
        temp_dir = Path(tempfile.mkdtemp())
        audio_file1 = create_dummy_wav(temp_dir / "song1.wav", duration_s=2.0, freq=440)
        audio_file2 = create_dummy_wav(temp_dir / "song2.wav", duration_s=1.5, freq=660)
        audio_file3 = create_dummy_wav(temp_dir / "song3.wav", duration_s=2.5, freq=880)

        await media_manager.initialize() # Load playlists (initially empty)

        print("\n--- Teste 1: Adicionar mídia à playlist ---")
        await dummy_gem.command_executor.execute("add_to_playlist", playlist_name="Minhas Músicas", path=str(audio_file1), title="Canção Um", artist="Artista A")
        await dummy_gem.command_executor.execute("add_to_playlist", playlist_name="Minhas Músicas", path=str(audio_file2), title="Canção Dois", artist="Artista B")
        await dummy_gem.command_executor.execute("add_to_playlist", playlist_name="Favoritos", path=str(audio_file3), title="Canção Três")
        await asyncio.sleep(0.1)

        print("\n--- Teste 2: Listar Playlists ---")
        result_list_playlists = await dummy_gem.command_executor.execute("list_playlists")
        print(result_list_playlists["output"])
        assert "Minhas Músicas (2 itens)" in result_list_playlists["output"]
        assert "Favoritos (1 itens)" in result_list_playlists["output"]

        print("\n--- Teste 3: Tocar uma música diretamente ---")
        result_play_single = await dummy_gem.command_executor.execute("play_media", path=str(audio_file1), title="Direta")
        print(result_play_single["output"])
        assert "A reproduzir Direta" in result_play_single["output"]
        await asyncio.sleep(2.5) # Allow playback to finish

        print("\n--- Teste 4: Tocar uma playlist ---")
        result_play_playlist = await dummy_gem.command_executor.execute("play_media", playlist_name="Minhas Músicas")
        print(result_play_playlist["output"])
        assert "A reproduzir Canção Um" in result_play_playlist["output"]
        await asyncio.sleep(2.5) # Allow song1 to finish and song2 to start
        assert "A reproduzir Canção Dois" in dummy_gem.notification_manager.get_notification_history(limit=1)[0]['message']
        await asyncio.sleep(2.0) # Allow song2 to finish

        print("\n--- Teste 5: Pausar e Retomar ---")
        result_play_playlist_again = await dummy_gem.command_executor.execute("play_media", playlist_name="Favoritos")
        await asyncio.sleep(0.5) # Let it start
        result_pause = await dummy_gem.command_executor.execute("pause_media")
        print(result_pause["output"])
        assert "Reprodução pausada." in result_pause["output"]
        await asyncio.sleep(1.0) # While paused
        result_resume = await dummy_gem.command_executor.execute("resume_media")
        print(result_resume["output"])
        assert "Reprodução retomada." in result_resume["output"]
        await asyncio.sleep(3.0) # Allow to finish

        print("\n--- Teste 6: Definir Volume ---")
        result_set_volume = await dummy_gem.command_executor.execute("set_media_volume", level=0.2)
        print(result_set_volume["output"])
        assert "Volume definido para 20%." in result_set_volume["output"]
        
        # Tentar tocar uma música com volume baixo
        result_play_low_volume = await dummy_gem.command_executor.execute("play_media", path=str(audio_file1), title="Baixo Volume")
        print(result_play_low_volume["output"])
        await asyncio.sleep(2.5)

        print("\n--- Teste 7: Status da Mídia ---")
        result_status = await dummy_gem.command_executor.execute("get_media_status")
        print(result_status["output"])
        assert "Nenhuma mídia em reprodução no momento." in result_status["output"] # Deveria estar parada após o último play

        # Tocar e verificar status
        await dummy_gem.command_executor.execute("play_media", path=str(audio_file2), title="Verificar Status")
        await asyncio.sleep(0.5)
        result_status_playing = await dummy_gem.command_executor.execute("get_media_status")
        print(result_status_playing["output"])
        assert "reproduzindo: Verificar Status." in result_status_playing["output"]
        await dummy_gem.command_executor.execute("pause_media")
        result_status_paused = await dummy_gem.command_executor.execute("get_media_status")
        print(result_status_paused["output"])
        assert "pausada: Verificar Status." in result_status_paused["output"]
        await dummy_gem.command_executor.execute("stop_media") # Stop it

        print("\n--- Teste 8: Remover de Playlist ---")
        result_remove = await dummy_gem.command_executor.execute("remove_from_playlist", playlist_name="Minhas Músicas", title_or_path="Canção Um")
        print(result_remove["output"])
        assert "'Canção Um' removido da playlist 'Minhas Músicas'." in result_remove["output"]
        
        result_list_playlists_after_remove = await dummy_gem.command_executor.execute("list_playlists")
        print(result_list_playlists_after_remove["output"])
        assert "Minhas Músicas (1 itens)" in result_list_playlists_after_remove["output"]

        print("\n--- Teste 9: Ativar/Desativar Shuffle ---")
        result_toggle_shuffle_on = await dummy_gem.command_executor.execute("toggle_shuffle")
        print(result_toggle_shuffle_on["output"])
        assert "Modo aleatório ativado." in result_toggle_shuffle_on["output"]
        
        result_toggle_shuffle_off = await dummy_gem.command_executor.execute("toggle_shuffle")
        print(result_toggle_shuffle_off["output"])
        assert "Modo aleatório desativado." in result_toggle_shuffle_off["output"]

        print("\n--- Teste 10: Parar Mídia ---")
        # Garantir que a mídia está a tocar para parar
        await dummy_gem.command_executor.execute("play_media", playlist_name="Minhas Músicas")
        await asyncio.sleep(0.5)
        result_stop = await dummy_gem.command_executor.execute("stop_media")
        print(result_stop["output"])
        assert "Reprodução de mídia parada." in result_stop["output"]


        print("\n--- Testes do MediaManager concluídos com sucesso. ---")
        media_manager.shutdown()
        
        # Cleanup dummy files and directory
        for f in temp_dir.iterdir():
            f.unlink(missing_ok=True)
        temp_dir.rmdir()
        logger.info(f"Diretório temporário {temp_dir} limpo.")

    asyncio.run(run_media_manager_tests())


