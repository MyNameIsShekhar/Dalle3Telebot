import logging
import asyncio
from telebot.async_telebot import AsyncTeleBot
import telebot
import yaml
from provider.bing import ImageGenAsync
from telebot.types import InputMediaPhoto
from keepalive import keep_alive
with open("config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)

TOKEN = config["BotConfig"]["TOKEN"]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=config["Logging"]["level"],
)
logger = logging.getLogger(__name__)

bot = AsyncTeleBot(TOKEN)


@bot.message_handler(commands=["help", "start"])
async def send_welcome(message):
    logger.info(f"Received /help or /start command from user {message.from_user.id}")
    await bot.reply_to(
        message,
        """Give me your prompt I will turn it to Image for you !""",
    )


import logging

@bot.message_handler(commands=["imagine"])
async def generate_image(message):
    chat_id = message.chat.id
    await bot.send_chat_action(chat_id, action="upload_photo")
    args = message.text.split()[1:]
    prompt = " ".join(args)
    auth_cookie = config["Cookies"]["value"]
    quiet = False
    image_generator = ImageGenAsync(
        auth_cookie,
        quiet,
    )
    
    try:
        if prompt:
            logMs = await bot.send_message(chat_id,"Sending request to bing generator please wait...")
            print('sending request to bing image creator please wait ...')
            image_links = await image_generator.get_images(prompt)
            filtered_links = [link for link in image_links if ".svg" not in link]
            media = []
            for index, image_url in enumerate(filtered_links):
                caption = f"```prompt {prompt}```" if index == 0 else None
                media.append(
                    InputMediaPhoto(media=image_url, caption=caption, parse_mode="MARKDOWN")
                )
            await bot.delete_message(chat_id,logMs.message_id)
            await bot.send_media_group(chat_id=chat_id, media=media,reply_to_message_id=message.id)
        else:
            await bot.send_message(
                chat_id, "Please provide prompt ex: /imagine spiderman wearing skirt."
            )
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        await bot.delete_message(chat_id,logMs.message_id)
        await bot.send_message(chat_id, "An unexpected error occurred. Please try again later.")

@bot.message_handler(func=lambda message: True)
async def on_message_handler(message):
    chat_id = message.chat.id
    await bot.send_chat_action(chat_id,"typing")
    await bot.send_message(chat_id,"Please using /imagine {your prompt here} to generate image.!\nEX:\n```prompt /imagine spiderman wearing space suit.```",parse_mode="MARKDOWN")

async def main():
    logger.info("Bot started polling.")
    # Set up bot command description
    await bot.set_my_commands(
        [
            telebot.types.BotCommand("/start", "Start The Bot"),
            telebot.types.BotCommand(
                "/imagine", "Using DALLE3 by /imagine {your prompt}}"
            ),
        ]
    )
    me = await bot.get_me()
    print(f"Bot connected: {me.username}")
    await bot.infinity_polling()


if __name__ == "__main__":
    try:
        keep_alive()
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt)")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
