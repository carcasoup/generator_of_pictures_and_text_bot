import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, BufferedInputFile
from datetime import datetime
from base64 import b64decode
import time
import requests
from keys import *

class YandexGPT:
    def getAnswer(user_prompt):
        system_prompt = 'Ты ассистент писателя. Напиши короткий рассказ. В ответе пришли только рассказ.'
        gpt_model = 'yandexgpt-lite'
        body = {
            'modelUri': f'gpt://{folder_id}/{gpt_model}',
            'completionOptions': {'stream': False, 'temperature': 0.3, 'maxTokens': 2000},
            'messages': [
                {'role': 'system', 'text': system_prompt},
                {'role': 'user', 'text': user_prompt},
            ]
        }
        url = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completionAsync'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Api-Key {api_key}'
        }
        response = requests.post(url, headers=headers, json=body)
        operation_id = response.json().get('id')
        url = f"https://llm.api.cloud.yandex.net:443/operations/{operation_id}"
        headers = {"Authorization": f"Api-Key {api_key}"}

        while True:
            response = requests.get(url, headers=headers)
            done = response.json()["done"]
            if done:
                break
            else:
                time.sleep(1)

        data = response.json()
        answer = data['response']['alternatives'][0]['message']['text']
        return answer


class YandexArt:

    def getImage(prompt, style):
        match style:
            case 'Живопись':
                system_prompt = 'стиль: живопись'
            case 'Аниме':
                system_prompt = 'Стиль Studio Ghibli, Динамичный Shonen'

        seed = int(round(datetime.now().timestamp()))
        folder_id = "b1gug7c74crq38i2spt2"
        api_key = "AQVN07CqobFnf6YA4f-LYwKCKqhJ_slTIzOgEWGf"

        body = {
            "modelUri": f"art://{folder_id}/yandex-art/latest",
            "generationOptions": {"seed": seed, "temperature": 0.6},
            "messages": [
                {"weight": 1, "text": prompt},
                {"weight": 1, "text": system_prompt}
            ],
        }

        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/imageGenerationAsync"
        headers = {"Authorization": f"Api-Key {api_key}"}

        response = requests.post(url, headers=headers, json=body)
        operation_id = response.json()["id"]

        url = f"https://llm.api.cloud.yandex.net:443/operations/{operation_id}"
        headers = {"Authorization": f"Api-Key {api_key}"}

        while True:
            response = requests.get(url, headers=headers)
            done = response.json()["done"]
            if done:
                break
            else:
                time.sleep(2)

        image_data = response.json()["response"]["image"]
        image = b64decode(image_data)
        return image


class UserInfo(StatesGroup):
    mode = State()
    style = State()
    prompt = State()


async def command_start(message: Message, state: FSMContext) -> None:
    await state.set_state(UserInfo.mode)
    kb_list = [
        [KeyboardButton(text="Придумать рассказ"), KeyboardButton(text="Придумать картинку")],
    ]
    await message.answer("Привет, давай придумаем!", reply_markup=ReplyKeyboardMarkup(keyboard=kb_list,
                                                                                      resize_keyboard=True,
                                                                                        one_time_keyboard=True))
async def process_mode(message: Message, state: FSMContext) -> None:
    if message.text == "Придумать рассказ":
        data = await state.update_data(mode=1, style="")
        await state.set_state(UserInfo.prompt)
        await message.answer("Хорошо, какая тема будет?")
    elif message.text == "Придумать картинку":
        data = await state.update_data(mode=2)
        await state.set_state(UserInfo.style)
        kb_list = [
            [KeyboardButton(text="Живопись"), KeyboardButton(text="Аниме")],
        ]
        await message.answer("Хорошо, какой стиль будет?", reply_markup=ReplyKeyboardMarkup(keyboard=kb_list,
                                                                                            resize_keyboard=True,
                                                                                            one_time_keyboard=True))


async def process_style(message: Message, state: FSMContext) -> None:
    data = await state.update_data(style=message.text)
    await state.set_state(UserInfo.prompt)
    await message.answer("Хорошо, какая тема будет?")


async def process_prompt(message: Message, state: FSMContext) -> None:
    data = await state.update_data(prompt=message.text)
    kb_list = [[KeyboardButton(text="/start")]]
    match data["mode"]:
        case 1:
            answer = YandexGPT.getAnswer(data["prompt"])
            await message.answer(answer, reply_markup=ReplyKeyboardMarkup(
                keyboard=kb_list,
                resize_keyboard=True,
                one_time_keyboard=True)
                                 )
        case 2:
            img = YandexArt.getImage(data["prompt"], data["style"])
            image_file = BufferedInputFile(
                file=img,
                filename="generated_image.png"
            )
            await message.answer_photo(
                photo=image_file,
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=kb_list,
                    resize_keyboard=True,
                    one_time_keyboard=True)
            )

    await state.clear()


async def main() -> None:

    dp = Dispatcher()
    dp.message.register(command_start, Command("start"))
    dp.message.register(process_mode, UserInfo.mode)
    dp.message.register(process_style, UserInfo.style)
    dp.message.register(process_prompt, UserInfo.prompt)

    bot = Bot(token=bot_token)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
