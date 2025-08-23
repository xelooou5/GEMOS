#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Email Manager (core/email_manager.py)
Manages email functionalities, including checking inbox, reading, and composing.

Responsibilities
----------------
- Connect to IMAP server to check for new emails.
- Retrieve and parse email details (sender, subject, body).
- Manage email credentials securely.
- Expose email capabilities as tools for the LLM.
- Publish email-related events.
- Integrate with NotificationManager for alerts.
"""

from __future__ import annotations

import asyncio
import logging
import imaplib # Para IMAP
import email # Para parsing de e-mails
from email.header import decode_header
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Awaitable

from core.plugins import BasePlugin, CommandExecutor, GEMVoiceAssistant
from core.notification_manager import NotificationManager, NOTIFICATION_INFO, NOTIFICATION_WARNING, NOTIFICATION_ERROR

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

# --- Dataclass para Email ---
@dataclass
class EmailMessage:
    uid: str # Unique ID from IMAP server
    sender: str
    subject: str
    date: datetime
    body_plain: Optional[str] = None
    body_html: Optional[str] = None
    is_read: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uid": self.uid,
            "sender": self.sender,
            "subject": self.subject,
            "date": self.date.isoformat(),
            "body_plain": self.body_plain,
            "body_html": self.body_html,
            "is_read": self.is_read,
        }

# --- Email Manager como um Plugin ---
class EmailManager(BasePlugin):
    """
    Manages email functionalities for GEM OS, acting as a plugin.
    """
    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("EmailManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.tts_module: TTSModule = gem_instance.tts_module
        self.config_manager: ConfigManager = gem_instance.config_manager

        # Email account settings from config or environment variables
        self._email_address = os.getenv("EMAIL_ADDRESS", self.config_manager.get_config().general.email_address)
        self._email_password = os.getenv("EMAIL_PASSWORD", self.config_manager.get_config().general.email_password)
        self._imap_server = self.config_manager.get_config().general.imap_server
        self._imap_port = self.config_manager.get_config().general.imap_port
        self._check_interval_seconds = self.config_manager.get_config().general.email_check_interval_seconds

        self._imap_connection: Optional[imaplib.IMAP4_SSL] = None
        self._check_task: Optional[asyncio.Task] = None
        self._is_logged_in: bool = False

        self.logger.info(f"EmailManager configurado para: {self._email_address} (IMAP: {self._imap_server}:{self._imap_port})")

        if not self._email_address or not self._email_password:
            self.logger.warning("Credenciais de e-mail ausentes. O gerenciador de e-mail pode não funcionar.")

    async def initialize(self) -> None:
        """Starts the background task for periodically checking new emails."""
        if not self._check_task and self._email_address and self._email_password:
            self._check_task = asyncio.create_task(self._periodic_email_check())
            self.logger.info("Verificação periódica de e-mail iniciada.")
        elif not (self._email_address and self._email_password):
             self.logger.warning("Não foi possível iniciar a verificação periódica de e-mail devido a credenciais ausentes.")

        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self.logger.info("EmailManager inicializado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event to gracefully disconnect from IMAP."""
        self.logger.info("Recebido GEM_SHUTDOWN. A desconectar do servidor IMAP.")
        await self.shutdown()

    async def _connect_and_login(self) -> bool:
        """Connects to the IMAP server and logs in."""
        if self._is_logged_in:
            return True

        if not self._email_address or not self._email_password:
            self.logger.error("Credenciais de e-mail não fornecidas. Não é possível conectar.")
            await self.notification_manager.add_notification(
                "Falha na conexão de e-mail: Credenciais ausentes.", level=NOTIFICATION_ERROR
            )
            return False

        try:
            self.logger.info(f"A conectar a IMAP em {self._imap_server}:{self._imap_port}...")
            self._imap_connection = await asyncio.to_thread(imaplib.IMAP4_SSL, self._imap_server, self._imap_port)
            self.logger.info("Conectado ao servidor IMAP. A iniciar login...")
            await asyncio.to_thread(self._imap_connection.login, self._email_address, self._email_password)
            self._is_logged_in = True
            self.logger.info(f"Login IMAP bem-sucedido para {self._email_address}.")
            return True
        except imaplib.IMAP4.error as e:
            self.logger.error(f"Erro de login IMAP para {self._email_address}: {e}", exc_info=True)
            await self.notification_manager.add_notification(
                f"Falha no login de e-mail para {self._email_address}: {e}", level=NOTIFICATION_ERROR
            )
            return False
        except Exception as e:
            self.logger.error(f"Erro inesperado na conexão/login IMAP: {e}", exc_info=True)
            await self.notification_manager.add_notification(
                f"Erro inesperado na conexão de e-mail para {self._email_address}.", level=NOTIFICATION_ERROR
            )
            return False

    async def _disconnect(self) -> None:
        """Disconnects from the IMAP server."""
        if self._imap_connection and self._is_logged_in:
            try:
                self.logger.info("A desconectar do IMAP...")
                await asyncio.to_thread(self._imap_connection.logout)
                self._is_logged_in = False
                self._imap_connection = None
                self.logger.info("Desconectado do servidor IMAP.")
            except Exception as e:
                self.logger.error(f"Erro ao desconectar do IMAP: {e}", exc_info=True)

    async def _periodic_email_check(self) -> None:
        """Periodically checks for new emails."""
        self.logger.debug("Loop de verificação periódica de e-mail iniciado.")
        while True:
            try:
                await self._check_for_new_emails()
                await asyncio.sleep(self._check_interval_seconds)
            except asyncio.CancelledError:
                self.logger.info("Tarefa de verificação periódica de e-mail cancelada.")
                break
            except Exception as e:
                self.logger.error(f"Erro no loop de verificação de e-mail: {e}", exc_info=True)
                await asyncio.sleep(self._check_interval_seconds * 2) # Espera mais tempo em caso de erro

    async def _check_for_new_emails(self) -> None:
        """Checks the inbox for unread emails."""
        if not await self._connect_and_login():
            return

        try:
            await asyncio.to_thread(self._imap_connection.select, "inbox")
            status, email_ids = await asyncio.to_thread(self._imap_connection.search, None, "UNSEEN")
            if status != "OK":
                self.logger.error(f"Falha ao pesquisar por e-mails não lidos: {email_ids}")
                return

            email_id_list = email_ids[0].split()
            if email_id_list:
                self.logger.info(f"Encontrados {len(email_id_list)} e-mails não lidos.")
                await self.notification_manager.add_notification(
                    f"Você tem {len(email_id_list)} novos e-mails!", level=NOTIFICATION_INFO, vocalize=True
                )
                await self.tts_module.speak(f"Você tem {len(email_id_list)} novos e-mails.")
                for uid_byte in email_id_list:
                    uid = uid_byte.decode('utf-8')
                    # Não vamos buscar o corpo completo aqui para evitar lentidão, apenas detalhes essenciais
                    status, msg_data = await asyncio.to_thread(self._imap_connection.fetch, uid, "(RFC822)")
                    if status == "OK":
                        raw_email = msg_data[0][1]
                        msg = email.message_from_bytes(raw_email)
                        sender = self._decode_header_part(msg.get("From", "Desconhecido"))
                        subject = self._decode_header_part(msg.get("Subject", "Sem Assunto"))
                        date_str = msg.get("Date")
                        date_obj = datetime.now()
                        try:
                            date_obj = email.utils.parsedate_to_datetime(date_str) if date_str else datetime.now()
                        except ValueError:
                            self.logger.warning(f"Não foi possível analisar a data do e-mail: {date_str}. A usar a data atual.")

                        new_email = EmailMessage(
                            uid=uid,
                            sender=sender,
                            subject=subject,
                            date=date_obj,
                            is_read=False # Inicialmente não lido
                        )
                        self.logger.info(f"Novo E-mail: De='{new_email.sender}', Assunto='{new_email.subject}'")
                        await self.event_manager.publish("NEW_EMAIL_RECEIVED", new_email.to_dict())
            else:
                self.logger.debug("Nenhum e-mail não lido encontrado.")
            
            # Garante que a conexão é mantida viva para a próxima verificação
            await asyncio.to_thread(self._imap_connection.noop)

        except imaplib.IMAP4.error as e:
            self.logger.error(f"Erro IMAP ao verificar e-mails: {e}", exc_info=True)
            self._is_logged_in = False # Marcar como desconectado para tentar reconectar
        except Exception as e:
            self.logger.error(f"Erro inesperado ao verificar e-mails: {e}", exc_info=True)
            # Pode ser útil tentar desconectar e reconectar em caso de erro inesperado
            await self._disconnect()


    async def _read_latest_emails(self, count: int = 1) -> List[EmailMessage]:
        """Reads the latest 'count' emails from the inbox, marking them as seen."""
        if not await self._connect_and_login():
            return []

        try:
            await asyncio.to_thread(self._imap_connection.select, "inbox")
            status, email_ids = await asyncio.to_thread(self._imap_connection.search, None, "ALL")
            if status != "OK":
                self.logger.error(f"Falha ao pesquisar por e-mails: {email_ids}")
                return []

            email_id_list = email_ids[0].split()
            email_id_list.reverse() # Mais recente primeiro

            read_emails: List[EmailMessage] = []
            for uid_byte in email_id_list[:count]:
                uid = uid_byte.decode('utf-8')
                status, msg_data = await asyncio.to_thread(self._imap_connection.fetch, uid, "(RFC822)")
                if status == "OK":
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    sender = self._decode_header_part(msg.get("From", "Desconhecido"))
                    subject = self._decode_header_part(msg.get("Subject", "Sem Assunto"))
                    date_str = msg.get("Date")
                    date_obj = datetime.now()
                    try:
                        date_obj = email.utils.parsedate_to_datetime(date_str) if date_str else datetime.now()
                    except ValueError:
                        self.logger.warning(f"Não foi possível analisar a data do e-mail: {date_str}. A usar a data atual.")

                    body_plain, body_html = self._parse_email_body(msg)

                    read_email = EmailMessage(
                        uid=uid,
                        sender=sender,
                        subject=subject,
                        date=date_obj,
                        body_plain=body_plain,
                        body_html=body_html,
                        is_read=True
                    )
                    read_emails.append(read_email)
                    # Marcar o e-mail como lido (SEEN)
                    await asyncio.to_thread(self._imap_connection.store, uid_byte, '+FLAGS', '\\Seen')
                    await self.event_manager.publish("EMAIL_READ", read_email.to_dict())
            return read_emails
        except imaplib.IMAP4.error as e:
            self.logger.error(f"Erro IMAP ao ler e-mails: {e}", exc_info=True)
            self._is_logged_in = False
            return []
        except Exception as e:
            self.logger.error(f"Erro inesperado ao ler e-mails: {e}", exc_info=True)
            await self._disconnect()
            return []

    def _decode_header_part(self, header: str) -> str:
        """Decodes an email header part (e.g., Subject, From)."""
        decoded_headers = decode_header(header)
        decoded_string = ""
        for part, charset in decoded_headers:
            if isinstance(part, bytes):
                try:
                    decoded_string += part.decode(charset if charset else "utf-8")
                except (UnicodeDecodeError, TypeError):
                    decoded_string += part.decode("latin-1", errors="replace") # Fallback
            else:
                decoded_string += part
        return decoded_string

    def _parse_email_body(self, msg: email.message.Message) -> Tuple[Optional[str], Optional[str]]:
        """Parses the email message to extract plain text and HTML bodies."""
        plain_text_body = None
        html_body = None

        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdisposition = part.get("Content-Disposition")

                # Ignorar anexos
                if ctype == "text/plain" and "attachment" not in (cdisposition or ""):
                    try:
                        plain_text_body = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
                    except Exception as e:
                        self.logger.warning(f"Erro ao descodificar parte de texto simples: {e}")
                elif ctype == "text/html" and "attachment" not in (cdisposition or ""):
                    try:
                        html_body = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
                    except Exception as e:
                        self.logger.warning(f"Erro ao descodificar parte HTML: {e}")
                
                if plain_text_body and html_body: # Já encontrámos ambos
                    break
        else: # Não multipart
            ctype = msg.get_content_type()
            if ctype == "text/plain":
                try:
                    plain_text_body = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='replace')
                except Exception as e:
                    self.logger.warning(f"Erro ao descodificar parte de texto simples (não multipart): {e}")
            elif ctype == "text/html":
                try:
                    html_body = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='replace')
                except Exception as e:
                    self.logger.warning(f"Erro ao descodificar parte HTML (não multipart): {e}")

        # Prioriza texto simples se ambos estiverem presentes
        return plain_text_body, html_body


    # --------------------------------------------------------------------- Commands

    async def _check_new_emails_command(self) -> Dict[str, Any]:
        """
        Verifica a caixa de entrada para novos e-mails não lidos e vocaliza o resumo.
        """
        if not (self._email_address and self._email_password):
            message = "As credenciais de e-mail não estão configuradas."
            await self._speak_response(message)
            return {"success": False, "output": "", "error": message}

        self.logger.info("A verificar novos e-mails...")
        await self._check_for_new_emails() # Isso já publica notificações e fala
        
        message = "Verificação de novos e-mails concluída. As notificações foram enviadas, se houver novos e-mails."
        return {"success": True, "output": message, "error": None}

    async def _read_emails_command(self, count: int = 1) -> Dict[str, Any]:
        """
        Lê os 'count' e-mails mais recentes da caixa de entrada e os vocaliza.
        """
        if not (self._email_address and self._email_password):
            message = "As credenciais de e-mail não estão configuradas."
            await self._speak_response(message)
            return {"success": False, "output": "", "error": message}

        self.logger.info(f"A ler os {count} e-mails mais recentes...")
        emails_to_read = await self._read_latest_emails(count)

        if not emails_to_read:
            message = "Nenhum e-mail para ler na caixa de entrada."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}
        
        output_lines = ["E-mails lidos:"]
        for i, email_msg in enumerate(emails_to_read):
            summary = f"De: {email_msg.sender}. Assunto: {email_msg.subject}. "
            body_preview = (email_msg.body_plain or email_msg.body_html or "Sem corpo.").split('\n')[0][:100] + "..."
            summary += f"Conteúdo: {body_preview}"
            
            output_lines.append(f"{i+1}. {summary}")
            
            await self._speak_response(f"E-mail {i+1}: De {email_msg.sender}. Assunto: {email_msg.subject}. Mensagem: {body_preview}")
            await self.notification_manager.add_notification(
                f"E-mail lido: De {email_msg.sender}, Assunto: {email_msg.subject}", level=NOTIFICATION_INFO, vocalize=False
            )
        
        message = "\n".join(output_lines)
        return {"success": True, "output": message, "error": None}

    # Futuras funcionalidades: Compor e Enviar E-mail, Responder, Apagar, etc.
    # Requereria SMTP e mais lógica.

    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers email management commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin EmailManager...")
        executor.register_command("check_new_emails", self._check_new_emails_command)
        executor.register_command("read_emails", self._read_emails_command)
        self.logger.info("Comandos EmailManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for email features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "check_new_emails",
                    "description": "Verifica a caixa de entrada para novos e-mails não lidos e notifica o usuário sobre quantos foram encontrados. Não lê o conteúdo completo.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_emails",
                    "description": "Lê os e-mails mais recentes da caixa de entrada do usuário. Por padrão, lê apenas o e-mail mais recente. Pode especificar quantos e-mails ler.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "count": {
                                "type": "integer",
                                "description": "O número de e-mails mais recentes a serem lidos. Padrão para 1.",
                                "default": 1
                            }
                        },
                        "required": [],
                    },
                },
            },
            # Esquemas de ferramentas para compor, enviar, responder, apagar, etc., podem ser adicionados aqui.
        ]

    async def _speak_response(self, text: str) -> None:
        """Helper para vocalizar respostas através do módulo TTS principal do GEM."""
        if self.tts_module:
            await self.tts_module.speak(text)
        else:
            self.logger.warning(f"Módulo TTS não disponível para falar: '{text}'")

    async def shutdown(self) -> None:
        """Disconnects from IMAP and stops any background tasks."""
        self.logger.info("EmailManager a ser desligado.")
        if self._check_task:
            self._check_task.cancel()
            self._check_task = None
        await self._disconnect()
        self.event_manager.unsubscribe("GEM_SHUTDOWN", self._on_gem_shutdown)


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestEmailManager")

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
                    'email_address': os.getenv("TEST_EMAIL_ADDRESS", "test@example.com"),
                    'email_password': os.getenv("TEST_EMAIL_PASSWORD", "password123"),
                    'imap_server': os.getenv("TEST_IMAP_SERVER", "imap.example.com"),
                    'imap_port': int(os.getenv("TEST_IMAP_PORT", 993)),
                    'email_check_interval_seconds': 5,
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
            self.storage = type('DummyStorage', (), {})() # Not used directly

    # Mock the imaplib functions for testing without a real IMAP server
    class MockIMAP4_SSL:
        def __init__(self, host, port):
            logger.info(f"MockIMAP4_SSL: Conectado a {host}:{port}")
            self.host = host
            self.port = port
            self.logged_in = False
            self.selected_mailbox = None
            self.mock_emails = { # UID -> raw_email_bytes
                b'1': b'From: sender1@example.com\r\nSubject: Teste 1 (Nao Lido)\r\nDate: Thu, 22 Aug 2025 10:00:00 -0300\r\n\r\nEste e o corpo do email 1.',
                b'2': b'From: sender2@example.com\r\nSubject: Teste 2 (Lido)\r\nDate: Thu, 22 Aug 2025 10:05:00 -0300\r\n\r\nEste e o corpo do email 2.',
                b'3': b'From: sender3@example.com\r\nSubject: Teste 3 (Nao Lido)\r\nDate: Thu, 22 Aug 2025 10:10:00 -0300\r\n\r\nCorpo do email 3, com informacoes importantes.',
            }
            self.unseen_uids = [b'1', b'3']
            self.all_uids = [b'1', b'2', b'3']
            self.flags = {b'1': [], b'2': [b'\\Seen'], b'3': []}

        def login(self, user, password):
            logger.info(f"MockIMAP4_SSL: Tentativa de login para {user}")
            if user == "test@example.com" and password == "password123":
                self.logged_in = True
                return "OK", []
            raise imaplib.IMAP4.error("Login falhou")

        def logout(self):
            logger.info("MockIMAP4_SSL: Logout")
            self.logged_in = False
            return "OK", []
        
        def select(self, mailbox):
            if not self.logged_in: raise imaplib.IMAP4.error("Nao logado")
            self.selected_mailbox = mailbox
            logger.info(f"MockIMAP4_SSL: Selecionada mailbox {mailbox}")
            return "OK", [b'3'] # dummy count

        def search(self, charset, *criteria):
            if not self.logged_in or self.selected_mailbox != "inbox": raise imaplib.IMAP4.error("Nao logado ou mailbox nao selecionada")
            if "UNSEEN" in criteria:
                logger.info(f"MockIMAP4_SSL: Pesquisando UNSEEN. Retornando: {self.unseen_uids}")
                return "OK", [b' '.join(self.unseen_uids)]
            if "ALL" in criteria:
                logger.info(f"MockIMAP4_SSL: Pesquisando ALL. Retornando: {self.all_uids}")
                return "OK", [b' '.join(self.all_uids)]
            return "OK", [b'']

        def fetch(self, uid, *criteria):
            if not self.logged_in or self.selected_mailbox != "inbox": raise imaplib.IMAP4.error("Nao logado ou mailbox nao selecionada")
            raw_email = self.mock_emails.get(uid)
            if raw_email:
                logger.info(f"MockIMAP4_SSL: Fetching email UID {uid}")
                return "OK", [[(b'1 (RFC822)', raw_email), b')']] # IMAP format
            return "NO", []
        
        def store(self, uid, command, flags):
            if not self.logged_in or self.selected_mailbox != "inbox": raise imaplib.IMAP4.error("Nao logado ou mailbox nao selecionada")
            if command == '+FLAGS' and b'\\Seen' in flags:
                if uid in self.unseen_uids:
                    self.unseen_uids.remove(uid)
                self.flags[uid].append(b'\\Seen')
                logger.info(f"MockIMAP4_SSL: Marcado UID {uid} como lido.")
            return "OK", []
        
        def noop(self):
            if not self.logged_in: raise imaplib.IMAP4.error("Nao logado")
            return "OK", []

    # Patch imaplib.IMAP4_SSL with our mock for testing
    original_imap4_ssl = imaplib.IMAP4_SSL
    imaplib.IMAP4_SSL = MockIMAP4_SSL

    async def run_email_manager_tests():
        print("\n--- Iniciando Testes do EmailManager ---")

        dummy_gem = DummyGEM(logger)
        email_manager = EmailManager(dummy_gem, logger)
        
        email_manager.register_commands(dummy_gem.command_executor)

        # Set environment variables for dummy config (or modify DummyConfigManager directly)
        os.environ["TEST_EMAIL_ADDRESS"] = "test@example.com"
        os.environ["TEST_EMAIL_PASSWORD"] = "password123"
        os.environ["TEST_IMAP_SERVER"] = "imap.example.com"
        os.environ["TEST_IMAP_PORT"] = "993"
        
        # Reload config to pick up env vars for the manager being tested
        email_manager.config_manager = DummyConfigManager() 
        email_manager._email_address = email_manager.config_manager.get_config().general.email_address
        email_manager._email_password = email_manager.config_manager.get_config().general.email_password
        email_manager._imap_server = email_manager.config_manager.get_config().general.imap_server
        email_manager._imap_port = email_manager.config_manager.get_config().general.imap_port

        await email_manager.initialize() # Inicia a verificação periódica

        print("\n--- Teste 1: Verificar novos e-mails ---")
        result_check = await dummy_gem.command_executor.execute("check_new_emails")
        print(result_check["output"])
        assert result_check["success"] is True
        assert any(n["message"] == "Você tem 2 novos e-mails!" for n in dummy_gem.notification_manager._history)

        print("\n--- Teste 2: Ler o e-mail mais recente ---")
        result_read_one = await dummy_gem.command_executor.execute("read_emails", count=1)
        print(result_read_one["output"])
        assert result_read_one["success"] is True
        assert "Assunto: Teste 3 (Nao Lido)" in result_read_one["output"]
        # Após a leitura, o email 3 deve ter sido marcado como lido e removido da lista UNSEEN do mock
        assert b'3' not in email_manager._imap_connection.unseen_uids

        print("\n--- Teste 3: Ler todos os e-mails ---")
        # Deve agora ler Teste 1 (que era o outro não lido) e Teste 2 (que já era lido)
        result_read_all = await dummy_gem.command_executor.execute("read_emails", count=3)
        print(result_read_all["output"])
        assert result_read_all["success"] is True
        assert "Assunto: Teste 1 (Nao Lido)" in result_read_all["output"]
        assert "Assunto: Teste 2 (Lido)" in result_read_all["output"]
        assert b'1' not in email_manager._imap_connection.unseen_uids # Email 1 também deve estar lido agora

        print("\n--- Teste 4: Verificar novamente (deve reportar 0 novos) ---")
        dummy_gem.notification_manager._history.clear() # Limpa o histórico para esta verificação
        result_check_again = await dummy_gem.command_executor.execute("check_new_emails")
        print(result_check_again["output"])
        assert result_check_again["success"] is True
        assert not any("novos e-mails!" in n["message"] for n in dummy_gem.notification_manager._history) # Nenhuma notificação de novos e-mails

        print("\n--- Testes do EmailManager concluídos com sucesso. ---")
        await email_manager.shutdown()
        
        # Restore original imaplib.IMAP4_SSL
        imaplib.IMAP4_SSL = original_imap4_ssl

    asyncio.run(run_email_manager_tests())

