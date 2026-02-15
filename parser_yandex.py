import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import BufferedInputFile, FSInputFile
from parse_hitmos.entered_tracks import EnteredTrack
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

TOKEN = '8572442312:AAHAtRuHOKs0BQwbAAPEgT3cZNt1G1AXP5M'
bot = Bot(TOKEN)
dp = Dispatcher()

session = requests.Session()

fake_user = UserAgent().random
header = {'User-Agent': fake_user,
          'Accept': '*/*',
          'accept-language': 'ru,en-US;q=0.9,en;q=0.8,fr;q=0.7,zh-CN;q=0.6,zh;q=0.5,it;q=0.4'}

proxies = {
    'http': f'http://5.188.208.229:8000',
    'https': f'https://5.188.208.229:8000'
}

@dp.message(Command('start'))
async def start(message: types.Message):
    await message.answer(
        f'<b>👋 Привет, {message.from_user.first_name}!</b>\n\n'
        '<i>🎵 Я музыкальный бот, который поможет узнать всё о любимых исполнителях!</i>\n\n'
        '🔍 Просто отправь мне имя артиста или группы, и я покажу:\n\n'
        '• 🧑‍🎤 Информацию о музыканте\n'
        '• 👥 Количество слушателей\n'
        '• 🔥 Топ популярных треков\n\n'
        '<b>🎧 Попробуй прямо сейчас! 👇</b>', parse_mode='html'
    )

@dp.message(F.text)
async def text(message: types.Message):
    try:
        builder = InlineKeyboardBuilder()
        
        link = message.text
        responce = session.get(link, headers=header, proxies=proxies).text
        soup = BeautifulSoup(responce, 'lxml')
        block = soup.find('div', class_ = 'By12CU9obvaH0jYtauNw pnFSEGiRmI9JuhUxbfVe ArtistPage_root__QPg3p')

        name = block.find('div', class_='PageHeaderTitle_root__ESu2q').text

        month_listeners = block.find('div', class_='PageHeaderArtist_label__rXyrB').text

        image_link = block.find('div', class_ = 'qaIScXjx1qyXuaIHXQIo QIWoHHDozGGG5w2JYImt ZcpulvHgF_wsgzB8Hye9 PageHeaderCover_root_hoverable__WF_BH').find('img').get('src')
        image_bytes = session.get(image_link, headers=header).content

        photo = BufferedInputFile(image_bytes, filename='pinterest_photo')
        tracks = block.find_all('div', class_='_MWOVuZRvUQdXKTMcOPx LezmJlldtbHWqU7l1950 oyQL2RSmoNbNQf3Vc6YI Z_WIr2W8JU4MPQek3hgR _3_Mxw7Si7j2g4kWjlpR Meta_text__Y5uYH')
        
        top_tracks = []

        for track in tracks:
            top_tracks_text = track.find('span').text
            top_tracks.append(top_tracks_text)
            
            safe_track = top_tracks_text.replace(' ', '_')
            
            builder.button(text=top_tracks_text,
                           callback_data=f'track_{safe_track}')
            
        builder.adjust(1)
        
        format_track = '\n'.join(top_tracks)   
        
            

        info_text = (
            '<b>🎵 ИНФОРМАЦИЯ О МУЗЫКАНТЕ</b>\n\n'
            f'<b>🤵 Имя:</b> {name}\n'
            f'<b>👥 Слушателей:</b> {month_listeners}\n\n'
            '<b>🔥 Топ треков:</b>\n'
            f'<i>{format_track}</i>\n')


        
        await message.answer_photo(caption=info_text, photo=photo, parse_mode='html', reply_markup=builder.as_markup())
      
    except Exception as e:
        await message.answer('<b>⛔Неправильная ссылка</b>\n\nПопробуйте еще раз', parse_mode='html')    
        print(f'Ошибка: {e}')


@dp.callback_query(F.data.startswith('track_'))
async def dowload_track(call: types.CallbackQuery):
    try:
        await call.answer('⏳ Ищу трек...')
        
        data = call.data.replace('track_', '')
        
        track_name = data.replace('_', ' ')
        
        result = EnteredTrack(track_name, 1)
        link = result.get_url_down[0]
        print(link)
        responce = requests.get(link, headers=header, timeout=60).content
        
        with open(f'audio/{data}.mp3', 'wb') as file:
            file.write(responce)
        
        audio = FSInputFile(f'audio/{data}.mp3')
        print('Файл готов к отправке')
        
        await call.message.answer_audio(audio=audio)
        print('Файл отправлен')
        
    
    except Exception as e:
        await call.message.answer("К сожалению нам не удалось найти этот трек(")  
        print(f'Ошибка: {e}')  

async def main():
   await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())   
