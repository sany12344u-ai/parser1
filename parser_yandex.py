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

fake_user = UserAgent().random
header = {'User-Agent': fake_user,
          'Accept': '*/*',
          'accept-language': 'ru,en-US;q=0.9,en;q=0.8,fr;q=0.7,zh-CN;q=0.6,zh;q=0.5,it;q=0.4'}

proxies = {
    'http': f'http://ycgTUQ:gQhnX6@5.188.208.229:8000',
    'https': f'http://ycgTUQ:gQhnX6@5.188.208.229:8000'      
}

session = requests.Session()
session.proxies.update(proxies)

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

        with open('audio.html', 'w') as file:
          file.write(responce)
        document = FSInputFile('audio.html')
        await message.answer_document(document)      
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
        
        # 1. Ищем трек через поиск на hitmotop
        search_url = f"https://rus.hitmotop.com/search?q={track_name.replace(' ', '+')}"
        print(f"Поиск: {search_url}")
        
        search_response = session.get(search_url, headers=header, timeout=60)
        search_soup = BeautifulSoup(search_response.text, 'lxml')
        
        # Сохраняем для отладки
        with open(f'search_{data}.html', 'w', encoding='utf-8') as f:
            f.write(search_response.text)
        
        # 2. Пробуем разные селекторы для поиска трека
        # Вариант 1: ищем по классу track-item
        track_item = search_soup.find('div', class_='track-item')
        if not track_item:
            # Вариант 2: ищем по классу track
            track_item = search_soup.find('div', class_='track')
        if not track_item:
            # Вариант 3: ищем первую ссылку с классом track__title
            track_item = search_soup.find('a', class_='track__title')
        
        if not track_item:
            print("Трек не найден в результатах поиска")
            raise Exception("Трек не найден")
        
        # Получаем ссылку на трек
        if track_item.name == 'a':
            track_link = track_item.get('href')
        else:
            track_link = track_item.find('a')['href']
        
        if not track_link.startswith('http'):
            full_track_url = f"https://rus.hitmotop.com{track_link}"
        else:
            full_track_url = track_link
            
        print(f"Ссылка на трек: {full_track_url}")
        
        # 3. Получаем страницу трека
        track_page = session.get(full_track_url, headers=header, timeout=60)
        track_soup = BeautifulSoup(track_page.text, 'lxml')
        
        # Сохраняем для отладки
        with open(f'track_{data}.html', 'w', encoding='utf-8') as f:
            f.write(track_page.text)
        
        # 4. Ищем ссылку на скачивание
        download_link = None
        
        # Вариант 1: ищем кнопку download
        download_btn = track_soup.find('a', class_='download')
        if download_btn:
            download_link = download_btn.get('href')
        
        # Вариант 2: ищем аудио плеер
        if not download_link:
            audio_tag = track_soup.find('audio')
            if audio_tag and audio_tag.get('src'):
                download_link = audio_tag['src']
        
        # Вариант 3: ищем ссылку в data-url
        if not download_link:
            player_data = track_soup.find('div', {'data-url': True})
            if player_data:
                download_link = player_data['data-url']
        
        if not download_link:
            print("Ссылка на скачивание не найдена")
            raise Exception("Ссылка на скачивание не найдена")
        
        print(f"Ссылка на скачивание: {download_link}")
        
        # 5. Скачиваем
        mp3_response = session.get(download_link, headers=header, timeout=60).content
        
        # 6. Сохраняем
        os.makedirs('audio', exist_ok=True)
        with open(f'audio/{data}.mp3', 'wb') as file:
            file.write(mp3_response)
        
        audio = FSInputFile(f'audio/{data}.mp3')
        await call.message.answer_audio(audio=audio)
        print('Файл отправлен')
        
    except Exception as e:
        await call.message.answer("К сожалению нам не удалось найти этот трек(")  
        print(f'Ошибка: {e}')
        # Выводим дополнительную информацию для отладки
        import traceback
        traceback.print_exc()

async def main():
   await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())   







