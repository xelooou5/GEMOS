import asyncio
import logging
import inspect
import re
import subprocess
import time
// Hidden
Lines


class CommandPattern:
    """Represents a command pattern with its handler."""

    def __init__(self, name: str, patterns: List[str], handler: Callable, description: str, category: str = "general",
                 requires_confirmation: bool = False, schema: Optional[Dict[str, Any]] = None):
        self.name = name
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        self.handler = handler
        self.description = description
        self.category = category
        self.requires_confirmation = requires_confirmation
        self.schema = schema or self._generate_schema_from_handler()

    def _generate_schema_from_handler(self) -> Dict[str, Any]:
        """Generates a tool schema by inspecting the handler's signature."""
        sig = inspect.signature(self.handler)
        properties = {}
        required = []

        for name, param in sig.parameters.items():
            if name in ('self', 'match', 'kwargs'):
                continue

            # A very basic type mapping. This can be expanded.
            param_type = "string"
            if param.annotation == int:
                param_type = "integer"
            elif param.annotation == bool:
                param_type = "boolean"

            properties[name] = {"type": param_type, "description": f"Parameter: {name}"}
            if param.default is inspect.Parameter.empty:
                required.append(name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                },
            },
        }

    def matches(self, text: str) -> Optional[re.Match]:
        """Check if text matches any pattern."""
        for pattern in self.patterns:

// Hidden
Lines
self.register_command(
    name="set_system_volume",
    patterns=[r"volume (\d+)", r"ajustar volume para (\d+)", r"set volume to (\d+)"],
    handler=self._handle_set_volume,
    description="Ajusta o volume do sistema",
    category="system",
    schema={
           // Hidden
Lines
"""
command = CommandPattern(name, patterns, handler, description, category, requires_confirmation, schema)
self.commands.append(command)
self.logger.debug(f"Registered command '{name}' with schema: {command.schema}")

def get_tool_schemas(self) -> List[Dict[str, Any]]:
"""
Get
tool
schemas
for all registered commands that have one."""
// Hidden Lines

                 self.logger.info(f"LLM requested to call tool '{tool_name}' with args: {tool_args}")
                 self._record_command(f"{tool_name}({tool_args})", "llm_tool")

                 # Ensure tool_args is a dict before passing
                 if not isinstance(tool_args, dict):
                     self.logger.error(f"LLM provided non-dict arguments for {tool_name}: {tool_args}")
                     return f"Desculpe, os argumentos para a ferramenta {tool_name} estão mal formatados."
                 return await self.execute_tool(tool_name, **tool_args)
             else:
                 return llm_response.get("content", "Não tenho uma resposta para isso no momento.")
         else:
// Hidden Lines
         for command in self.commands:
             if command.name == tool_name:
                 try:
                     # The handler can accept kwargs from the LLM.
                     result = await command.handler(match=None, **kwargs)
                     return result or "Comando executado."
                 except Exception as e:
                     self.logger.error(f"Error executing tool '{tool_name}' with args {kwargs}: {e}", exc_info=self.gem.debug)
                     return f"Ocorreu um erro ao usar a ferramenta {tool_name}."

         self.logger.error(f"LLM requested unknown tool: '{tool_name}'")
// Hidden Lines
         await asyncio.sleep(1)
         await self.gem.shutdown()

     async def _handle_restart(self, match: Optional[re.Match], **kwargs) -> str:
         """Handle restart request.Can be called by regex or tool call."""
         self.logger.info("Restart requested")
         return "Função de reinicialização não implementada ainda."

     async def _handle_set_volume(self, match: Optional[re.Match], volume: Optional[int] = None, **kwargs) -> str:
         """Handle volume adjustment."""
         # Prioritize explicit argument from LLM, then fall back to regex match.
         if volume is None and match:
             try:
                 volume = int(match.group(1))
             except (ValueError, IndexError):
                 return "Não consegui extrair o nível de volume do seu comando."

         if volume is None:
             return "Por favor, especifique um nível de volume entre 0 e 100."

         try:
             volume = int(max(0, min(100, volume)))  # Clamp between 0-100

             # Try to set system volume (Linux)
             try:
// Hidden Lines
     async def _handle_help(self, match: Optional[re.Match], **kwargs) -> str:
         """Handle help request.Can be called by regex or tool call."""
         categories = {}
         for command in self.commands:
             if command.category not in categories:
                 categories[command.category] = []
             # Use the command name for clarity, as descriptions can be long
             categories[command.category].append(command.name)

         response_lines = ["Comandos disponíveis, agrupados por categoria:"]
         for category, commands in categories.items():
             response_lines.append(f"\n{category.capitalize()}:")
             for name in sorted(commands):
                 # Find the command again to get its description
                 cmd_obj = next((c for c in self.commands if c.name == name), None)
                 if cmd_obj:
                     response_lines.append(f"  - {name}: {cmd_obj.description}")

         response = "\n".join(response_lines)
         self.logger.info(f"Generated help response:\n{response}")
         return response