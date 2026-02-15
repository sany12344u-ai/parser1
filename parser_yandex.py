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
import os
import tempfile
from requests.auth import HTTPProxyAuth

logging.basicConfig(level=logging.INFO)

TOKEN = '8572442312:AAHAtRuHOKs0BQwbAAPEgT3cZNt1G1AXP5M'
bot = Bot(TOKEN)
dp = Dispatcher()

# Данные прокси
PROXY_CONFIG = {
    'ip': '5.188.208.229',
    'port': '8000',
    'login': 'ycgTUQ',
    'password': 'gQhnX6'
}

def create_session():
    """Создает новую сессию с рандомным User-Agent и прокси"""
    session = requests.Session()
    
    # Рандомный User-Agent для каждого запроса
    session.headers.update({
        'User-Agent': UserAgent().random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    # Настраиваем прокси с авторизацией
    proxy_url = f"http://{PROXY_CONFIG['login']}:{PROXY_CONFIG['password']}@{PROXY_CONFIG['ip']}:{PROXY_CONFIG['port']}"
    session.proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    
    return session

@dp.message(Command('start'))
async def start(message: types.Message):
    await message.answer(
        f'<b>👋 Привет, {message.from_user.first_name}!</b>\n\n'
        '<i>🎵 Я музыкальный бот, который поможет узнать всё о любимых исполнителях!</i>\n\n'
        '🔍 Просто отправь мне ссылку на артиста с Яндекс.Музыки:\n\n'
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
        
        # Создаем новую сессию для каждого запроса
        session = create_session()
        
        # Проверяем IP (для отладки)
        try:
            ip_check = session.get('https://api.ipify.org?format=json', timeout=5)
            print(f"Текущий IP: {ip_check.json()['ip']}")
        except:
            print("Не удалось проверить IP")
        
        # Получаем страницу
        response = session.get(link, timeout=15)
        
        if response.status_code != 200:
            await message.answer(f"❌ Ошибка {response.status_code}")
            print(f"Статус код: {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Ищем блок с информацией
        block = soup.find('div', class_='By12CU9obvaH0jYtauNw')
        if not block:
            block = soup.find('div', class_='ArtistPage_root')
        if not block:
            # Сохраняем для отладки
            with open('debug_error.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            await message.answer("❌ Не удалось найти информацию об артисте")
            return

        # Получаем имя
        name_elem = block.find('div', class_='PageHeaderTitle_root')
        name = name_elem.text if name_elem else "Неизвестно"

        # Получаем слушателей
        listeners_elem = block.find('div', class_='PageHeaderArtist_label')
        month_listeners = listeners_elem.text if listeners_elem else "Нет данных"

        # Получаем изображение
        image_block = block.find('div', class_='PageHeaderCover_root')
        if image_block and image_block.find('img'):
            image_link = image_block.find('img').get('src')
            image_bytes = session.get(image_link, timeout=10).content
            photo = BufferedInputFile(image_bytes, filename='artist.jpg')
        else:
            photo = None

        # Получаем треки
        tracks = block.find_all('div', class_='Meta_text')
        
        top_tracks = []
        for track in tracks[:10]:  # Берем первые 10 треков
            span = track.find('span')
            if span:
                track_text = span.text
                top_tracks.append(track_text)
                
                safe_track = track_text.replace(' ', '_').replace('/', '_').replace('?', '')
                builder.button(text=track_text[:20] + ('...' if len(track_text) > 20 else ''),
                             callback_data=f'track_{safe_track}')
        
        builder.adjust(1)
        
        format_track = '\n'.join(top_tracks[:5])  # Показываем только 5 треков в тексте
        
        info_text = (
            '<b>🎵 ИНФОРМАЦИЯ О МУЗЫКАНТЕ</b>\n\n'
            f'<b>🤵 Имя:</b> {name}\n'
            f'<b>👥 Слушателей:</b> {month_listeners}\n\n'
            '<b>🔥 Популярные треки:</b>\n'
            f'<i>{format_track}</i>\n'
        )

        if photo:
            await message.answer_photo(
                caption=info_text, 
                photo=photo, 
                parse_mode='html', 
                reply_markup=builder.as_markup() if top_tracks else None
            )
        else:
            await message.answer(
                text=info_text, 
                parse_mode='html', 
                reply_markup=builder.as_markup() if top_tracks else None
            )
      
    except Exception as e:
        await message.answer('<b>❌ Не удалось загрузить информацию</b>\n\nПроверьте ссылку и попробуйте еще раз', parse_mode='html')    
        print(f'Ошибка: {e}')
        import traceback
        traceback.print_exc()

@dp.callback_query(F.data.startswith('track_'))
async def download_track(call: types.CallbackQuery):
    try:
        await call.answer('⏳ Ищу трек...')
        
        data = call.data.replace('track_', '')
        track_name = data.replace('_', ' ')
        
        result = EnteredTrack(track_name, 1)
        link = result.get_url_down[0]
        print(f"Ссылка на трек: {link}")
        
        # Создаем временную папку
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, f'{data}.mp3')
        
        # Скачиваем трек
        response = requests.get(link, headers={'User-Agent': UserAgent().random}, timeout=60)
        
        with open(file_path, 'wb') as file:
            file.write(response.content)
        
        print(f'Файл готов к отправке, размер: {len(response.content)} байт')
        
        audio = FSInputFile(file_path)
        await call.message.answer_audio(audio=audio)
        print('Файл отправлен')
        
        # Удаляем временный файл
        os.remove(file_path)
        os.rmdir(temp_dir)
    
    except Exception as e:
        await call.message.answer("❌ Не удалось найти этот трек")  
        print(f'Ошибка скачивания трека: {e}')

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

