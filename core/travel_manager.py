#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
üíé GEM OS - Travel Manager (core/travel_manager.py)
Manages travel planning, including flight and hotel search, and itinerary management.

Responsibilities
----------------
- Search for flights and hotels using mock APIs.
- Manage user's travel itineraries (add, list, remove segments).
- Persist travel data using the Storage module.
- Expose travel capabilities as tools for the LLM.
- Publish travel-related events.
- Integrate with NotificationManager for alerts.
"""

from __future__ import annotations

import asyncio
import logging
import httpx # Para requisi√ß√µes HTTP ass√≠ncronas
import uuid
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Awaitable

from core.plugins import BasePlugin, CommandExecutor, GEMVoiceAssistant
from core.notification_manager import NotificationManager, NOTIFICATION_INFO, NOTIFICATION_WARNING, NOTIFICATION_SUCCESS

# Forward declarations for type hinting
class EventManager:
    async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        pass

class TTSModule:
    async def speak(self, text: str) -> None:
        pass

class ConfigManager:
    def get_config(self) -> Any:
        pass

class Storage:
    async def get_setting(self, key: str, default: Any = None) -> Any:
        pass
    async def set_setting(self, key: str, value: Any) -> bool:
        pass

# --- Dataclass para Voos ---
@dataclass
class Flight:
    id: str
    airline: str
    flight_number: str
    departure_airport: str
    arrival_airport: str
    departure_time: datetime
    arrival_time: datetime
    price: float
    currency: str
    booking_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "airline": self.airline,
            "flight_number": self.flight_number,
            "departure_airport": self.departure_airport,
            "arrival_airport": self.arrival_airport,
            "departure_time": self.departure_time.isoformat(),
            "arrival_time": self.arrival_time.isoformat(),
            "price": self.price,
            "currency": self.currency,
            "booking_url": self.booking_url,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Flight:
        return cls(
            id=data["id"],
            airline=data["airline"],
            flight_number=data["flight_number"],
            departure_airport=data["departure_airport"],
            arrival_airport=data["arrival_airport"],
            departure_time=datetime.fromisoformat(data["departure_time"]),
            arrival_time=datetime.fromisoformat(data["arrival_time"]),
            price=data["price"],
            currency=data["currency"],
            booking_url=data.get("booking_url"),
        )

# --- Dataclass para Hot√©is ---
@dataclass
class Hotel:
    id: str
    name: str
    city: str
    check_in_date: datetime
    check_out_date: datetime
    price_per_night: float
    currency: str
    stars: Optional[int] = None
    booking_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "city": self.city,
            "check_in_date": self.check_in_date.isoformat(),
            "check_out_date": self.check_out_date.isoformat(),
            "price_per_night": self.price_per_night,
            "currency": self.currency,
            "stars": self.stars,
            "booking_url": self.booking_url,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Hotel:
        return cls(
            id=data["id"],
            name=data["name"],
            city=data["city"],
            check_in_date=datetime.fromisoformat(data["check_in_date"]),
            check_out_date=datetime.fromisoformat(data["check_out_date"]),
            price_per_night=data["price_per_night"],
            currency=data["currency"],
            stars=data.get("stars"),
            booking_url=data.get("booking_url"),
        )

# --- Dataclass para Itiner√°rio ---
@dataclass
class ItineraryItem:
    id: str
    name: str # Nome do item do itiner√°rio (ex: "Voo para Paris", "Hotel em Roma")
    type: str # "flight", "hotel", "activity", "general"
    start_time: datetime
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    details: Optional[Dict[str, Any]] = None # Pode guardar os dados de Flight ou Hotel aqui

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "location": self.location,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ItineraryItem:
        return cls(
            id=data["id"],
            name=data["name"],
            type=data["type"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            location=data.get("location"),
            details=data.get("details"),
        )


# --- Travel Manager como um Plugin ---
class TravelManager(BasePlugin):
    """
    Manages travel planning data for GEM OS, acting as a plugin.
    This implementation uses mock APIs and local storage for demonstration.
    Real integration would require actual travel APIs (e.g., Skyscanner, Booking.com)
    and robust authentication.
    """
    STORAGE_KEY_ITINERARIES = "user_travel_itineraries"
    
    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("TravelManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.storage: Storage = gem_instance.storage
        self.tts_module: TTSModule = gem_instance.tts_module
        self.config_manager: ConfigManager = gem_instance.config_manager

        self._http_client = httpx.AsyncClient()
        self._itineraries: Dict[str, ItineraryItem] = {} # {itinerary_item_id: ItineraryItem_object}
        self._itineraries_loaded = asyncio.Event()

        # Mock API URLs (in a real scenario, these would be actual travel APIs)
        self._mock_flights_api_url = "https://api.mockflights.com/v1"
        self._mock_hotels_api_url = "https://api.mockhotels.com/v1"
        self._mock_api_key = os.getenv("TRAVEL_API_KEY", "MOCK_TRAVEL_KEY") # Chave para ambas as APIs mock

        if self._mock_api_key == "MOCK_TRAVEL_KEY":
            self.logger.warning("Credenciais de viagem est√£o usando valores de MOCK. Funcionalidade real ser√° limitada.")
        
        self.logger.info("TravelManager configurado com APIs mock.")

    async def initialize(self) -> None:
        """Loads itineraries from storage and performs any necessary setup."""
        await self._load_itineraries_from_storage()
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self.logger.info("TravelManager inicializado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event to gracefully close HTTP client."""
        self.logger.info("Recebido GEM_SHUTDOWN. A fechar cliente HTTP do TravelManager.")
        await self.shutdown()

    async def _load_itineraries_from_storage(self) -> None:
        """Loads itinerary items from persistent storage."""
        try:
            itineraries_data = await self.storage.get_setting(self.STORAGE_KEY_ITINERARIES, [])
            for item_dict in itineraries_data:
                try:
                    item = ItineraryItem.from_dict(item_dict)
                    self._itineraries[item.id] = item
                except Exception as e:
                    self.logger.error(f"Erro ao carregar item do itiner√°rio: {e} - Dados: {item_dict}", exc_info=True)
            self.logger.info(f"Carregados {len(self._itineraries)} itens do itiner√°rio do armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao carregar itiner√°rios do armazenamento: {e}", exc_info=True)
        finally:
            self._itineraries_loaded.set() # Sinaliza que os itiner√°rios foram carregados

    async def _save_itineraries_to_storage(self) -> None:
        """Saves current itinerary items to persistent storage."""
        try:
            itineraries_data = [item.to_dict() for item in self._itineraries.values()]
            await self.storage.set_setting(self.STORAGE_KEY_ITINERARIES, itineraries_data)
            self.logger.debug(f"Salvos {len(self._itineraries)} itens do itiner√°rio para o armazenamento.")
        except Exception as e:
            self.logger.error(f"Falha ao salvar itiner√°rios no armazenamento: {e}", exc_info=True)

    async def _search_flights_api(self, origin: str, destination: str, departure_date: str,
                                  return_date: Optional[str] = None, passengers: int = 1,
                                  limit: int = 3) -> List[Flight]:
        """
        Simulates searching for flights using a mock API.
        `departure_date` and `return_date` in YYYY-MM-DD format.
        """
        search_url = f"{self._mock_flights_api_url}/flights/search"
        headers = {"Authorization": f"Bearer {self._mock_api_key}"}
        params = {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "passengers": passengers,
            "limit": limit
        }
        if return_date:
            params["return_date"] = return_date

        if "MOCK_TRAVEL_KEY" in self._mock_api_key:
            self.logger.warning(f"Usando credenciais mock para viagens. Busca de voos apenas simulada.")
            await asyncio.sleep(0.5) # Simulate API call delay

            mock_flights = []
            if "lis" in origin.lower() and "par" in destination.lower():
                mock_flights.append(Flight(
                    id="flt-001", airline="AirMock", flight_number="AM100",
                    departure_airport="LIS", arrival_airport="CDG",
                    departure_time=datetime.fromisoformat(f"{departure_date}T08:00:00Z"),
                    arrival_time=datetime.fromisoformat(f"{departure_date}T10:30:00Z"),
                    price=150.00, currency="EUR", booking_url="https://mockair.com/book/am100"
                ))
                if return_date:
                     mock_flights.append(Flight(
                        id="flt-002", airline="AirMock", flight_number="AM101",
                        departure_airport="CDG", arrival_airport="LIS",
                        departure_time=datetime.fromisoformat(f"{return_date}T18:00:00Z"),
                        arrival_time=datetime.fromisoformat(f"{return_date}T20:30:00Z"),
                        price=170.00, currency="EUR", booking_url="https://mockair.com/book/am101"
                    ))
            elif "nyc" in origin.lower() and "lax" in destination.lower():
                 mock_flights.append(Flight(
                    id="flt-003", airline="UnitedMock", flight_number="UM200",
                    departure_airport="JFK", arrival_airport="LAX",
                    departure_time=datetime.fromisoformat(f"{departure_date}T10:00:00Z"),
                    arrival_time=datetime.fromisoformat(f"{departure_date}T13:00:00Z"),
                    price=300.00, currency="USD", booking_url="https://mockunited.com/book/um200"
                ))
            
            await self.notification_manager.add_notification(
                f"Busca simulada de voos para {origin}-{destination} conclu√≠da.", level=NOTIFICATION_INFO
            )
            return mock_flights[:limit]

        self.logger.info(f"Simulando busca de voos para {origin}-{destination}...")
        try:
            response = await self._http_client.get(search_url, params=params, headers=headers, timeout=15.0)
            response.raise_for_status()
            data = response.json()

            flights: List[Flight] = []
            for item in data.get("flights", []):
                try:
                    flights.append(Flight.from_dict(item))
                except Exception as e:
                    self.logger.error(f"Erro ao parsear dados de voo: {e} - Dados: {item}", exc_info=True)
            
            await self.notification_manager.add_notification(
                f"Busca de voos para {origin}-{destination} conclu√≠da. {len(flights)} resultados.", level=NOTIFICATION_SUCCESS, vocalize=False
            )
            await self.event_manager.publish("TRAVEL_FLIGHT_SEARCHED", {"origin": origin, "destination": destination, "count": len(flights)})
            return flights

        except httpx.HTTPStatusError as e:
            error_msg = f"Erro HTTP ao buscar voos: {e.response.status_code} - {e.response.text}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Falha na busca de voos: {e.response.status_code}", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, houve um erro ao buscar voos.")
            return []
        except httpx.RequestError as e:
            error_msg = f"Erro de rede/requisi√ß√£o ao buscar voos: {e}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Erro de rede na busca de voos.", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, houve um problema de rede ao buscar voos.")
            return []
        except Exception as e:
            error_msg = f"Erro inesperado ao buscar voos: {e}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Erro inesperado na busca de voos.", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, ocorreu um erro inesperado ao buscar voos.")
            return []

    async def _search_hotels_api(self, city: str, check_in_date: str, check_out_date: str,
                                 guests: int = 1, stars: Optional[int] = None, limit: int = 3) -> List[Hotel]:
        """
        Simulates searching for hotels using a mock API.
        `check_in_date` and `check_out_date` in YYYY-MM-DD format.
        """
        search_url = f"{self._mock_hotels_api_url}/hotels/search"
        headers = {"Authorization": f"Bearer {self._mock_api_key}"}
        params = {
            "city": city,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "guests": guests,
            "limit": limit
        }
        if stars:
            params["stars"] = stars

        if "MOCK_TRAVEL_KEY" in self._mock_api_key:
            self.logger.warning(f"Usando credenciais mock para viagens. Busca de hot√©is apenas simulada.")
            await asyncio.sleep(0.5)

            mock_hotels = []
            if "paris" in city.lower():
                mock_hotels.append(Hotel(
                    id="htl-001", name="Hotel Mock Eiffel", city="Paris",
                    check_in_date=datetime.fromisoformat(check_in_date),
                    check_out_date=datetime.fromisoformat(check_out_date),
                    price_per_night=200.00, currency="EUR", stars=4,
                    booking_url="https://mockhotels.com/book/eiffel"
                ))
                mock_hotels.append(Hotel(
                    id="htl-002", name="Hostel Central Mock", city="Paris",
                    check_in_date=datetime.fromisoformat(check_in_date),
                    check_out_date=datetime.fromisoformat(check_out_date),
                    price_per_night=80.00, currency="EUR", stars=2,
                    booking_url="https://mockhostels.com/book/central"
                ))
            elif "lisboa" in city.lower():
                mock_hotels.append(Hotel(
                    id="htl-003", name="Hotel Mock Tejo", city="Lisboa",
                    check_in_date=datetime.fromisoformat(check_in_date),
                    check_out_date=datetime.fromisoformat(check_out_date),
                    price_per_night=120.00, currency="EUR", stars=3,
                    booking_url="https://mockhotels.com/book/tejo"
                ))
            
            await self.notification_manager.add_notification(
                f"Busca simulada de hot√©is para {city} conclu√≠da.", level=NOTIFICATION_INFO
            )
            return mock_hotels[:limit]

        self.logger.info(f"Simulando busca de hot√©is para {city}...")
        try:
            response = await self._http_client.get(search_url, params=params, headers=headers, timeout=15.0)
            response.raise_for_status()
            data = response.json()

            hotels: List[Hotel] = []
            for item in data.get("hotels", []):
                try:
                    hotels.append(Hotel.from_dict(item))
                except Exception as e:
                    self.logger.error(f"Erro ao parsear dados de hotel: {e} - Dados: {item}", exc_info=True)
            
            await self.notification_manager.add_notification(
                f"Busca de hot√©is para {city} conclu√≠da. {len(hotels)} resultados.", level=NOTIFICATION_SUCCESS, vocalize=False
            )
            await self.event_manager.publish("TRAVEL_HOTEL_SEARCHED", {"city": city, "count": len(hotels)})
            return hotels

        except httpx.HTTPStatusError as e:
            error_msg = f"Erro HTTP ao buscar hot√©is: {e.response.status_code} - {e.response.text}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Falha na busca de hot√©is: {e.response.status_code}", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, houve um erro ao buscar hot√©is.")
            return []
        except httpx.RequestError as e:
            error_msg = f"Erro de rede/requisi√ß√£o ao buscar hot√©is: {e}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Erro de rede na busca de hot√©is.", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, houve um problema de rede ao buscar hot√©is.")
            return []
        except Exception as e:
            error_msg = f"Erro inesperado ao buscar hot√©is: {e}"
            self.logger.error(error_msg, exc_info=True)
            await self.notification_manager.add_notification(f"Erro inesperado na busca de hot√©is.", level=NOTIFICATION_ERROR)
            await self.tts_module.speak(f"Desculpe, ocorreu um erro inesperado ao buscar hot√©is.")
            return []

    # --------------------------------------------------------------------- Commands

    async def _search_flights_command(self, origin: str, destination: str, departure_date: str,
                                      return_date: Optional[str] = None, passengers: int = 1,
                                      limit: int = 3) -> Dict[str, Any]:
        """
        Pesquisa voos.
        `departure_date` e `return_date` devem ser no formato YYYY-MM-DD.
        """
        try:
            datetime.fromisoformat(departure_date)
            if return_date: datetime.fromisoformat(return_date)
        except ValueError:
            await self._speak_response("Formato de data inv√°lido. Use 'AAAA-MM-DD'.")
            return {"success": False, "output": "Formato de data inv√°lido.", "error": "Invalid date format"}
        
        if not (1 <= passengers <= 9):
            return {"success": False, "output": "", "error": "N√∫mero de passageiros deve ser entre 1 e 9."}
        if not (1 <= limit <= 10):
            return {"success": False, "output": "", "error": "O limite de resultados deve ser entre 1 e 10."}

        flights = await self._search_flights_api(origin, destination, departure_date, return_date, passengers, limit)

        if not flights:
            message = f"N√£o foram encontrados voos para {origin} para {destination} na data especificada."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}
        
        output_lines = [f"Voos encontrados de {origin} para {destination} (Partida: {departure_date}{f', Regresso: {return_date}' if return_date else ''}):"]
        for i, flight in enumerate(flights):
            output_lines.append(f"{i+1}. {flight.airline} Voo {flight.flight_number} - {flight.departure_airport} ({flight.departure_time.strftime('%H:%M')}) para {flight.arrival_airport} ({flight.arrival_time.strftime('%H:%M')})")
            output_lines.append(f"   Pre√ßo: {flight.price:.2f} {flight.currency}")
            if flight.booking_url:
                output_lines.append(f"   Reservar: {flight.booking_url}")
            output_lines.append("-" * 20)
        
        message = "\n".join(output_lines)
        await self._speak_response(f"Voos encontrados. Verifique o ecr√£ para os detalhes.")
        return {"success": True, "output": message, "error": None}

    async def _search_hotels_command(self, city: str, check_in_date: str, check_out_date: str,
                                     guests: int = 1, stars: Optional[int] = None, limit: int = 3) -> Dict[str, Any]:
        """
        Pesquisa hot√©is.
        `check_in_date` e `check_out_date` devem ser no formato YYYY-MM-DD.
        `stars` pode ser 1 a 5.
        """
        try:
            dt_check_in = datetime.fromisoformat(check_in_date)
            dt_check_out = datetime.fromisoformat(check_out_date)
            if dt_check_in >= dt_check_out:
                raise ValueError("Data de check-in deve ser anterior √† data de check-out.")
        except ValueError as e:
            await self._speak_response(f"Formato de data inv√°lido ou datas incorretas: {e}. Use 'AAAA-MM-DD'.")
            return {"success": False, "output": "Formato de data inv√°lido.", "error": str(e)}

        if not (1 <= guests <= 9):
            return {"success": False, "output": "", "error": "N√∫mero de h√≥spedes deve ser entre 1 e 9."}
        if stars and not (1 <= stars <= 5):
            return {"success": False, "output": "", "error": "O n√∫mero de estrelas deve ser entre 1 e 5."}
        if not (1 <= limit <= 10):
            return {"success": False, "output": "", "error": "O limite de resultados deve ser entre 1 e 10."}

        hotels = await self._search_hotels_api(city, check_in_date, check_out_date, guests, stars, limit)

        if not hotels:
            message = f"N√£o foram encontrados hot√©is em {city} para as datas especificadas."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}
        
        output_lines = [f"Hot√©is encontrados em {city} (Check-in: {check_in_date}, Check-out: {check_out_date}):"]
        for i, hotel in enumerate(hotels):
            stars_str = "‚≠ê" * hotel.stars if hotel.stars else ""
            output_lines.append(f"{i+1}. {hotel.name} {stars_str} - Pre√ßo por noite: {hotel.price_per_night:.2f} {hotel.currency}")
            if hotel.booking_url:
                output_lines.append(f"   Reservar: {hotel.booking_url}")
            output_lines.append("-" * 20)
        
        message = "\n".join(output_lines)
        await self._speak_response(f"Hot√©is encontrados. Verifique o ecr√£ para os detalhes.")
        return {"success": True, "output": message, "error": None}

    async def _add_itinerary_item_command(self, name: str, item_type: str, start_time: str,
                                          end_time: Optional[str] = None, location: Optional[str] = None,
                                          details_json: Optional[str] = None) -> Dict[str, Any]:
        """
        Adiciona um item ao itiner√°rio de viagem (ex: um voo, uma reserva de hotel, uma atividade).
        `start_time` e `end_time` devem ser no formato ISO 8601 (YYYY-MM-DD HH:MM).
        `details_json` deve ser uma string JSON com detalhes espec√≠ficos (ex: dados de voo ou hotel).
        """
        await self._itineraries_loaded.wait()

        try:
            parsed_start_time = datetime.fromisoformat(start_time)
            parsed_end_time: Optional[datetime] = None
            if end_time:
                parsed_end_time = datetime.fromisoformat(end_time)
        except ValueError:
            await self._speak_response("Formato de data/hora inv√°lido. Use 'AAAA-MM-DD HH:MM'.")
            return {"success": False, "output": "Formato de data/hora inv√°lido.", "error": "Invalid datetime format"}

        parsed_details: Optional[Dict[str, Any]] = None
        if details_json:
            try:
                parsed_details = json.loads(details_json)
            except json.JSONDecodeError:
                await self._speak_response("Formato JSON inv√°lido para detalhes. Por favor, corrija.")
                return {"success": False, "output": "Formato de detalhes JSON inv√°lido.", "error": "Invalid JSON for details"}
        
        item_id = str(uuid.uuid4())
        new_item = ItineraryItem(
            id=item_id,
            name=name,
            type=item_type,
            start_time=parsed_start_time,
            end_time=parsed_end_time,
            location=location,
            details=parsed_details
        )
        self._itineraries[item_id] = new_item
        await self._save_itineraries_to_storage()

        message = f"Item '{name}' (tipo: {item_type}) adicionado ao seu itiner√°rio."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("TRAVEL_ITINERARY_ITEM_ADDED", new_item.to_dict())
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _list_itinerary_command(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Lista itens do itiner√°rio, opcionalmente filtrando por um intervalo de datas.
        `start_date` e `end_date` devem ser no formato YYYY-MM-DD.
        """
        await self._itineraries_loaded.wait()

        filtered_items: List[ItineraryItem] = []
        parsed_start_date: Optional[datetime] = None
        parsed_end_date: Optional[datetime] = None

        try:
            if start_date: parsed_start_date = datetime.fromisoformat(start_date).replace(hour=0, minute=0, second=0, microsecond=0)
            if end_date: parsed_end_date = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
        except ValueError:
            await self._speak_response("Formato de data inv√°lido. Use 'AAAA-MM-DD'.")
            return {"success": False, "output": "Formato de data inv√°lido.", "error": "Invalid date format"}

        for item in self._itineraries.values():
            should_add = True
            if parsed_start_date and item.start_time < parsed_start_date:
                should_add = False
            if parsed_end_date and item.start_time > parsed_end_date:
                should_add = False
            
            if should_add:
                filtered_items.append(item)
        
        filtered_items.sort(key=lambda item: item.start_time) # Ordenar por tempo de in√≠cio

        if not filtered_items:
            message = "Nenhum item encontrado no itiner√°rio."
            if start_date or end_date:
                message = f"Nenhum item encontrado no itiner√°rio para o per√≠odo de {start_date or 'in√≠cio'} a {end_date or 'fim'}."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}

        output_lines = ["Seu Itiner√°rio de Viagem:"]
        for i, item in enumerate(filtered_items):
            time_info = f"{item.start_time.strftime('%Y-%m-%d %H:%M')}"
            if item.end_time:
                time_info += f" a {item.end_time.strftime('%Y-%m-%d %H:%M')}"
            
            location_info = f" ({item.location})" if item.location else ""
            
            output_lines.append(f"{i+1}. {item.name} (Tipo: {item.type}) - {time_info}{location_info}")
            if item.details:
                for key, value in item.details.items():
                    if key not in ["id", "booking_url"] and isinstance(value, (str, int, float)): # Evitar IDs e URLs grandes, focar em informa√ß√£o relevante
                        output_lines.append(f"   {key.replace('_', ' ').capitalize()}: {value}")
                if item.details.get("booking_url"):
                    output_lines.append(f"   Reservar: {item.details['booking_url']}")
            output_lines.append(f"   (ID: {item.id[:8]}...)")
            output_lines.append("-" * 20)
        
        message = "\n".join(output_lines)
        await self._speak_response(f"Seu itiner√°rio foi listado. Verifique o ecr√£ para os detalhes.")
        await self.notification_manager.add_notification("Itiner√°rio exibido.", level=NOTIFICATION_INFO)
        return {"success": True, "output": message, "error": None}

    async def _remove_itinerary_item_command(self, item_id_prefix: str) -> Dict[str, Any]:
        """
        Remove um item do itiner√°rio de viagem.
        Requer um prefixo do ID do item.
        """
        await self._itineraries_loaded.wait()

        item_to_remove: Optional[ItineraryItem] = None
        matching_items = [i for i in self._itineraries.values() if i.id.startswith(item_id_prefix)]

        if len(matching_items) == 1:
            item_to_remove = matching_items[0]
        elif len(matching_items) > 1:
            message = f"M√∫ltiplos itens correspondem ao ID '{item_id_prefix}'. Por favor, seja mais espec√≠fico."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Multiple matches"}
        else:
            message = f"Nenhum item encontrado com o ID '{item_id_prefix}' no seu itiner√°rio."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Item not found"}

        if item_to_remove:
            del self._itineraries[item_to_remove.id]
            await self._save_itineraries_to_storage()
            message = f"Item '{item_to_remove.name}' (ID: {item_to_remove.id[:8]}...) removido do seu itiner√°rio."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
            await self.event_manager.publish("TRAVEL_ITINERARY_ITEM_REMOVED", {"item_id": item_to_remove.id})
            self.logger.info(message)
            return {"success": True, "output": message, "error": None}
        
        return {"success": False, "output": "Erro desconhecido ao remover item do itiner√°rio.", "error": "Unknown error"}


    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers travel management commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin TravelManager...")
        executor.register_command("search_flights", self._search_flights_command)
        executor.register_command("search_hotels", self._search_hotels_command)
        executor.register_command("add_itinerary_item", self._add_itinerary_item_command)
        executor.register_command("list_itinerary", self._list_itinerary_command)
        executor.register_command("remove_itinerary_item", self._remove_itinerary_item_command)
        self.logger.info("Comandos TravelManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for travel features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_flights",
                    "description": "Pesquisa voos de uma origem para um destino em uma data de partida espec√≠fica. Opcionalmente, pode incluir uma data de retorno e o n√∫mero de passageiros. As datas devem ser no formato YYYY-MM-DD.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "origin": {
                                "type": "string",
                                "description": "O c√≥digo IATA do aeroporto ou nome da cidade de partida (ex: 'LIS', 'Lisboa').",
                            },
                            "destination": {
                                "type": "string",
                                "description": "O c√≥digo IATA do aeroporto ou nome da cidade de chegada (ex: 'CDG', 'Paris').",
                            },
                            "departure_date": {
                                "type": "string",
                                "description": "A data de partida no formato YYYY-MM-DD.",
                            },
                            "return_date": {
                                "type": "string",
                                "description": "A data de regresso no formato YYYY-MM-DD. Opcional para voos de ida e volta.",
                            },
                            "passengers": {
                                "type": "integer",
                                "description": "O n√∫mero de passageiros. Padr√£o para 1.",
                                "default": 1,
                                "minimum": 1,
                                "maximum": 9
                            },
                            "limit": {
                                "type": "integer",
                                "description": "O n√∫mero m√°ximo de voos a retornar. Padr√£o para 3, m√°ximo de 10.",
                                "default": 3,
                                "minimum": 1,
                                "maximum": 10
                            }
                        },
                        "required": ["origin", "destination", "departure_date"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_hotels",
                    "description": "Pesquisa hot√©is em uma cidade para um per√≠odo de check-in e check-out. Opcionalmente, pode especificar o n√∫mero de h√≥spedes e a classifica√ß√£o por estrelas. As datas devem ser no formato YYYY-MM-DD.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "O nome da cidade para pesquisar hot√©is (ex: 'Paris').",
                            },
                            "check_in_date": {
                                "type": "string",
                                "description": "A data de check-in no formato YYYY-MM-DD.",
                            },
                            "check_out_date": {
                                "type": "string",
                                "description": "A data de check-out no formato YYYY-MM-DD.",
                            },
                            "guests": {
                                "type": "integer",
                                "description": "O n√∫mero de h√≥spedes. Padr√£o para 1.",
                                "default": 1,
                                "minimum": 1,
                                "maximum": 9
                            },
                            "stars": {
                                "type": "integer",
                                "description": "A classifica√ß√£o m√≠nima por estrelas do hotel (1 a 5). Opcional.",
                                "minimum": 1,
                                "maximum": 5
                            },
                            "limit": {
                                "type": "integer",
                                "description": "O n√∫mero m√°ximo de hot√©is a retornar. Padr√£o para 3, m√°ximo de 10.",
                                "default": 3,
                                "minimum": 1,
                                "maximum": 10
                            }
                        },
                        "required": ["city", "check_in_date", "check_out_date"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "add_itinerary_item",
                    "description": "Adiciona um item ao seu itiner√°rio de viagem (ex: um voo, uma reserva de hotel, uma atividade). Requer um nome, tipo de item e hora de in√≠cio. Opcionalmente, pode incluir hora de t√©rmino, localiza√ß√£o e detalhes adicionais em formato JSON.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Um nome descritivo para o item do itiner√°rio (ex: 'Voo para Paris', 'Jantar na Torre Eiffel').",
                            },
                            "item_type": {
                                "type": "string",
                                "description": "O tipo do item do itiner√°rio (ex: 'flight', 'hotel', 'activity', 'general').",
                                "enum": ["flight", "hotel", "activity", "general"]
                            },
                            "start_time": {
                                "type": "string",
                                "description": "A data e hora de in√≠cio do item no formato ISO 8601 (YYYY-MM-DD HH:MM).",
                            },
                            "end_time": {
                                "type": "string",
                                "description": "A data e hora de t√©rmino do item no formato ISO 8601 (YYYY-MM-DD HH:MM). Opcional.",
                            },
                            "location": {
                                "type": "string",
                                "description": "A localiza√ß√£o associada ao item (ex: 'Aeroporto de Lisboa', 'Hotel Mock Eiffel'). Opcional.",
                            },
                            "details_json": {
                                "type": "string",
                                "description": "Uma string JSON com detalhes adicionais espec√≠ficos do item (ex: {'flight_number': 'AM100', 'airline': 'AirMock'}). Opcional.",
                            }
                        },
                        "required": ["name", "item_type", "start_time"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_itinerary",
                    "description": "Lista todos os itens no itiner√°rio de viagem do usu√°rio, opcionalmente filtrando por um intervalo de datas. Ordena os itens por ordem cronol√≥gica.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "description": "A data de in√≠cio do intervalo para filtrar o itiner√°rio no formato YYYY-MM-DD. Opcional.",
                            },
                            "end_date": {
                                "type": "string",
                                "description": "A data de t√©rmino do intervalo para filtrar o itiner√°rio no formato YYYY-MM-DD. Opcional.",
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "remove_itinerary_item",
                    "description": "Remove um item espec√≠fico do itiner√°rio de viagem. Requer o ID completo ou um prefixo √∫nico do item.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "item_id_prefix": {
                                "type": "string",
                                "description": "O ID completo ou um prefixo √∫nico do item do itiner√°rio a ser removido.",
                            },
                        },
                        "required": ["item_id_prefix"],
                    },
                },
            },
        ]

    async def _speak_response(self, text: str) -> None:
        """Helper para vocalizar respostas atrav√©s do m√≥dulo TTS principal do GEM."""
        if self.tts_module:
            await self.tts_module.speak(text)
        else:
            self.logger.warning(f"M√≥dulo TTS n√£o dispon√≠vel para falar: '{text}'")

    async def shutdown(self) -> None:
        """Closes the HTTP client and performs cleanup."""
        self.logger.info("TravelManager a ser desligado. A fechar o cliente HTTP.")
        if self._http_client:
            await self._http_client.aclose()
        self.event_manager.unsubscribe("GEM_SHUTDOWN", self._on_gem_shutdown)


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    import json
    
    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestTravelManager")

    # --- Dummy Implementations for testing ---
    class DummyEventManager:
        def __init__(self, logger_instance):
            self.logger = logger_instance
        async def publish(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
            self.logger.info(f"Dummy EventManager: Publicado '{event_type}' com {data}")

    class DummyNotificationManager:
        def __init__(self, logger_instance):
            self.logger = logger_instance
            self._history: List[Dict[str, Any]] = []
        async def add_notification(self, message: str, level: str = NOTIFICATION_INFO, vocalize: bool = True) -> None:
            self.logger.info(f"Dummy Notification: [{level.upper()}] {message} (Vocalize: {vocalize})")
            self._history.append({"message": message, "level": level})
            await asyncio.sleep(0.01)

    class DummyStorage:
        def __init__(self, logger_instance):
            self.logger = logger_instance
            self._data: Dict[str, Any] = {}
        async def get_setting(self, key: str, default: Any = None) -> Any:
            self.logger.info(f"Dummy Storage: A obter '{key}'")
            return self._data.get(key, default)
        async def set_setting(self, key: str, value: Any) -> bool:
            self.logger.info(f"Dummy Storage: A salvar '{key}'")
            self._data[key] = value
            return True

    class DummyTTSModule:
        def __init__(self, logger_instance):
            self.logger = logger_instance
        async def speak(self, text: str) -> None:
            self.logger.info(f"Dummy TTS: A falar: '{text}'")
            await asyncio.sleep(0.01)

    class DummyCommandExecutor:
        def __init__(self, logger_instance):
            self.logger = logger_instance
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
                    'travel_api_key': "MOCK_TRAVEL_KEY",
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
            self.tts_module = DummyTTSModule(logger_instance)
            self.config_manager = DummyConfigManager()
            self.command_executor = DummyCommandExecutor(logger_instance)
            self.storage = DummyStorage(logger_instance)

    # Mock the httpx.AsyncClient for testing without real API calls
    async def mock_httpx_get_travel(*args, **kwargs):
        class MockResponse:
            def __init__(self, status_code, json_data):
                self.status_code = status_code
                self._json_data = json_data
            
            def raise_for_status(self):
                if 400 <= self.status_code < 600:
                    raise httpx.HTTPStatusError(f"HTTP Error: {self.status_code}", request=None, response=self)
            
            def json(self):
                return self._json_data
            
            @property
            def text(self):
                return json.dumps(self._json_data)

        url = args[0]
        params = kwargs.get('params', {})
        
        if "flights/search" in url:
            origin = params.get("origin", "").lower()
            destination = params.get("destination", "").lower()
            departure_date = params.get("departure_date")
            return_date = params.get("return_date")
            limit = params.get("limit", 3)
            
            mock_flights = []
            if "lis" in origin and "par" in destination:
                mock_flights.append(Flight(
                    id="flt-001", airline="AirMock", flight_number="AM100",
                    departure_airport="LIS", arrival_airport="CDG",
                    departure_time=datetime.fromisoformat(f"{departure_date}T08:00:00Z"),
                    arrival_time=datetime.fromisoformat(f"{departure_date}T10:30:00Z"),
                    price=150.00, currency="EUR", booking_url="https://mockair.com/book/am100"
                ).to_dict())
                if return_date:
                     mock_flights.append(Flight(
                        id="flt-002", airline="AirMock", flight_number="AM101",
                        departure_airport="CDG", arrival_airport="LIS",
                        departure_time=datetime.fromisoformat(f"{return_date}T18:00:00Z"),
                        arrival_time=datetime.fromisoformat(f"{return_date}T20:30:00Z"),
                        price=170.00, currency="EUR", booking_url="https://mockair.com/book/am101"
                    ).to_dict())
            return MockResponse(200, {"flights": mock_flights[:limit]})
        
        elif "hotels/search" in url:
            city = params.get("city", "").lower()
            check_in_date = params.get("check_in_date")
            check_out_date = params.get("check_out_date")
            limit = params.get("limit", 3)

            mock_hotels = []
            if "paris" in city:
                mock_hotels.append(Hotel(
                    id="htl-001", name="Hotel Mock Eiffel", city="Paris",
                    check_in_date=datetime.fromisoformat(check_in_date),
                    check_out_date=datetime.fromisoformat(check_out_date),
                    price_per_night=200.00, currency="EUR", stars=4,
                    booking_url="https://mockhotels.com/book/eiffel"
                ).to_dict())
                mock_hotels.append(Hotel(
                    id="htl-002", name="Hostel Central Mock", city="Paris",
                    check_in_date=datetime.fromisoformat(check_in_date),
                    check_out_date=datetime.fromisoformat(check_out_date),
                    price_per_night=80.00, currency="EUR", stars=2,
                    booking_url="https://mockhostels.com/book/central"
                ).to_dict())
            elif "lisboa" in city:
                mock_hotels.append(Hotel(
                    id="htl-003", name="Hotel Mock Tejo", city="Lisboa",
                    check_in_date=datetime.fromisoformat(check_in_date),
                    check_out_date=datetime.fromisoformat(check_out_date),
                    price_per_night=120.00, currency="EUR", stars=3,
                    booking_url="https://mockhotels.com/book/tejo"
                ).to_dict())
            return MockResponse(200, {"hotels": mock_hotels[:limit]})

        return MockResponse(404, {"error": "Not Found"})

    # Patch httpx.AsyncClient.get with our mock for testing
    original_httpx_get_travel = httpx.AsyncClient.get
    httpx.AsyncClient.get = mock_httpx_get_travel

    async def run_travel_manager_tests():
        print("\n--- Iniciando Testes do TravelManager ---")

        dummy_gem = DummyGEM(logger)
        travel_manager = TravelManager(dummy_gem, logger)
        
        travel_manager.register_commands(dummy_gem.command_executor)

        await travel_manager.initialize()

        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        day_after_tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        departure_time_str = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d 10:00")
        arrival_time_str = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d 12:30")

        # --- Teste 1: Pesquisar Voos ---
        print("\n--- Teste 1: Pesquisar Voos ---")
        result_search_flights = await dummy_gem.command_executor.execute(
            "search_flights", origin="LIS", destination="PAR", departure_date=today, passengers=2, limit=1
        )
        print(result_search_flights["output"])
        assert result_search_flights["success"] is True
        assert "Voos encontrados de LIS para PAR" in result_search_flights["output"]
        assert "AirMock Voo AM100" in result_search_flights["output"]

        # --- Teste 2: Pesquisar Hot√©is ---
        print("\n--- Teste 2: Pesquisar Hot√©is ---")
        result_search_hotels = await dummy_gem.command_executor.execute(
            "search_hotels", city="Paris", check_in_date=tomorrow, check_out_date=day_after_tomorrow, guests=2, stars=4, limit=1
        )
        print(result_search_hotels["output"])
        assert result_search_hotels["success"] is True
        assert "Hot√©is encontrados em Paris" in result_search_hotels["output"]
        assert "Hotel Mock Eiffel" in result_search_hotels["output"]
        
        # --- Teste 3: Adicionar Item ao Itiner√°rio (Voo) ---
        print("\n--- Teste 3: Adicionar Item ao Itiner√°rio (Voo) ---")
        flight_details = {
            "airline": "AirMock",
            "flight_number": "AM100",
            "departure_airport": "LIS",
            "arrival_airport": "CDG",
            "price": 150.00,
            "currency": "EUR",
            "booking_url": "https://mockair.com/book/am100"
        }
        result_add_flight_item = await dummy_gem.command_executor.execute(
            "add_itinerary_item",
            name="Voo para Paris",
            item_type="flight",
            start_time=departure_time_str,
            end_time=arrival_time_str,
            location="LIS",
            details_json=json.dumps(flight_details)
        )
        print(result_add_flight_item["output"])
        assert result_add_flight_item["success"] is True
        assert "Item 'Voo para Paris' (tipo: flight) adicionado ao seu itiner√°rio." in result_add_flight_item["output"]

        # --- Teste 4: Adicionar Item ao Itiner√°rio (Hotel) ---
        print("\n--- Teste 4: Adicionar Item ao Itiner√°rio (Hotel) ---")
        hotel_details = {
            "name": "Hotel Mock Eiffel",
            "city": "Paris",
            "price_per_night": 200.00,
            "currency": "EUR",
            "stars": 4,
            "booking_url": "https://mockhotels.com/book/eiffel"
        }
        result_add_hotel_item = await dummy_gem.command_executor.execute(
            "add_itinerary_item",
            name="Estadia em Hotel Paris",
            item_type="hotel",
            start_time=(datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d 15:00"),
            end_time=(datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d 11:00"),
            location="Paris",
            details_json=json.dumps(hotel_details)
        )
        print(result_add_hotel_item["output"])
        assert result_add_hotel_item["success"] is True
        assert "Item 'Estadia em Hotel Paris' (tipo: hotel) adicionado ao seu itiner√°rio." in result_add_hotel_item["output"]


        # --- Teste 5: Listar Itiner√°rio ---
        print("\n--- Teste 5: Listar Itiner√°rio ---")
        result_list_itinerary = await dummy_gem.command_executor.execute("list_itinerary")
        print(result_list_itinerary["output"])
        assert result_list_itinerary["success"] is True
        assert "Voo para Paris" in result_list_itinerary["output"]
        assert "Estadia em Hotel Paris" in result_list_itinerary["output"]
        assert "Seu Itiner√°rio de Viagem:" in result_list_itinerary["output"]

        # --- Teste 6: Remover Item do Itiner√°rio ---
        print("\n--- Teste 6: Remover Item do Itiner√°rio ---")
        item_id_to_remove = next(i.id for i in travel_manager._itineraries.values() if i.name == "Voo para Paris")
        result_remove_item = await dummy_gem.command_executor.execute(
            "remove_itinerary_item", item_id_prefix=item_id_to_remove[:8]
        )
        print(result_remove_item["output"])
        assert result_remove_item["success"] is True
        assert "Item 'Voo para Paris' (ID:" in result_remove_item["output"] and "removido do seu itiner√°rio." in result_remove_item["output"]
        
        # Verify removal
        assert item_id_to_remove not in travel_manager._itineraries

        # --- Teste 7: Pesquisar Voos Sem Resultados ---
        print("\n--- Teste 7: Pesquisar Voos Sem Resultados ---")
        result_no_flights = await dummy_gem.command_executor.execute(
            "search_flights", origin="XYZ", destination="ABC", departure_date=today
        )
        print(result_no_flights["output"])
        assert result_no_flights["success"] is True
        assert "N√£o foram encontrados voos para XYZ para ABC na data especificada." in result_no_flights["output"]

        print("\n--- Testes do TravelManager conclu√≠dos com sucesso. ---")
        await travel_manager.shutdown()
        
        # Restore original httpx.AsyncClient.get
        httpx.AsyncClient.get = original_httpx_get_travel

    asyncio.run(run_travel_manager_tests())

