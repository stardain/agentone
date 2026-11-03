import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from dotenv import load_dotenv
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_gigachat.chat_models import GigaChat
# model.stream(), model.batch() (max_concurrency через config), model.batch_as_completed(), 

load_dotenv()

llm = GigaChat(
    verify_ssl_certs=False,
    scope="GIGACHAT_API_PERS",
    model="GigaChat-2-Pro"
)

def call_llm(state: MessagesState):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

graph = StateGraph(MessagesState)
graph.add_node(call_llm)
graph.add_edge(START, "call_llm")
graph.add_edge("call_llm", END)
graph = graph.compile()

def run_agent(user_query: str) -> str:
    """Принимает вопрос, возвращает ответ агента."""
    res = graph.invoke({"messages": [{"role": "user", "content": user_query}]})
    return res["messages"][-1].content

#
#
#

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
dp = Dispatcher()

# --- 2. Состояния (FSM) для будущей логики с оператором ---
class Dialog(StatesGroup):
    user_waiting = State()  # Пользователь ждёт ответа оператора

# --- 4. Обработчик /start ---
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Привет! Напиши вопрос.")
# --- 5. Обработчик текста (твой агент) ---
@dp.message(F.text)
async def handle(message: Message):
    # message.text — это вопрос пользователя из Telegram
    user_query = message.text
    # Вызываем твоего агента (он синхронный, поэтому через to_thread)
    response = await asyncio.to_thread(run_agent, user_query)
    # Отправляем ответ обратно в Telegram
    await message.answer(response)
# --- 6. Запуск ---
async def main():
    bot = Bot(TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())