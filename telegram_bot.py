"""
telegram_bot.py — Interface Telegram da Iara
Toda a lógica de interação com o usuário via Telegram fica aqui.
"""

import asyncio
import logging
import re

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode

import config

logger = logging.getLogger("telegram")

bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Callback que será configurado pelo brain.py
_message_handler = None


def set_message_handler(handler):
    """Define a função que processa mensagens (configurada pelo brain.py)."""
    global _message_handler
    _message_handler = handler


def sanitize_markdown(text: str) -> str:
    """
    Sanitiza Markdown para Telegram.
    Telegram usa um subset limitado e crasha com marcadores desbalanceados.
    """
    # Bold **: deve ter pares
    count_bold = text.count("**")
    if count_bold % 2 != 0:
        text = text + "**"

    # Code blocks ```: devem ter pares
    count_code_block = text.count("```")
    if count_code_block % 2 != 0:
        text = text + "\n```"

    # Inline code `: deve ter pares (excluindo ```)
    temp = text.replace("```", "XXX")
    count_inline = temp.count("`")
    if count_inline % 2 != 0:
        text = text + "`"

    return text


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Resposta ao /start."""
    if message.from_user.id != config.USER_ID_ALLOWED:
        await message.answer("🚫 Acesso não autorizado.")
        return

    await message.answer(
        "🌊 Oi Criador! Iara online e pronta.\n"
        "Manda qualquer mensagem que eu respondo!",
        parse_mode=ParseMode.MARKDOWN,
    )


@dp.message()
async def handle_message(message: types.Message):
    """Captura todas as mensagens e roteia para o brain."""
    if message.from_user.id != config.USER_ID_ALLOWED:
        return

    if not _message_handler:
        await message.answer("⚠️ Meu cérebro ainda não carregou. Tenta de novo em 5s.")
        return

    text = message.text or message.caption or ""

    # Detectar documento anexado
    file_path = None
    if message.document:
        try:
            import os
            file_info = await bot.get_file(message.document.file_id)
            file_name = message.document.file_name or "arquivo"
            file_path = f"/tmp/{file_name}"
            await bot.download_file(file_info.file_path, file_path)
            logger.info(f"📄 Arquivo baixado: {file_name}")
            text = f"📄FILE:{file_path}|{text}" if text else f"📄FILE:{file_path}|analisa este documento"
        except Exception as e:
            logger.error(f"Erro baixando arquivo: {e}")
            await message.answer(f"❌ Não consegui baixar o arquivo: {str(e)[:200]}")
            return

    if not text.strip():
        return

    await bot.send_chat_action(message.chat.id, "typing")

    try:
        await _message_handler(text, message)
    except Exception as e:
        logger.error(f"❌ Erro processando mensagem: {e}", exc_info=True)
        await message.answer(
            f"😿 Algo deu errado. Erro: {str(e)[:200]}\n"
            "Tenta de novo em alguns segundos.",
        )


async def send_streaming_response(chat_id: int, stream_generator, reply_to: int = None):
    """Envia resposta com streaming progressivo."""
    full_text = ""
    sent_message = None
    last_edit_length = 0
    edit_interval = config.STREAMING_EDIT_INTERVAL

    try:
        async for chunk in stream_generator:
            full_text += chunk

            if len(full_text) - last_edit_length < 40:
                continue

            display_text = full_text + " ▌"

            if sent_message is None:
                sent_message = await bot.send_message(
                    chat_id,
                    display_text,
                    reply_to_message_id=reply_to,
                )
            else:
                try:
                    await bot.edit_message_text(
                        display_text,
                        chat_id=chat_id,
                        message_id=sent_message.message_id,
                    )
                except Exception:
                    pass

            last_edit_length = len(full_text)
            await asyncio.sleep(edit_interval)

        # Mensagem final — sanitiza Markdown antes de enviar
        if sent_message and full_text:
            clean_text = sanitize_markdown(full_text)
            try:
                await bot.edit_message_text(
                    clean_text,
                    chat_id=chat_id,
                    message_id=sent_message.message_id,
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                # Markdown falhou mesmo sanitizado → texto puro
                try:
                    await bot.edit_message_text(
                        full_text,
                        chat_id=chat_id,
                        message_id=sent_message.message_id,
                    )
                except Exception:
                    pass
        elif full_text and not sent_message:
            clean_text = sanitize_markdown(full_text)
            try:
                await bot.send_message(
                    chat_id, clean_text,
                    reply_to_message_id=reply_to,
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                await bot.send_message(
                    chat_id, full_text,
                    reply_to_message_id=reply_to,
                )

    except Exception as e:
        error_msg = f"😿 Erro no streaming: {str(e)[:200]}"
        if sent_message:
            try:
                await bot.edit_message_text(
                    error_msg,
                    chat_id=chat_id,
                    message_id=sent_message.message_id,
                )
            except Exception:
                pass
        else:
            await bot.send_message(chat_id, error_msg)

    return full_text


async def send_simple_message(chat_id: int, text: str, reply_to: int = None):
    """Envia uma mensagem simples. Se muito longa, envia como arquivo .md."""
    # Telegram limit: 4096 chars
    if len(text) > 3900:
        # Enviar como arquivo markdown
        await send_as_document(chat_id, text, reply_to=reply_to)
        return

    clean_text = sanitize_markdown(text)
    try:
        await bot.send_message(
            chat_id, clean_text,
            reply_to_message_id=reply_to,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        await bot.send_message(
            chat_id, text,
            reply_to_message_id=reply_to,
        )


async def send_channel_message(chat_id: int, text: str, channel: str = "final", reply_to: int = None):
    """
    Envia uma mensagem respeitando o canal de visibilidade:
    - analysis: Raciocínio interno e leitura bruta (visível apenas nos logs).
    - commentary: Atualização de status visual via Telegram.
    - final: Output formal final ou pedindo decisões do usuário.
    """
    if channel == "analysis":
        logger.info(f"[🧠 ANALYSIS]: {text[:500]}...")
        return # Não atinge o usuário
        
    if channel == "commentary":
        text = f"⚙️ _{text}_"
        
    await send_simple_message(chat_id, text, reply_to=reply_to)


async def send_as_document(chat_id: int, text: str, filename: str = None, reply_to: int = None):
    """Envia texto como arquivo .md no Telegram."""
    import tempfile
    import os
    from datetime import datetime
    from aiogram.types import FSInputFile

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pesquisa_{timestamp}.md"

    # Criar arquivo temporário
    tmp_path = os.path.join(tempfile.gettempdir(), filename)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(text)

    try:
        doc = FSInputFile(tmp_path, filename=filename)
        # Enviar preview curto + arquivo
        preview = text[:300].split("\n")[0] + "..."
        await bot.send_document(
            chat_id,
            doc,
            caption=f"📄 {preview}",
            reply_to_message_id=reply_to,
        )
    except Exception as e:
        logger.error(f"Erro enviando documento: {e}")
        # Fallback: enviar em chunks
        for i in range(0, len(text), 3900):
            chunk = text[i:i+3900]
            try:
                await bot.send_message(chat_id, chunk)
            except Exception:
                pass
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


async def start_bot():
    """Inicia o bot Telegram (polling)."""
    logger.info("🌊 Telegram bot iniciando...")
    await dp.start_polling(bot)
