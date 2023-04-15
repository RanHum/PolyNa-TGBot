import json

import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode, BotCommand, BotCommandScopeDefault
from aiogram.utils import executor


settings = json.load(open('settings.json', encoding='utf-8'))
bot = Bot(settings['token'])


storage = MemoryStorage()  # todo redis storage for persistent sessions
dp = Dispatcher(bot, storage=storage)

campuses = json.load(open('campuses.json', encoding='utf-8'))

# Defining available states
class Form(StatesGroup):
	campus = State()
	destination = State()


@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
	"""
	Conversation's entry point
	"""
	commands = [
		BotCommand('start', 'Begin dialog'),
		BotCommand('navigate', 'Begin navigation'),
		BotCommand('cancel', 'Cancel navigation at any point')
	]
	await dp.bot.set_my_commands(commands, BotCommandScopeDefault()) # todo ensure every user getting actual commands
	await message.answer("Hello, I'm PolyNa, Polytech University Navagaion Bot!")


@dp.message_handler(commands='navigate')
async def cmd_navigate(message: types.Message):
	"""
	Navigation entry point
	"""
	# Configure ReplyKeyboardMarkup for campuses
	markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
	for campus in campuses:
		markup.add(campus)

	await Form.campus.set()
	await message.answer("Please choose your campus for destination", reply_markup=markup)


# You can use state '*' if you need to handle all states
@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
	"""
	Allow user to cancel any state
	"""
	current_state = await state.get_state()
	if current_state is None:
		return

	await state.finish()
	await message.answer('Dialog reset!', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(state=Form.campus)
async def process_campus(message: types.Message, state: FSMContext):
	"""
	Process campus
	"""
	async with state.proxy() as data:
		data['campus'] = message.text

	await Form.destination.set()
	# Remove keyboard
	markup = types.ReplyKeyboardRemove()
	await message.answer('Enter destination room', reply_markup=markup)


@dp.message_handler(lambda message: message.text not in campuses, state=Form.campus)
async def process_campus_invalid(message: types.Message):
	"""
	Campus has to be one of predefined
	"""
	return await message.answer('Bad campus. Choose your campus from the keyboard!')


@dp.message_handler(state=Form.destination)
async def process_destination(message: types.Message, state: FSMContext):
	"""
	Process destination room or point
	"""
	async with state.proxy() as data:
		data['destination'] = message.text

		# Remove keyboard
		markup = types.ReplyKeyboardRemove()

		# And send message
		await bot.send_message(
			message.chat.id,
			md.text(
				md.text('Hi! Nice to navigate you to'),
				md.text('Campus: ', md.bold(data['campus'])),
				md.text('Room: ', md.bold(data['destination'])),
				sep='\n',
			),
			reply_markup=markup,
			parse_mode=ParseMode.MARKDOWN,
		)

	# Finish nav session
	await state.finish()


if __name__ == '__main__':
	executor.start_polling(dp, skip_updates=True)