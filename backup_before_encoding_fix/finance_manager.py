#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💎 GEM OS - Finance Manager (core/finance_manager.py)
Manages personal finance, including tracking expenses, managing budgets, and providing financial insights.

Responsibilities
----------------
- Add, list, and categorize expenses.
- Define and track spending against budgets.
- Provide financial summaries.
- Persist financial data using the Storage module.
- Expose finance capabilities as tools for the LLM.
- Publish financial-related events.
- Integrate with NotificationManager for alerts.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Awaitable
from collections import defaultdict

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

# --- Dataclass para Transação Financeira (Despesa) ---
@dataclass
class FinancialTransaction:
    id: str
    amount: float
    category: str
    description: Optional[str] = None
    date: datetime = field(default_factory=datetime.now)
    type: str = "expense" # "expense" ou "income" (futuro)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "amount": self.amount,
            "category": self.category,
            "description": self.description,
            "date": self.date.isoformat(),
            "type": self.type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FinancialTransaction:
        return cls(
            id=data["id"],
            amount=data["amount"],
            category=data["category"],
            description=data.get("description"),
            date=datetime.fromisoformat(data["date"]) if data.get("date") else datetime.now(),
            type=data.get("type", "expense"),
        )

# --- Dataclass para Orçamento (Budget) ---
@dataclass
class Budget:
    id: str
    category: str
    amount: float
    start_date: datetime
    end_date: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "amount": self.amount,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Budget:
        return cls(
            id=data["id"],
            category=data["category"],
            amount=data["amount"],
            start_date=datetime.fromisoformat(data["start_date"]),
            end_date=datetime.fromisoformat(data["end_date"]),
        )


# --- Finance Manager como um Plugin ---
class FinanceManager(BasePlugin):
    """
    Manages personal finance data for GEM OS, acting as a plugin.
    """
    STORAGE_KEY_TRANSACTIONS = "user_financial_transactions"
    STORAGE_KEY_BUDGETS = "user_financial_budgets"

    def __init__(self, gem_instance: GEMVoiceAssistant, logger: Optional[logging.Logger] = None):
        super().__init__(gem_instance, logger)
        self.logger.info("FinanceManager plugin inicializado.")
        
        self.event_manager: EventManager = gem_instance.event_manager
        self.notification_manager: NotificationManager = gem_instance.notification_manager
        self.storage: Storage = gem_instance.storage
        self.tts_module: TTSModule = gem_instance.tts_module

        self._transactions: Dict[str, FinancialTransaction] = {} # {id: transaction_obj}
        self._budgets: Dict[str, Budget] = {} # {id: budget_obj}
        self._data_loaded = asyncio.Event()

    async def initialize(self) -> None:
        """Loads financial data (transactions and budgets) from storage."""
        await self._load_data_from_storage()
        self.event_manager.subscribe("GEM_SHUTDOWN", self._on_gem_shutdown)
        self.logger.info("FinanceManager inicializado.")

    async def _on_gem_shutdown(self, event_data: Dict[str, Any]) -> None:
        """Handler for GEM_SHUTDOWN event."""
        self.logger.info("Recebido GEM_SHUTDOWN. FinanceManager a ser desligado.")
        self.shutdown()

    async def _load_data_from_storage(self) -> None:
        """Loads transactions and budgets from persistent storage."""
        try:
            transactions_data = await self.storage.get_setting(self.STORAGE_KEY_TRANSACTIONS, [])
            for tx_dict in transactions_data:
                try:
                    tx = FinancialTransaction.from_dict(tx_dict)
                    self._transactions[tx.id] = tx
                except Exception as e:
                    self.logger.error(f"Erro ao carregar transação: {e} - Dados: {tx_dict}", exc_info=True)
            self.logger.info(f"Carregadas {len(self._transactions)} transações.")

            budgets_data = await self.storage.get_setting(self.STORAGE_KEY_BUDGETS, [])
            for budget_dict in budgets_data:
                try:
                    budget = Budget.from_dict(budget_dict)
                    self._budgets[budget.id] = budget
                except Exception as e:
                    self.logger.error(f"Erro ao carregar orçamento: {e} - Dados: {budget_dict}", exc_info=True)
            self.logger.info(f"Carregados {len(self._budgets)} orçamentos.")

        except Exception as e:
            self.logger.error(f"Falha ao carregar dados financeiros: {e}", exc_info=True)
        finally:
            self._data_loaded.set() # Sinaliza que os dados foram carregados

    async def _save_transactions_to_storage(self) -> None:
        """Saves current transactions to persistent storage."""
        try:
            transactions_data = [tx.to_dict() for tx in self._transactions.values()]
            await self.storage.set_setting(self.STORAGE_KEY_TRANSACTIONS, transactions_data)
            self.logger.debug(f"Salvas {len(self._transactions)} transações.")
        except Exception as e:
            self.logger.error(f"Falha ao salvar transações: {e}", exc_info=True)

    async def _save_budgets_to_storage(self) -> None:
        """Saves current budgets to persistent storage."""
        try:
            budgets_data = [budget.to_dict() for budget in self._budgets.values()]
            await self.storage.set_setting(self.STORAGE_KEY_BUDGETS, budgets_data)
            self.logger.debug(f"Salvos {len(self._budgets)} orçamentos.")
        except Exception as e:
            self.logger.error(f"Falha ao salvar orçamentos: {e}", exc_info=True)

    # --------------------------------------------------------------------- Commands

    async def _add_expense_command(self, amount: float, category: str,
                                   description: Optional[str] = None, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Adiciona uma nova despesa.
        `date` deve ser uma string no formato ISO 8601 (YYYY-MM-DD HH:MM).
        """
        await self._data_loaded.wait()

        parsed_date: datetime = datetime.now()
        if date:
            try:
                parsed_date = datetime.fromisoformat(date)
            except ValueError:
                await self._speak_response("Formato de data/hora inválido. Por favor, use 'AAAA-MM-DD HH:MM'.")
                return {"success": False, "output": "Formato de data/hora inválido.", "error": "Invalid date/time format"}

        if amount <= 0:
            await self._speak_response("O valor da despesa deve ser positivo.")
            return {"success": False, "output": "Valor inválido.", "error": "Amount must be positive"}

        transaction_id = str(uuid.uuid4())
        new_expense = FinancialTransaction(
            id=transaction_id,
            amount=amount,
            category=category,
            description=description,
            date=parsed_date,
            type="expense"
        )
        self._transactions[transaction_id] = new_expense
        await self._save_transactions_to_storage()
        
        message = f"Despesa de {amount:.2f} na categoria '{category}' adicionada com sucesso."
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("FINANCE_EXPENSE_ADDED", new_expense.to_dict())
        self.logger.info(message)
        
        await self._check_budget_limits(category, amount) # Verificar orçamento
        return {"success": True, "output": message, "error": None}

    async def _list_expenses_command(self, category: Optional[str] = None, period: str = "this_month", limit: int = 5) -> Dict[str, Any]:
        """
        Lista despesas com base na categoria e período.
        Períodos suportados: "today", "this_week", "this_month", "all".
        """
        await self._data_loaded.wait()

        now = datetime.now()
        filtered_expenses: List[FinancialTransaction] = []

        for tx in self._transactions.values():
            if tx.type != "expense": continue # Apenas despesas por enquanto

            matches_category = (category is None or tx.category.lower() == category.lower())
            
            matches_period = False
            if period == "all":
                matches_period = True
            elif period == "today" and tx.date.date() == now.date():
                matches_period = True
            elif period == "this_week" and now.isocalendar()[1] == tx.date.isocalendar()[1] and now.year == tx.date.year:
                matches_period = True
            elif period == "this_month" and now.month == tx.date.month and now.year == tx.date.year:
                matches_period = True
            
            if matches_category and matches_period:
                filtered_expenses.append(tx)
        
        filtered_expenses.sort(key=lambda t: t.date, reverse=True) # Mais recentes primeiro
        expenses_to_display = filtered_expenses[:limit]

        if not expenses_to_display:
            message = f"Não há despesas para {period} na categoria '{category}'." if category else f"Não há despesas para {period}."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}
        
        output_lines = [f"Despesas para {period} (Categoria: {category or 'Todas'}):"]
        for i, tx in enumerate(expenses_to_display):
            output_lines.append(f"{i+1}. {tx.description or 'Sem descrição'} - {tx.amount:.2f} - Categoria: {tx.category} (Data: {tx.date.strftime('%Y-%m-%d %H:%M')})")
            output_lines.append(f"   (ID: {tx.id[:8]}...)")
            output_lines.append("-" * 20)
        
        message = "\n".join(output_lines)
        await self._speak_response(f"Despesas listadas. Verifique o ecrã para os detalhes.")
        await self.notification_manager.add_notification(f"Lista de despesas exibida.", level=NOTIFICATION_INFO)
        return {"success": True, "output": message, "error": None}

    async def _set_budget_command(self, category: str, amount: float,
                                  start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Define ou atualiza um orçamento para uma categoria específica.
        Datas devem ser no formato ISO 8601 (YYYY-MM-DD). Se não fornecidas, será o mês atual.
        """
        await self._data_loaded.wait()

        now = datetime.now()
        parsed_start_date: datetime
        parsed_end_date: datetime

        try:
            if start_date:
                parsed_start_date = datetime.fromisoformat(start_date).replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                parsed_start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) # Início do mês atual

            if end_date:
                parsed_end_date = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
            else:
                # Fim do mês atual
                next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1) # Move to next month
                parsed_end_date = (next_month - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)

        except ValueError:
            await self._speak_response("Formato de data inválido. Por favor, use 'AAAA-MM-DD'.")
            return {"success": False, "output": "Formato de data inválido.", "error": "Invalid date format"}

        if parsed_start_date >= parsed_end_date:
            await self._speak_response("A data de início do orçamento deve ser anterior à data de término.")
            return {"success": False, "output": "Erro de data.", "error": "Start date must be before end date"}
        
        if amount <= 0:
            await self._speak_response("O valor do orçamento deve ser positivo.")
            return {"success": False, "output": "Valor inválido.", "error": "Amount must be positive"}

        # Verificar se já existe um orçamento para a categoria e período
        existing_budget: Optional[Budget] = None
        for b_id, budget in self._budgets.items():
            if budget.category.lower() == category.lower() and \
               max(parsed_start_date, budget.start_date) < min(parsed_end_date, budget.end_date): # Há sobreposição
                existing_budget = budget
                break
        
        if existing_budget:
            # Atualiza o orçamento existente
            existing_budget.amount = amount
            existing_budget.start_date = parsed_start_date
            existing_budget.end_date = parsed_end_date
            message = f"Orçamento para '{category}' atualizado para {amount:.2f} de {parsed_start_date.strftime('%Y-%m-%d')} a {parsed_end_date.strftime('%Y-%m-%d')}."
            budget_to_save = existing_budget
        else:
            # Cria um novo orçamento
            budget_id = str(uuid.uuid4())
            new_budget = Budget(
                id=budget_id,
                category=category,
                amount=amount,
                start_date=parsed_start_date,
                end_date=parsed_end_date
            )
            self._budgets[budget_id] = new_budget
            message = f"Orçamento de {amount:.2f} para '{category}' definido de {parsed_start_date.strftime('%Y-%m-%d')} a {parsed_end_date.strftime('%Y-%m-%d')}."
            budget_to_save = new_budget
        
        await self._save_budgets_to_storage()
        await self._speak_response(message)
        await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
        await self.event_manager.publish("FINANCE_BUDGET_SET", budget_to_save.to_dict())
        self.logger.info(message)
        return {"success": True, "output": message, "error": None}

    async def _get_budget_status_command(self, category: Optional[str] = None, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtém o status do orçamento para uma categoria e/ou data específica.
        Se `date` não for fornecido, usará o mês atual.
        """
        await self._data_loaded.wait()

        target_date: datetime = datetime.now()
        if date:
            try:
                target_date = datetime.fromisoformat(date)
            except ValueError:
                await self._speak_response("Formato de data inválido. Por favor, use 'AAAA-MM-DD'.")
                return {"success": False, "output": "Formato de data inválido.", "error": "Invalid date format"}

        relevant_budgets: List[Budget] = []
        if category:
            for budget in self._budgets.values():
                if budget.category.lower() == category.lower() and \
                   budget.start_date <= target_date <= budget.end_date:
                    relevant_budgets.append(budget)
        else:
            # Pegar todos os orçamentos ativos para a data
            for budget in self._budgets.values():
                if budget.start_date <= target_date <= budget.end_date:
                    relevant_budgets.append(budget)

        if not relevant_budgets:
            message = f"Nenhum orçamento ativo encontrado para a categoria '{category}' na data {target_date.strftime('%Y-%m-%d')}." if category else f"Nenhum orçamento ativo encontrado para a data {target_date.strftime('%Y-%m-%d')}."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}

        output_lines = [f"Status do Orçamento para {target_date.strftime('%Y-%m-%d')} (Categoria: {category or 'Todas'}):"]
        total_spent_global = 0.0
        total_budget_global = 0.0

        for budget in relevant_budgets:
            spent_in_category = sum(tx.amount for tx in self._transactions.values()
                                    if tx.type == "expense" and tx.category.lower() == budget.category.lower() and
                                       budget.start_date <= tx.date <= budget.end_date)
            
            remaining = budget.amount - spent_in_category
            status_emoji = "✅" if remaining >= 0 else "❌"
            status_text = "dentro do orçamento" if remaining >= 0 else f"excedido em {-remaining:.2f}"

            output_lines.append(f"{status_emoji} Orçamento '{budget.category}': {spent_in_category:.2f} / {budget.amount:.2f} (Restante: {remaining:.2f}) - {status_text}")
            total_spent_global += spent_in_category
            total_budget_global += budget.amount

            if remaining < 0:
                await self.notification_manager.add_notification(
                    f"Atenção: O orçamento para '{budget.category}' foi excedido em {-remaining:.2f}!", level=NOTIFICATION_WARNING, vocalize=True
                )
                await self.tts_module.speak(f"Atenção: O orçamento para {budget.category} foi excedido.")

        if not category and len(relevant_budgets) > 1:
            output_lines.append("-" * 20)
            output_lines.append(f"Total Gasto: {total_spent_global:.2f} / Total Orçado: {total_budget_global:.2f}")
            global_remaining = total_budget_global - total_spent_global
            global_status_emoji = "✅" if global_remaining >= 0 else "❌"
            global_status_text = "dentro do orçamento" if global_remaining >= 0 else f"excedido em {-global_remaining:.2f}"
            output_lines.append(f"{global_status_emoji} Status Geral: {global_status_text}")

        message = "\n".join(output_lines)
        await self._speak_response(f"Status do orçamento obtido. Verifique o ecrã para os detalhes.")
        return {"success": True, "output": message, "error": None}

    async def _list_budgets_command(self) -> Dict[str, Any]:
        """
        Lista todos os orçamentos definidos.
        """
        await self._data_loaded.wait()

        if not self._budgets:
            message = "Nenhum orçamento definido."
            await self._speak_response(message)
            return {"success": True, "output": message, "error": None}
        
        output_lines = ["Orçamentos Definidos:"]
        for i, budget in enumerate(self._budgets.values()):
            spent_in_category = sum(tx.amount for tx in self._transactions.values()
                                    if tx.type == "expense" and tx.category.lower() == budget.category.lower() and
                                       budget.start_date <= tx.date <= budget.end_date)
            
            output_lines.append(f"{i+1}. Categoria: {budget.category} - Orçamento: {budget.amount:.2f} (Gasto: {spent_in_category:.2f})")
            output_lines.append(f"   Período: {budget.start_date.strftime('%Y-%m-%d')} a {budget.end_date.strftime('%Y-%m-%d')} (ID: {budget.id[:8]}...)")
            output_lines.append("-" * 20)
        
        message = "\n".join(output_lines)
        await self._speak_response(f"Seus orçamentos foram listados. Verifique o ecrã para os detalhes.")
        await self.notification_manager.add_notification("Lista de orçamentos exibida.", level=NOTIFICATION_INFO)
        return {"success": True, "output": message, "error": None}

    async def _delete_budget_command(self, budget_id_prefix: str) -> Dict[str, Any]:
        """
        Remove um orçamento pela sua categoria.
        Requer um prefixo do ID do orçamento.
        """
        await self._data_loaded.wait()

        budget_to_delete: Optional[Budget] = None
        matching_budgets = [b for b in self._budgets.values() if b.id.startswith(budget_id_prefix)]

        if len(matching_budgets) == 1:
            budget_to_delete = matching_budgets[0]
        elif len(matching_budgets) > 1:
            message = f"Múltiplos orçamentos correspondem ao ID '{budget_id_prefix}'. Por favor, seja mais específico."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Multiple matches"}
        else:
            message = f"Nenhum orçamento encontrado com o ID '{budget_id_prefix}' para remoção."
            await self._speak_response(message)
            return {"success": False, "output": message, "error": "Budget not found"}

        if budget_to_delete:
            del self._budgets[budget_to_delete.id]
            await self._save_budgets_to_storage()
            message = f"Orçamento para '{budget_to_delete.category}' (ID: {budget_to_delete.id[:8]}...) removido."
            await self._speak_response(message)
            await self.notification_manager.add_notification(message, level=NOTIFICATION_SUCCESS)
            await self.event_manager.publish("FINANCE_BUDGET_DELETED", {"budget_id": budget_to_delete.id})
            self.logger.info(message)
            return {"success": True, "output": message, "error": None}
        
        return {"success": False, "output": "Erro desconhecido ao remover orçamento.", "error": "Unknown error"}

    async def _get_financial_summary_command(self, period: str = "this_month") -> Dict[str, Any]:
        """
        Fornece um resumo financeiro para um período (ex: "this_month").
        Períodos suportados: "this_month", "last_month", "this_year", "all".
        """
        await self._data_loaded.wait()

        now = datetime.now()
        start_period: datetime
        end_period: datetime

        if period == "this_month":
            start_period = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
            end_period = (next_month - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == "last_month":
            first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_period = first_day_this_month - timedelta(microseconds=1)
            start_period = end_period.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "this_year":
            start_period = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_period = now.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
        elif period == "all":
            start_period = datetime.min
            end_period = datetime.max
        else:
            await self._speak_response("Período inválido para resumo financeiro. Use 'this_month', 'last_month', 'this_year' ou 'all'.")
            return {"success": False, "output": "Período inválido.", "error": "Invalid period"}

        total_expenses = 0.0
        expenses_by_category = defaultdict(float)

        for tx in self._transactions.values():
            if tx.type == "expense" and start_period <= tx.date <= end_period:
                total_expenses += tx.amount
                expenses_by_category[tx.category] += tx.amount
        
        output_lines = [f"Resumo Financeiro para {period.replace('_', ' ').capitalize()}:"]
        output_lines.append(f"Total de Despesas: {total_expenses:.2f}")
        
        if expenses_by_category:
            output_lines.append("\nDespesas por Categoria:")
            for category, amount in sorted(expenses_by_category.items(), key=lambda item: item[1], reverse=True):
                output_lines.append(f"- {category}: {amount:.2f}")

        # Incluir status dos orçamentos para o período relevante
        active_budgets_for_period: List[Budget] = []
        for budget in self._budgets.values():
            if max(start_period, budget.start_date) < min(end_period, budget.end_date):
                active_budgets_for_period.append(budget)
        
        if active_budgets_for_period:
            output_lines.append("\nStatus dos Orçamentos no Período:")
            for budget in active_budgets_for_period:
                spent_in_category = expenses_by_category[budget.category] # Já calculado acima
                remaining = budget.amount - spent_in_category
                status_emoji = "✅" if remaining >= 0 else "❌"
                status_text = "dentro do orçamento" if remaining >= 0 else f"excedido em {-remaining:.2f}"
                output_lines.append(f"{status_emoji} Orçamento '{budget.category}': {spent_in_category:.2f} / {budget.amount:.2f} (Restante: {remaining:.2f}) - {status_text}")


        message = "\n".join(output_lines)
        await self._speak_response(f"Resumo financeiro para {period} obtido. Verifique o ecrã para os detalhes.")
        await self.notification_manager.add_notification(f"Resumo financeiro para {period} exibido.", level=NOTIFICATION_INFO)
        await self.event_manager.publish("FINANCE_SUMMARY_GENERATED", {"period": period, "total_expenses": total_expenses})
        return {"success": True, "output": message, "error": None}

    async def _check_budget_limits(self, category: str, amount_spent: float) -> None:
        """Internal helper to check if adding an expense exceeds any relevant budget."""
        now = datetime.now()
        for budget in self._budgets.values():
            if budget.category.lower() == category.lower() and \
               budget.start_date <= now <= budget.end_date: # Orçamento ativo para a categoria
                
                spent_so_far = sum(tx.amount for tx in self._transactions.values()
                                   if tx.type == "expense" and tx.category.lower() == category.lower() and
                                      budget.start_date <= tx.date <= budget.end_date)
                
                new_total_spent = spent_so_far + amount_spent

                if new_total_spent > budget.amount:
                    message = f"Atenção! Gasto de {amount_spent:.2f} na categoria '{category}' excede o seu orçamento de {budget.amount:.2f} em {new_total_spent - budget.amount:.2f}."
                    await self.notification_manager.add_notification(message, level=NOTIFICATION_WARNING, vocalize=True)
                    await self.tts_module.speak(message)
                    self.logger.warning(f"Orçamento excedido para '{category}': {message}")
                elif new_total_spent > budget.amount * 0.9: # 90% do orçamento
                    message = f"Alerta: Você atingiu 90% do seu orçamento para '{category}'. Gastou {new_total_spent:.2f} de {budget.amount:.2f}."
                    await self.notification_manager.add_notification(message, level=NOTIFICATION_INFO, vocalize=True)
                    await self.tts_module.speak(message)
                    self.logger.info(f"Orçamento perto do limite para '{category}': {message}")

    # --------------------------------------------------------------------- Plugin Interface

    def register_commands(self, executor: CommandExecutor) -> None:
        """Registers finance management commands with the CommandExecutor."""
        self.logger.info("A registar comandos do plugin FinanceManager...")
        executor.register_command("add_expense", self._add_expense_command)
        executor.register_command("list_expenses", self._list_expenses_command)
        executor.register_command("set_budget", self._set_budget_command)
        executor.register_command("get_budget_status", self._get_budget_status_command)
        executor.register_command("list_budgets", self._list_budgets_command)
        executor.register_command("delete_budget", self._delete_budget_command)
        executor.register_command("get_financial_summary", self._get_financial_summary_command)
        self.logger.info("Comandos FinanceManager registados.")

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool definitions (schemas) for finance features.
        These schemas are exposed to the LLM for function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "add_expense",
                    "description": "Adiciona uma nova despesa ao seu registo financeiro. Requer o valor da despesa e a categoria. Opcionalmente, pode incluir uma descrição e a data.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "amount": {
                                "type": "number",
                                "format": "float",
                                "description": "O valor da despesa.",
                            },
                            "category": {
                                "type": "string",
                                "description": "A categoria da despesa (ex: 'Alimentação', 'Transporte', 'Lazer').",
                            },
                            "description": {
                                "type": "string",
                                "description": "Uma breve descrição da despesa (ex: 'Jantar com amigos'). Opcional.",
                            },
                            "date": {
                                "type": "string",
                                "description": "A data e hora da despesa no formato ISO 8601 (YYYY-MM-DD HH:MM). Padrão para a hora atual se não fornecida. Opcional.",
                            }
                        },
                        "required": ["amount", "category"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_expenses",
                    "description": "Lista as despesas registadas. Pode filtrar por categoria, período ('today', 'this_week', 'this_month', 'all') e limitar o número de resultados.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "A categoria das despesas a listar (ex: 'Transporte'). Opcional.",
                            },
                            "period": {
                                "type": "string",
                                "description": "O período das despesas a listar: 'today' (hoje), 'this_week' (esta semana), 'this_month' (este mês), 'all' (todas). Padrão para 'this_month'.",
                                "enum": ["today", "this_week", "this_month", "all"],
                                "default": "this_month"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "O número máximo de despesas a retornar. Padrão para 5.",
                                "default": 5,
                                "minimum": 1
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "set_budget",
                    "description": "Define ou atualiza um orçamento para uma categoria específica. Requer a categoria e o valor do orçamento. Opcionalmente, pode definir um período (data de início e fim). Se as datas não forem fornecidas, o orçamento será para o mês atual.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "A categoria para a qual definir o orçamento (ex: 'Lazer', 'Utilidades').",
                            },
                            "amount": {
                                "type": "number",
                                "format": "float",
                                "description": "O valor total orçado para a categoria no período.",
                            },
                            "start_date": {
                                "type": "string",
                                "description": "A data de início do período do orçamento no formato ISO 8601 (YYYY-MM-DD). Opcional.",
                            },
                            "end_date": {
                                "type": "string",
                                "description": "A data de término do período do orçamento no formato ISO 8601 (YYYY-MM-DD). Opcional.",
                            }
                        },
                        "required": ["category", "amount"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_budget_status",
                    "description": "Obtém o status do orçamento para uma categoria específica e/ou data. Se a data não for fornecida, considerará o mês atual. Se a categoria não for fornecida, mostrará o status de todos os orçamentos ativos para o período.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "A categoria do orçamento a verificar. Opcional.",
                            },
                            "date": {
                                "type": "string",
                                "description": "A data para verificar o orçamento no formato ISO 8601 (YYYY-MM-DD). Padrão para a data atual. Opcional.",
                            }
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_budgets",
                    "description": "Lista todos os orçamentos que foram definidos, mostrando a categoria, o valor orçado e o período de validade.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_budget",
                    "description": "Remove um orçamento existente. Requer o ID completo ou um prefixo único do orçamento.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "budget_id_prefix": {
                                "type": "string",
                                "description": "O ID completo ou um prefixo único do orçamento a ser removido.",
                            },
                        },
                        "required": ["budget_id_prefix"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_financial_summary",
                    "description": "Fornece um resumo financeiro para um período específico, incluindo o total de despesas e despesas por categoria. Períodos suportados: 'this_month', 'last_month', 'this_year', 'all'.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "period": {
                                "type": "string",
                                "description": "O período para o resumo financeiro. Padrão para 'this_month'.",
                                "enum": ["this_month", "last_month", "this_year", "all"],
                                "default": "this_month"
                            }
                        },
                        "required": [],
                    },
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
        """Performs any necessary cleanup."""
        self.logger.info("FinanceManager a ser desligado.")
        self.event_manager.unsubscribe("GEM_SHUTDOWN", self._on_gem_shutdown)


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    # Configure logging for standalone test
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("TestFinanceManager")

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

    async def run_finance_manager_tests():
        print("\n--- Iniciando Testes do FinanceManager ---")

        dummy_gem = DummyGEM(logger)
        finance_manager = FinanceManager(dummy_gem, logger)
        
        finance_manager.register_commands(dummy_gem.command_executor)

        await finance_manager.initialize()

        now = datetime.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month_start = (now.replace(day=28) + timedelta(days=4)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month_end = (next_month_start - timedelta(microseconds=1))

        # --- Teste 1: Adicionar Despesas ---
        print("\n--- Teste 1: Adicionar Despesas ---")
        result_add_expense1 = await dummy_gem.command_executor.execute(
            "add_expense", amount=50.00, category="Alimentação", description="Almoço no restaurante"
        )
        print(result_add_expense1["output"])
        assert result_add_expense1["success"] is True
        assert "Despesa de 50.00 na categoria 'Alimentação' adicionada com sucesso." in result_add_expense1["output"]

        result_add_expense2 = await dummy_gem.command_executor.execute(
            "add_expense", amount=30.00, category="Transporte", description="Gasolina"
        )
        print(result_add_expense2["output"])
        assert result_add_expense2["success"] is True

        result_add_expense3 = await dummy_gem.command_executor.execute(
            "add_expense", amount=20.00, category="Alimentação", description="Café da manhã",
            date=(now - timedelta(days=2)).isoformat() # Despesa de dias atrás
        )
        print(result_add_expense3["output"])
        assert result_add_expense3["success"] is True

        # --- Teste 2: Listar Despesas ---
        print("\n--- Teste 2: Listar Despesas (Este Mês) ---")
        result_list_expenses = await dummy_gem.command_executor.execute("list_expenses", category="Alimentação", period="this_month")
        print(result_list_expenses["output"])
        assert result_list_expenses["success"] is True
        assert "Almoço no restaurante" in result_list_expenses["output"]
        assert "Café da manhã" in result_list_expenses["output"]
        assert "Despesas para this_month (Categoria: Alimentação):" in result_list_expenses["output"]

        print("\n--- Teste 3: Definir Orçamento ---")
        result_set_budget = await dummy_gem.command_executor.execute(
            "set_budget", category="Alimentação", amount=100.00,
            start_date=this_month_start.strftime("%Y-%m-%d"),
            end_date=this_month_end.strftime("%Y-%m-%d")
        )
        print(result_set_budget["output"])
        assert result_set_budget["success"] is True
        assert "Orçamento de 100.00 para 'Alimentação' definido" in result_set_budget["output"]

        result_set_budget_transport = await dummy_gem.command_executor.execute(
            "set_budget", category="Transporte", amount=50.00,
            start_date=this_month_start.strftime("%Y-%m-%d"),
            end_date=this_month_end.strftime("%Y-%m-%d")
        )
        print(result_set_budget_transport["output"])
        assert result_set_budget_transport["success"] is True

        # --- Teste 4: Adicionar Despesa que Excede Orçamento ---
        print("\n--- Teste 4: Adicionar Despesa que Excede Orçamento ---")
        result_add_expense_exceed = await dummy_gem.command_executor.execute(
            "add_expense", amount=40.00, category="Alimentação", description="Jantar de última hora"
        )
        print(result_add_expense_exceed["output"])
        assert result_add_expense_exceed["success"] is True # Despesa é adicionada
        # Verificar notificação de orçamento excedido
        assert any("Orçamento para 'Alimentação' foi excedido" in n["message"] for n in dummy_gem.notification_manager.get_notification_history(limit=5))

        # --- Teste 5: Obter Status do Orçamento ---
        print("\n--- Teste 5: Obter Status do Orçamento (Alimentação) ---")
        result_budget_status_food = await dummy_gem.command_executor.execute("get_budget_status", category="Alimentação")
        print(result_budget_status_food["output"])
        assert result_budget_status_food["success"] is True
        assert "Orçamento 'Alimentação': 110.00 / 100.00" in result_budget_status_food["output"]
        assert "excedido em 10.00" in result_budget_status_food["output"]

        print("\n--- Teste 6: Obter Status do Orçamento (Geral) ---")
        result_budget_status_general = await dummy_gem.command_executor.execute("get_budget_status")
        print(result_budget_status_general["output"])
        assert result_budget_status_general["success"] is True
        assert "Total Gasto: 140.00 / Total Orçado: 150.00" in result_budget_status_general["output"] # 110 (alimentacao) + 30 (transporte)
        assert "Status Geral: dentro do orçamento" in result_budget_status_general["output"]

        # --- Teste 7: Listar Orçamentos ---
        print("\n--- Teste 7: Listar Orçamentos ---")
        result_list_budgets = await dummy_gem.command_executor.execute("list_budgets")
        print(result_list_budgets["output"])
        assert result_list_budgets["success"] is True
        assert "Orçamento: 100.00 (Gasto: 110.00)" in result_list_budgets["output"]
        assert "Orçamento: 50.00 (Gasto: 30.00)" in result_list_budgets["output"]
        
        # --- Teste 8: Obter Resumo Financeiro ---
        print("\n--- Teste 8: Obter Resumo Financeiro (Este Mês) ---")
        result_summary = await dummy_gem.command_executor.execute("get_financial_summary", period="this_month")
        print(result_summary["output"])
        assert result_summary["success"] is True
        assert "Total de Despesas: 140.00" in result_summary["output"]
        assert "Despesas por Categoria:" in result_summary["output"]
        assert "- Alimentação: 110.00" in result_summary["output"]
        assert "- Transporte: 30.00" in result_summary["output"]
        assert "Orçamento 'Alimentação': 110.00 / 100.00 (Restante: -10.00) - excedido em 10.00" in result_summary["output"]

        # --- Teste 9: Deletar Orçamento ---
        print("\n--- Teste 9: Deletar Orçamento ---")
        budget_id_to_delete = next(b.id for b in finance_manager._budgets.values() if b.category == "Transporte")
        result_delete_budget = await dummy_gem.command_executor.execute("delete_budget", budget_id_prefix=budget_id_to_delete[:8])
        print(result_delete_budget["output"])
        assert result_delete_budget["success"] is True
        assert "Orçamento para 'Transporte' (ID:" in result_delete_budget["output"] and "removido." in result_delete_budget["output"]

        # Verify deletion
        assert budget_id_to_delete not in finance_manager._budgets

        print("\n--- Testes do FinanceManager concluídos com sucesso. ---")
        finance_manager.shutdown()
        
    asyncio.run(run_finance_manager_tests())

