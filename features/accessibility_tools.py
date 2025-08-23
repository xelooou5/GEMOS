#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Accessibility Tools
Comprehensive accessibility features for people with disabilities
"""

import asyncio
import logging
import subprocess
import time
from typing import Dict, Any, List, Optional, Tuple
import platform
from pathlib import Path


class ScreenReader:
    """Screen reader functionality."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.is_available = False
        self.reader_command = None
        
        # Detect available screen readers
        self._detect_screen_reader()
    
    def _detect_screen_reader(self):
        """Detect available screen reader."""
        system = platform.system()
        
        if system == "Linux":
            # Try espeak or spd-say
            for cmd in ['spd-say', 'espeak']:
                try:
                    subprocess.run([cmd, '--version'], 
                                 capture_output=True, timeout=5)
                    self.reader_command = cmd
                    self.is_available = True
                    self.logger.info(f"Screen reader available: {cmd}")
                    break
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
        
        elif system == "Darwin":  # macOS
            self.reader_command = 'say'
            self.is_available = True
        
        elif system == "Windows":
            # Windows has built-in narrator
            self.reader_command = 'narrator'
            self.is_available = True
    
    async def read_text(self, text: str) -> bool:
        """Read text aloud using screen reader."""
        if not self.is_available or not text.strip():
            return False
        
        try:
            if self.reader_command in ['spd-say', 'espeak']:
                cmd = [self.reader_command, text]
            elif self.reader_command == 'say':
                cmd = ['say', text]
            else:
                return False
            
            # Execute in background
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            return process.returncode == 0
        
        except Exception as e:
            self.logger.error(f"Screen reader error: {e}")
            return False


class MagnificationTool:
    """Screen magnification functionality."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.current_zoom = 1.0
        self.max_zoom = 5.0
        self.min_zoom = 0.5
        self.zoom_step = 0.25
    
    async def zoom_in(self) -> Tuple[bool, str]:
        """Increase screen magnification."""
        if self.current_zoom >= self.max_zoom:
            return False, f"Zoom máximo atingido: {self.current_zoom}x"
        
        self.current_zoom += self.zoom_step
        success = await self._apply_zoom()
        
        if success:
            return True, f"Zoom aumentado para {self.current_zoom}x"
        else:
            self.current_zoom -= self.zoom_step  # Revert
            return False, "Erro ao aplicar zoom"
    
    async def zoom_out(self) -> Tuple[bool, str]:
        """Decrease screen magnification."""
        if self.current_zoom <= self.min_zoom:
            return False, f"Zoom mínimo atingido: {self.current_zoom}x"
        
        self.current_zoom -= self.zoom_step
        success = await self._apply_zoom()
        
        if success:
            return True, f"Zoom reduzido para {self.current_zoom}x"
        else:
            self.current_zoom += self.zoom_step  # Revert
            return False, "Erro ao aplicar zoom"
    
    async def reset_zoom(self) -> Tuple[bool, str]:
        """Reset zoom to normal."""
        self.current_zoom = 1.0
        success = await self._apply_zoom()
        
        if success:
            return True, "Zoom resetado para normal"
        else:
            return False, "Erro ao resetar zoom"
    
    async def _apply_zoom(self) -> bool:
        """Apply zoom setting to system."""
        try:
            system = platform.system()
            
            if system == "Linux":
                # Try using xrandr for display scaling
                try:
                    process = await asyncio.create_subprocess_exec(
                        'xrandr', '--output', 'eDP-1', '--scale', f'{self.current_zoom}x{self.current_zoom}',
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await process.wait()
                    return process.returncode == 0
                except Exception:
                    # Fallback: try with different output names
                    for output in ['HDMI-1', 'VGA-1', 'DP-1']:
                        try:
                            process = await asyncio.create_subprocess_exec(
                                'xrandr', '--output', output, '--scale', f'{self.current_zoom}x{self.current_zoom}',
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE
                            )
                            await process.wait()
                            if process.returncode == 0:
                                return True
                        except Exception:
                            continue
                    return False
            
            elif system == "Darwin":  # macOS
                # Use AppleScript for zoom
                script = f'''
                tell application "System Events"
                    key code 28 using {{command down, option down}}
                end tell
                '''
                process = await asyncio.create_subprocess_exec(
                    'osascript', '-e', script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.wait()
                return process.returncode == 0
            
            elif system == "Windows":
                # Use Windows Magnifier
                process = await asyncio.create_subprocess_exec(
                    'magnify.exe',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.wait()
                return process.returncode == 0
            
            return False
        
        except Exception as e:
            self.logger.error(f"Zoom application error: {e}")
            return False


class HighContrastMode:
    """High contrast display mode."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.is_enabled = False
    
    async def toggle(self) -> Tuple[bool, str]:
        """Toggle high contrast mode."""
        if self.is_enabled:
            return await self.disable()
        else:
            return await self.enable()
    
    async def enable(self) -> Tuple[bool, str]:
        """Enable high contrast mode."""
        try:
            system = platform.system()
            
            if system == "Linux":
                # Try to set high contrast theme
                success = await self._set_gtk_theme("HighContrast")
                if success:
                    self.is_enabled = True
                    return True, "Modo alto contraste ativado"
                else:
                    return False, "Erro ao ativar alto contraste"
            
            elif system == "Windows":
                # Use Windows high contrast
                process = await asyncio.create_subprocess_exec(
                    'powershell', '-Command', 
                    'Set-ItemProperty -Path "HKCU:\\Control Panel\\Accessibility\\HighContrast" -Name "Flags" -Value "126"',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.wait()
                
                if process.returncode == 0:
                    self.is_enabled = True
                    return True, "Modo alto contraste ativado"
                else:
                    return False, "Erro ao ativar alto contraste"
            
            else:
                return False, "Alto contraste não suportado neste sistema"
        
        except Exception as e:
            self.logger.error(f"High contrast enable error: {e}")
            return False, f"Erro: {e}"
    
    async def disable(self) -> Tuple[bool, str]:
        """Disable high contrast mode."""
        try:
            system = platform.system()
            
            if system == "Linux":
                # Restore default theme
                success = await self._set_gtk_theme("Adwaita")
                if success:
                    self.is_enabled = False
                    return True, "Modo alto contraste desativado"
                else:
                    return False, "Erro ao desativar alto contraste"
            
            elif system == "Windows":
                # Disable Windows high contrast
                process = await asyncio.create_subprocess_exec(
                    'powershell', '-Command', 
                    'Set-ItemProperty -Path "HKCU:\\Control Panel\\Accessibility\\HighContrast" -Name "Flags" -Value "122"',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.wait()
                
                if process.returncode == 0:
                    self.is_enabled = False
                    return True, "Modo alto contraste desativado"
                else:
                    return False, "Erro ao desativar alto contraste"
            
            else:
                return False, "Alto contraste não suportado neste sistema"
        
        except Exception as e:
            self.logger.error(f"High contrast disable error: {e}")
            return False, f"Erro: {e}"
    
    async def _set_gtk_theme(self, theme_name: str) -> bool:
        """Set GTK theme."""
        try:
            process = await asyncio.create_subprocess_exec(
                'gsettings', 'set', 'org.gnome.desktop.interface', 'gtk-theme', theme_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            return process.returncode == 0
        
        except Exception:
            return False


class KeyboardNavigation:
    """Enhanced keyboard navigation."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.sticky_keys_enabled = False
        self.filter_keys_enabled = False
    
    async def enable_sticky_keys(self) -> Tuple[bool, str]:
        """Enable sticky keys."""
        try:
            system = platform.system()
            
            if system == "Linux":
                # Enable sticky keys via gsettings
                process = await asyncio.create_subprocess_exec(
                    'gsettings', 'set', 'org.gnome.desktop.a11y.keyboard', 'stickykeys-enable', 'true',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.wait()
                
                if process.returncode == 0:
                    self.sticky_keys_enabled = True
                    return True, "Teclas aderentes ativadas"
                else:
                    return False, "Erro ao ativar teclas aderentes"
            
            else:
                return False, "Teclas aderentes não suportadas neste sistema"
        
        except Exception as e:
            self.logger.error(f"Sticky keys error: {e}")
            return False, f"Erro: {e}"
    
    async def enable_filter_keys(self) -> Tuple[bool, str]:
        """Enable filter keys (slow keys)."""
        try:
            system = platform.system()
            
            if system == "Linux":
                # Enable filter keys via gsettings
                process = await asyncio.create_subprocess_exec(
                    'gsettings', 'set', 'org.gnome.desktop.a11y.keyboard', 'slowkeys-enable', 'true',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.wait()
                
                if process.returncode == 0:
                    self.filter_keys_enabled = True
                    return True, "Teclas lentas ativadas"
                else:
                    return False, "Erro ao ativar teclas lentas"
            
            else:
                return False, "Teclas lentas não suportadas neste sistema"
        
        except Exception as e:
            self.logger.error(f"Filter keys error: {e}")
            return False, f"Erro: {e}"


class AccessibilityTools:
    """Main accessibility tools manager."""
    
    def __init__(self, gem_assistant, logger: Optional[logging.Logger] = None):
        self.gem = gem_assistant
        self.logger = logger or logging.getLogger("AccessibilityTools")
        
        # Initialize tools
        self.screen_reader = ScreenReader(self.logger)
        self.magnification = MagnificationTool(self.logger)
        self.high_contrast = HighContrastMode(self.logger)
        self.keyboard_nav = KeyboardNavigation(self.logger)
        
        # Settings
        self.auto_read_enabled = True
        self.voice_feedback_enabled = True
    
    async def initialize(self):
        """Initialize accessibility tools."""
        self.logger.info("Initializing accessibility tools...")
        
        # Check system capabilities
        capabilities = await self._check_capabilities()
        
        self.logger.info(f"Accessibility capabilities: {capabilities}")
        self.logger.info("Accessibility tools initialized")
    
    async def _check_capabilities(self) -> Dict[str, bool]:
        """Check system accessibility capabilities."""
        capabilities = {
            "screen_reader": self.screen_reader.is_available,
            "magnification": True,  # Basic zoom always available
            "high_contrast": True,  # Theme switching usually available
            "keyboard_navigation": True  # Basic keyboard features available
        }
        
        return capabilities
    
    async def read_screen(self) -> str:
        """Read current screen content."""
        try:
            # Try to get window title and content
            window_info = await self._get_active_window_info()
            
            if window_info:
                text_to_read = f"Janela ativa: {window_info['title']}"
                
                if window_info.get('content'):
                    text_to_read += f". Conteúdo: {window_info['content'][:200]}"
                
                # Read using screen reader
                if self.screen_reader.is_available:
                    await self.screen_reader.read_text(text_to_read)
                
                return text_to_read
            else:
                message = "Não foi possível ler o conteúdo da tela"
                
                if self.screen_reader.is_available:
                    await self.screen_reader.read_text(message)
                
                return message
        
        except Exception as e:
            self.logger.error(f"Screen reading error: {e}")
            return "Erro ao ler a tela"
    
    async def _get_active_window_info(self) -> Optional[Dict[str, str]]:
        """Get information about the active window."""
        try:
            system = platform.system()
            
            if system == "Linux":
                # Use xdotool to get active window info
                process = await asyncio.create_subprocess_exec(
                    'xdotool', 'getactivewindow', 'getwindowname',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                
                if process.returncode == 0:
                    title = stdout.decode().strip()
                    return {"title": title, "content": ""}
            
            return None
        
        except Exception as e:
            self.logger.error(f"Window info error: {e}")
            return None
    
    async def zoom_in(self) -> str:
        """Increase screen magnification."""
        success, message = await self.magnification.zoom_in()
        
        if self.voice_feedback_enabled and self.gem.tts_module:
            await self.gem.tts_module.speak(message)
        
        return message
    
    async def zoom_out(self) -> str:
        """Decrease screen magnification."""
        success, message = await self.magnification.zoom_out()
        
        if self.voice_feedback_enabled and self.gem.tts_module:
            await self.gem.tts_module.speak(message)
        
        return message
    
    async def reset_zoom(self) -> str:
        """Reset screen magnification."""
        success, message = await self.magnification.reset_zoom()
        
        if self.voice_feedback_enabled and self.gem.tts_module:
            await self.gem.tts_module.speak(message)
        
        return message
    
    async def toggle_high_contrast(self) -> str:
        """Toggle high contrast mode."""
        success, message = await self.high_contrast.toggle()
        
        if self.voice_feedback_enabled and self.gem.tts_module:
            await self.gem.tts_module.speak(message)
        
        return message
    
    async def enable_sticky_keys(self) -> str:
        """Enable sticky keys."""
        success, message = await self.keyboard_nav.enable_sticky_keys()
        
        if self.voice_feedback_enabled and self.gem.tts_module:
            await self.gem.tts_module.speak(message)
        
        return message
    
    async def enable_filter_keys(self) -> str:
        """Enable filter keys."""
        success, message = await self.keyboard_nav.enable_filter_keys()
        
        if self.voice_feedback_enabled and self.gem.tts_module:
            await self.gem.tts_module.speak(message)
        
        return message
    
    async def describe_interface(self) -> str:
        """Describe the current interface."""
        try:
            description = "Interface atual: "
            
            # Get basic system info
            system = platform.system()
            description += f"Sistema {system}. "
            
            # Get active window info
            window_info = await self._get_active_window_info()
            if window_info:
                description += f"Janela ativa: {window_info['title']}. "
            
            # Add accessibility status
            if self.high_contrast.is_enabled:
                description += "Alto contraste ativado. "
            
            if self.magnification.current_zoom != 1.0:
                description += f"Zoom atual: {self.magnification.current_zoom}x. "
            
            if self.voice_feedback_enabled and self.gem.tts_module:
                await self.gem.tts_module.speak(description)
            
            return description
        
        except Exception as e:
            self.logger.error(f"Interface description error: {e}")
            return "Erro ao descrever a interface"
    
    async def get_accessibility_status(self) -> Dict[str, Any]:
        """Get current accessibility settings status."""
        return {
            "screen_reader_available": self.screen_reader.is_available,
            "current_zoom": self.magnification.current_zoom,
            "high_contrast_enabled": self.high_contrast.is_enabled,
            "sticky_keys_enabled": self.keyboard_nav.sticky_keys_enabled,
            "filter_keys_enabled": self.keyboard_nav.filter_keys_enabled,
            "auto_read_enabled": self.auto_read_enabled,
            "voice_feedback_enabled": self.voice_feedback_enabled
        }
    
    def set_auto_read(self, enabled: bool):
        """Enable/disable automatic reading."""
        self.auto_read_enabled = enabled
        self.logger.info(f"Auto-read {'enabled' if enabled else 'disabled'}")
    
    def set_voice_feedback(self, enabled: bool):
        """Enable/disable voice feedback."""
        self.voice_feedback_enabled = enabled
        self.logger.info(f"Voice feedback {'enabled' if enabled else 'disabled'}")
    
    async def emergency_accessibility_mode(self) -> str:
        """Activate emergency accessibility mode with maximum assistance."""
        try:
            # Enable all accessibility features
            await self.high_contrast.enable()
            await self.magnification.zoom_in()
            await self.keyboard_nav.enable_sticky_keys()
            
            self.auto_read_enabled = True
            self.voice_feedback_enabled = True
            
            message = "Modo de emergência de acessibilidade ativado. Alto contraste, zoom e teclas aderentes habilitados."
            
            if self.gem.tts_module:
                await self.gem.tts_module.speak(message)
            
            return message
        
        except Exception as e:
            self.logger.error(f"Emergency mode error: {e}")
            return "Erro ao ativar modo de emergência"