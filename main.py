import asyncio
import os  
from dotenv import load_dotenv 

load_dotenv()  
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None: 
    await message.answer(f'Привет! Давай помогу тебе с бытом.')

async def main() -> None:
    bot = Bot(token=os.getenv("TOKEN"))  
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())