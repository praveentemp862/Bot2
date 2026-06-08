import asyncio
import logging
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
import re
import os
import sys

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# CONFIGURATION - Put your details here
BOT_TOKEN = "8747413527:AAFruBP5jonjdis1pjJObMAmcJix84l060M"
ADMIN_ID = 5709610723  # Your numeric user ID
UPI_ID = "chaitram11@fam"  # Your UPI ID for payments
TOS_CHANNEL = "t.me/TermsOfsen"  # Your TOS channel
QR_CHANNEL = "t.me/sensmmqr/15"  # Your QR channel
VOUCH_LINK = "https://t.me/OfficialSensMM?comment=5"  # Your vouch link
VOUCH_USERNAME = "@seunko"  # Your username for vouch format
YOUR_CHANNEL = "@OfficialSensMM"  # Your channel username
VOUCH_CHANNEL = "t.me/vouchyf"  # Channel where vouches will be forwarded

# Default group name format
DEFAULT_GROUP_NAME = f"Sen's MM | {YOUR_CHANNEL}"

# Path to group picture
GROUP_PICTURE_PATH = "mm.jpg"

# Store pending vouches
pending_vouches = {}

# Cryptocurrency addresses
CRYPTO_ADDRESSES = {
    "ETH": {
        "name": "Ethereum (ETH)",
        "address": "0xf6AD4FDC6d118FdE032C08A5D3022da218089159"
    },
    "BTC": {
        "name": "Bitcoin (BTC)",
        "address": "bc1q5hpr2dcjanulkdeuyu24rr7zkxaxjmap507y7a"
    },
    "BNB": {
        "name": "BNB / USDT BEP20",
        "address": "0xf6AD4FDC6d118FdE032C08A5D3022da218089159"
    },
    "SOL": {
        "name": "Solana (SOL)",
        "address": "EqkzU1GnQJ4sNSuchbiPnBSpX6eFNH3WEGZGn98xRr6s"
    },
    "TON": {
        "name": "Toncoin (TON)",
        "address": "UQBPL_mstF2e57dxeXLla6XsfvrUAX_s-v3tOZrQaTXcQ2eK"
    },
    "USDT": {
        "name": "Tether (USDT ERC20)",
        "address": "0xf6AD4FDC6d118FdE032C08A5D3022da218089159"
    },
    "LTC": {
        "name": "Litecoin (LTC)",
        "address": "LefPeWVNvs374ChEUM34fbQS4BfgdcLvG2"
    }
}

# Per-chat state storage
chat_states = {}

def get_chat_state(chat_id):
    """Get or create state for a specific chat"""
    if chat_id not in chat_states:
        chat_states[chat_id] = {
            'current_deal_amount': None,
            'deal_active': False,
            'group_locked': False,
            'invite_link_used': False,
            'terms_sent': False,
            'deal_type': 'fiat',  # 'fiat' or 'crypto'
            'group_picture_set': False  # Track if picture has been set
        }
    return chat_states[chat_id]

def calculate_crypto_fee(amount):
    """Calculate fee for crypto deals"""
    if amount < 10:
        return 1  # Fixed $1 fee
    else:
        return amount * 0.002  # 0.2% fee

def calculate_inr_fee(amount):
    """Calculate fee for INR deals"""
    if amount < 100:
        return 10  # Fixed ₹10 fee for amounts below 100
    else:
        return amount * 0.05  # 5% fee

async def set_group_picture(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Set group picture from mm.jpg file"""
    try:
        # Check if mm.jpg exists
        if os.path.exists(GROUP_PICTURE_PATH):
            with open(GROUP_PICTURE_PATH, 'rb') as photo:
                await context.bot.set_chat_photo(
                    chat_id=chat_id,
                    photo=photo
                )
            logger.info(f"Group picture set for chat {chat_id}")
            return True
        else:
            logger.warning(f"Group picture file {GROUP_PICTURE_PATH} not found")
            return False
    except Exception as e:
        logger.error(f"Failed to set group picture: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send invite link message with 2-person limit and set group picture"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    
    # Check if user is admin
    if not await is_admin(update, context):
        await update.message.delete()
        return
    
    try:
        # Create invite link with member limit of 2 (only 2 people can join)
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=chat_id,
            member_limit=2,
            creates_join_request=False
        )
        
        # Set group picture from mm.jpg (always try to set it)
        picture_set = await set_group_picture(chat_id, context)
        if picture_set:
            chat_state['group_picture_set'] = True
            logger.info(f"Group picture set successfully for chat {chat_id}")
        else:
            logger.warning(f"Could not set group picture for chat {chat_id}")
        
        # Send the share link message
        message1 = f"<b>Share the link below with anyone involved in this deal</b>\n\n{invite_link.invite_link}\n\n<i>⚠️ Only 2 people can join using this link</i>"
        await context.bot.send_message(
            chat_id=chat_id,
            text=message1,
            parse_mode=ParseMode.HTML
        )
        
        chat_state['invite_link_used'] = True
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        error_msg = "Failed to create invite link. Make sure bot has proper permissions."
        await context.bot.send_message(chat_id=chat_id, text=error_msg)
    
    # Delete the command
    await update.message.delete()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command - Show all available commands for MM"""
    chat_id = update.effective_chat.id
    
    # Check if user is admin
    if not await is_admin(update, context):
        await update.message.delete()
        return
    
    help_text = """
🤖 <b>Middleman Bot Commands</b> 🤖

<b>📌 Setup Commands:</b>
• <code>/start</code> - Create invite link (2 person limit) & set group pic
• <code>/stat</code> - Send terms of deal message
• <code>/qr</code> - Forward QR code to group

<b>💰 Deal Commands:</b>
• <code>.pay &lt;amount&gt;</code> - Create INR payment request
• <code>.crypto &lt;amount&gt;</code> - Show crypto options
• <code>.eth &lt;amount&gt;</code> - Direct ETH payment
• <code>.btc &lt;amount&gt;</code> - Direct BTC payment
• <code>.bnb &lt;amount&gt;</code> - Direct BNB payment
• <code>.sol &lt;amount&gt;</code> - Direct SOL payment
• <code>.ton &lt;amount&gt;</code> - Direct TON payment
• <code>.usdt &lt;amount&gt;</code> - Direct USDT payment
• <code>.ltc &lt;amount&gt;</code> - Direct LTC payment

<b>✅ Deal Management:</b>
• <code>.rcvd [amount]</code> - Confirm payment received
• <code>.com</code> - Mark deal as completed
• <code>.cancel</code> - Cancel deal
• <code>.vouch</code> - Send vouch request

<b>🔒 Group Control:</b>
• <code>.lock</code> - Lock group (auto-delete messages)
• <code>.unlock</code> - Unlock group
• <code>/name [custom]</code> - Reset group name to default or set custom
• <code>/setname &lt;name&gt;</code> - Set custom group name

<b>⚙️ Owner Only:</b>
• <code>/chnge &lt;qr_link&gt; &lt;upi_id&gt;</code> - Change QR & UPI settings

<b>📝 Vouch System:</b>
• Send vouch format: <code>Vouch @seunko for MM'd</code>
• Bot will auto-detect and show approve/cancel buttons
• Admin reply with <code>/s</code> to forward vouch

<b>ℹ️ This Command:</b>
• <code>/help</code> - Show this help message

━━━━━━━━━━━━━━━━
<b>Need support?</b> @Reviveal
"""
    
    await update.message.reply_text(
        text=help_text,
        parse_mode=ParseMode.HTML
    )
    
    # Delete the command
    await update.message.delete()

async def name_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /name command - Change group name to default format"""
    chat_id = update.effective_chat.id
    
    # Check if user is admin
    if not await is_admin(update, context):
        await update.message.delete()
        return
    
    message_text = update.message.text.strip()
    
    # Default name format
    default_name = f"Sen's MM | {YOUR_CHANNEL}"
    
    # Check if custom name is provided
    # Format: /name Custom Group Name
    custom_name = None
    if len(message_text) > 6:  # More than just "/name "
        custom_name = message_text[6:].strip()
    
    try:
        if custom_name:
            # Use custom name
            new_name = custom_name
            await context.bot.set_chat_title(
                chat_id=chat_id,
                title=new_name
            )
            await update.message.reply_text(
                f"✅ Group name changed to:\n<code>{new_name}</code>",
                parse_mode=ParseMode.HTML
            )
        else:
            # Use default name
            await context.bot.set_chat_title(
                chat_id=chat_id,
                title=default_name
            )
            await update.message.reply_text(
                f"✅ Group name reset to default:\n<code>{default_name}</code>",
                parse_mode=ParseMode.HTML
            )
        
        logger.info(f"Group name changed for chat {chat_id} to: {new_name if custom_name else default_name}")
        
    except Exception as e:
        logger.error(f"Failed to change group name: {e}")
        await update.message.reply_text("❌ Failed to change group name. Make sure bot has admin permissions.")
    
    # Delete the command
    await update.message.delete()

async def setname_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setname command - Set custom group name"""
    chat_id = update.effective_chat.id
    
    # Check if user is admin
    if not await is_admin(update, context):
        await update.message.delete()
        return
    
    message_text = update.message.text.strip()
    
    # Extract custom name (remove /setname command)
    # Format: /setname Custom Group Name Here
    if len(message_text) <= 9:  # Just "/setname " or less
        await update.message.reply_text(
            "❌ <b>Please provide a group name!</b>\n\n"
            "Usage: <code>/setname Your Group Name Here</code>\n\n"
            f"Example: <code>/setname Sen's MM | {YOUR_CHANNEL}</code>",
            parse_mode=ParseMode.HTML
        )
        await update.message.delete()
        return
    
    custom_name = message_text[9:].strip()
    
    try:
        await context.bot.set_chat_title(
            chat_id=chat_id,
            title=custom_name
        )
        await update.message.reply_text(
            f"✅ Group name changed to:\n<code>{custom_name}</code>",
            parse_mode=ParseMode.HTML
        )
        logger.info(f"Group name changed for chat {chat_id} to: {custom_name}")
        
    except Exception as e:
        logger.error(f"Failed to change group name: {e}")
        await update.message.reply_text("❌ Failed to change group name. Make sure bot has admin permissions.")
    
    # Delete the command
    await update.message.delete()

async def stat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send terms of deal message and pin it"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    
    # Check if user is admin
    if not await is_admin(update, context):
        await update.message.delete()
        return
    
    # Terms of deal message
    message2 = """Hey. Please state the terms of the deal.

- What is the deal?
- Who is the buyer/seller?
- What is the agreed price and which crypto?
- Include any other relevant information.

• i am not dealing below 50rs ~ @seunko """
    
    sent_message = await context.bot.send_message(
        chat_id=chat_id,
        text=message2
    )
    
    # Pin the terms message
    await context.bot.pin_chat_message(
        chat_id=chat_id,
        message_id=sent_message.message_id,
        disable_notification=True
    )
    
    chat_state['terms_sent'] = True
    
    # Delete the command
    await update.message.delete()

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if the user is an admin"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Check if user is the bot owner
    if user_id == ADMIN_ID:
        return True
    
    # Check if user is chat admin
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ['creator', 'administrator']
    except:
        return False

async def chnge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /chnge command - Change QR link and UPI ID (Owner only)"""
    global QR_CHANNEL, UPI_ID
    
    # Check if user is the owner
    if update.effective_user.id != ADMIN_ID:
        await update.message.delete()
        return
    
    message_text = update.message.text
    
    # Parse command: /chnge <qr_link> <upi_id>
    # Example: /chnge https://t.me/sensmmqr/15 chaitram11@fam
    # Or: /chnge t.me/sensmmqr/15 chaitram11@fam
    
    pattern = r'^[/.]chnge\s+(?:https?://)?(t\.me/[^\s]+)\s+([^\s]+)'
    match = re.search(pattern, message_text, re.IGNORECASE)
    
    if not match:
        await update.message.reply_text(
            "❌ <b>Invalid format!</b>\n\n"
            "Use:\n"
            "<code>/chnge t.me/your_channel/message_id your_upi_id</code>\n\n"
            "<b>Examples:</b>\n"
            "<code>/chnge t.me/sensmmqr/15 chaitram11@fam</code>\n"
            "<code>/chnge https://t.me/sensmmqr/15 chaitram11@fam</code>",
            parse_mode=ParseMode.HTML
        )
        await update.message.delete()
        return
    
    qr_path = match.group(1)
    new_upi = match.group(2)
    
    # Store old values for confirmation
    old_qr = QR_CHANNEL
    old_upi = UPI_ID
    
    # Update global variables
    QR_CHANNEL = qr_path
    UPI_ID = new_upi
    
    # Send confirmation message
    confirmation_text = (
        "✅ <b>Settings Updated Successfully!</b>\n\n"
        f"<b>QR Channel/Link:</b>\n"
        f"Old: <code>{old_qr}</code>\n"
        f"New: <code>{QR_CHANNEL}</code>\n\n"
        f"<b>UPI ID:</b>\n"
        f"Old: <code>{old_upi}</code>\n"
        f"New: <code>{UPI_ID}</code>\n\n"
        "⚠️ All new deals will use the updated settings."
    )
    
    await update.message.reply_text(
        confirmation_text,
        parse_mode=ParseMode.HTML
    )
    
    # Also log to console
    logger.info(f"QR Channel changed from {old_qr} to {QR_CHANNEL}")
    logger.info(f"UPI ID changed from {old_upi} to {UPI_ID}")
    
    # Delete the command
    await update.message.delete()

async def pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .pay command - Admin only"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    
    if not await is_admin(update, context):
        await update.message.delete()
        return
    
    message_text = update.message.text
    
    try:
        # Extract amount from command
        amount_match = re.search(r'[/.]pay\s+(\d+)', message_text, re.IGNORECASE)
        
        if not amount_match:
            await update.message.reply_text("Please specify amount: .pay 150")
            await update.message.delete()
            return
        
        base_amount = float(amount_match.group(1))
        fee = calculate_inr_fee(base_amount)
        
        # Format fee display
        if base_amount < 100:
            fee_display = f"₹{fee:.0f} "
        else:
            fee_display = f"₹{fee:.0f} "
        
        total_amount = base_amount + fee
        
        chat_state['current_deal_amount'] = base_amount
        chat_state['deal_active'] = True
        chat_state['deal_type'] = 'fiat'
        
        # Payment message with Markdown links
        payment_text = (
            f"Pay ₹{base_amount:,.0f} +  {fee_display} = ₹{total_amount:,.0f} INR\n\n"
            f"To UPI: `{UPI_ID}`\n\n"
            f"[TOS](https://{TOS_CHANNEL}) | [QR](https://{QR_CHANNEL})"
        )
        
        sent_msg = await update.message.reply_text(
            text=payment_text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        
        # Change group name with channel
        new_group_name = f"₹{base_amount:,.0f} INR MM'D | {YOUR_CHANNEL}"
        try:
            await context.bot.set_chat_title(
                chat_id=chat_id,
                title=new_group_name
            )
        except Exception as e:
            logger.error(f"Failed to change group name: {e}")
        
    except Exception as e:
        logger.error(f"Error in pay command: {e}")
        await update.message.reply_text("Error processing payment command")
    
    # Delete the command message
    await update.message.delete()

async def crypto_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .crypto command - Shows crypto selection buttons"""
    chat_id = update.effective_chat.id
    
    if not await is_admin(update, context):
        await update.message.delete()
        return
    
    message_text = update.message.text
    
    # Extract amount from command
    amount_match = re.search(r'[/.]crypto\s+(\d+)', message_text, re.IGNORECASE)
    
    if not amount_match:
        await update.message.reply_text("Please specify amount: .crypto 150")
        await update.message.delete()
        return
    
    amount = float(amount_match.group(1))
    
    # Store amount temporarily for callback
    context.user_data['crypto_amount'] = amount
    
    # Create inline keyboard with crypto options
    keyboard = []
    row = []
    for i, (symbol, data) in enumerate(CRYPTO_ADDRESSES.items()):
        row.append(InlineKeyboardButton(data['name'], callback_data=f"crypto_{symbol}_{amount}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"<b>Select cryptocurrency for ${amount:,.0f} USD deal:</b>",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    
    await update.message.delete()

async def crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle crypto selection callback"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    
    # Parse callback data
    data_parts = query.data.split('_')
    if len(data_parts) >= 3 and data_parts[0] == 'crypto':
        symbol = data_parts[1]
        amount = float(data_parts[2])
        
        if symbol in CRYPTO_ADDRESSES:
            crypto_data = CRYPTO_ADDRESSES[symbol]
            fee = calculate_crypto_fee(amount)
            total_amount = amount + fee
            
            # Format fee display
            if amount < 10:
                fee_text = "Fixed $1.00"
            else:
                fee_text = f"0.2% (${fee:.2f})"
            
            chat_state['current_deal_amount'] = amount
            chat_state['deal_active'] = True
            chat_state['deal_type'] = 'crypto'
            
            # Create payment message
            payment_text = (
                f"<b>{crypto_data['name']} Payment</b>\n\n"
                f"Amount: ${amount:,.0f} + {fee_text} = ${total_amount:.2f} USD\n\n"
                f"<b>Send to this address:</b>\n"
                f"<code>{crypto_data['address']}</code>\n\n"
                f"<i>(Tap to copy address above)</i>\n\n"
                f"<a href='https://{TOS_CHANNEL}'>Terms of Service</a>"
            )
            
            await query.message.edit_text(
                text=payment_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            
            # Change group name
            new_group_name = f"${amount:,.0f} {symbol} MM'D | {YOUR_CHANNEL}"
            try:
                await context.bot.set_chat_title(
                    chat_id=chat_id,
                    title=new_group_name
                )
            except Exception as e:
                logger.error(f"Failed to change group name: {e}")

async def direct_crypto_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle direct crypto commands like .eth 150"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    
    if not await is_admin(update, context):
        await update.message.delete()
        return
    
    message_text = update.message.text
    
    # Extract crypto symbol and amount
    match = re.search(r'[/.](\w+)\s+(\d+)', message_text, re.IGNORECASE)
    
    if not match:
        await update.message.delete()
        return
    
    symbol = match.group(1).upper()
    amount = float(match.group(2))
    
    if symbol not in CRYPTO_ADDRESSES:
        await update.message.delete()
        return
    
    crypto_data = CRYPTO_ADDRESSES[symbol]
    fee = calculate_crypto_fee(amount)
    total_amount = amount + fee
    
    # Format fee display
    if amount < 10:
        fee_text = "Fixed $1.00"
    else:
        fee_text = f"0.2% (${fee:.2f})"
    
    chat_state['current_deal_amount'] = amount
    chat_state['deal_active'] = True
    chat_state['deal_type'] = 'crypto'
    
    # Create payment message
    payment_text = (
        f"<b>{crypto_data['name']} Payment</b>\n\n"
        f"Amount: ${amount:,.0f} + {fee_text} = ${total_amount:.2f} USD\n\n"
        f"<b>Send to this address:</b>\n"
        f"<code>{crypto_data['address']}</code>\n\n"
        f"<i>(Tap to copy address above)</i>\n\n"
        f"<a href='https://{TOS_CHANNEL}'>Terms of Service</a>"
    )
    
    await update.message.reply_text(
        text=payment_text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )
    
    # Change group name
    new_group_name = f"${amount:,.0f} {symbol} MM'D | {YOUR_CHANNEL}"
    try:
        await context.bot.set_chat_title(
            chat_id=chat_id,
            title=new_group_name
        )
    except Exception as e:
        logger.error(f"Failed to change group name: {e}")
    
    await update.message.delete()

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /qr command - Forward QR from QR channel"""
    if not await is_admin(update, context):
        await update.message.delete()
        return
    
    chat_id = update.effective_chat.id
    
    try:
        # Parse QR channel to get chat_id and message_id
        qr_parts = QR_CHANNEL.replace("t.me/", "").split("/")
        channel_username = f"@{qr_parts[0]}"
        message_id = int(qr_parts[1])
        
        # Forward message from QR channel to current group
        await context.bot.forward_message(
            chat_id=chat_id,
            from_chat_id=channel_username,
            message_id=message_id
        )
        
        logger.info(f"QR forwarded successfully to group {chat_id}")
        
    except Exception as e:
        logger.error(f"Failed to forward QR: {e}")
        await update.message.reply_text("Failed to forward QR. Make sure bot is admin in QR channel.")
    
    # Delete the command
    await update.message.delete()

async def rcvd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .rcvd command - Admin only with amount"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    
    if not await is_admin(update, context):
        await update.message.delete()
        return
    
    message_text = update.message.text
    
    # Check if amount is provided with .rcvd command
    amount_match = re.search(r'[/.]rcvd\s+(\d+)', message_text, re.IGNORECASE)
    
    if amount_match:
        # Update amount if provided
        chat_state['current_deal_amount'] = float(amount_match.group(1))
        chat_state['deal_active'] = True
        
        # Update group name with new amount
        if chat_state['deal_type'] == 'crypto':
            new_group_name = f"${chat_state['current_deal_amount']:,.0f} CRYPTO MM'D | {YOUR_CHANNEL}"
        else:
            new_group_name = f"₹{chat_state['current_deal_amount']:,.0f} INR MM'D | {YOUR_CHANNEL}"
        
        try:
            await context.bot.set_chat_title(
                chat_id=chat_id,
                title=new_group_name
            )
        except Exception as e:
            logger.error(f"Failed to change group name: {e}")
    
    if not chat_state['deal_active'] or chat_state['current_deal_amount'] is None:
        await update.message.reply_text("No active deal. Use .pay first or .rcvd amount")
        await update.message.delete()
        return
    
    # Received message
    if chat_state['deal_type'] == 'crypto':
        rcvd_text = f"""<b>Payment Received</b>

I am holding ${chat_state['current_deal_amount']:,.0f} USD in crypto
You can continue your deal

<a href="https://{TOS_CHANNEL}">Terms of Service</a>"""
    else:
        rcvd_text = f"""<b>Payment Received</b>

I am holding ₹{chat_state['current_deal_amount']:,.0f} amount
You can continue your deal

<a href="https://{TOS_CHANNEL}">Terms of Service</a>"""
    
    sent_msg = await update.message.reply_text(
        text=rcvd_text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=False
    )
    
    # Pin the message
    await context.bot.pin_chat_message(
        chat_id=chat_id,
        message_id=sent_msg.message_id,
        disable_notification=True
    )
    
    # Delete the command
    await update.message.delete()

async def vouch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .vouch command - Admin only"""
    if not await is_admin(update, context):
        await update.message.delete()
        return
    
    chat_id = update.effective_chat.id
    
    # Vouch message
    vouch_text = f"""<b>Thank you for using my Middleman service!</b>

Please leave me a vouch here:
{VOUCH_LINK}

<b>Format:</b>
<code>Vouch {VOUCH_USERNAME} for MM'd</code>
<i>(Copy this format)</i>"""
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=vouch_text,
        parse_mode=ParseMode.HTML
    )
    
    # Delete the command
    await update.message.delete()

async def detect_vouch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detect vouch messages and show inline buttons"""
    if not update.message or not update.message.text:
        return
    
    chat_id = update.effective_chat.id
    message_text = update.message.text
    
    # Check if message contains vouch format
    vouch_pattern = rf'(?i)vouch\s+{re.escape(VOUCH_USERNAME)}\s+(?:for\s+)?(?:mm\'d|mmd|middleman)'
    
    if re.search(vouch_pattern, message_text):
        # Check if sender is admin
        if await is_admin(update, context):
            return  # Don't show buttons for admin's own vouch
        
        # Store the vouch message
        message_id = update.message.message_id
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        pending_vouches[message_id] = {
            'user_id': user_id,
            'username': username,
            'text': message_text,
            'chat_id': chat_id
        }
        
        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Send", callback_data=f"vouch_accept_{message_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"vouch_cancel_{message_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send notification to admin
        await update.message.reply_text(
            f"📝 <b>Vouch Detected!</b>\n\n"
            f"From: @{username}\n"
            f"Message: {message_text[:100]}\n\n"
            f"Approve or cancel this vouch:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
        # Also mention admin in the group
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ @seunko New vouch requires approval! Use buttons above.",
            parse_mode=ParseMode.HTML
        )

async def vouch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle vouch approval/cancellation"""
    query = update.callback_query
    await query.answer()
    
    # Check if user is admin
    user_id = update.effective_user.id
    if user_id != ADMIN_ID and not await is_admin(update, context):
        await query.edit_message_text("❌ You don't have permission to do this!")
        return
    
    data_parts = query.data.split('_')
    if len(data_parts) >= 3:
        action = data_parts[1]
        message_id = int(data_parts[2])
        
        if message_id in pending_vouches:
            vouch_data = pending_vouches[message_id]
            
            if action == 'accept':
                # Forward vouch to vouch channel
                try:
                    # Parse vouch channel
                    vouch_parts = VOUCH_CHANNEL.replace("t.me/", "").split("/")
                    channel_username = f"@{vouch_parts[0]}"
                    
                    # Forward the original message to vouch channel
                    await context.bot.forward_message(
                        chat_id=channel_username,
                        from_chat_id=vouch_data['chat_id'],
                        message_id=message_id
                    )
                    
                    await query.edit_message_text(
                        f"✅ <b>Vouch Approved & Forwarded!</b>\n\n"
                        f"From: @{vouch_data['username']}\n"
                        f"Message: {vouch_data['text'][:100]}\n\n"
                        f"Vouch has been forwarded to {VOUCH_CHANNEL}",
                        parse_mode=ParseMode.HTML
                    )
                    
                    # Send confirmation to the user
                    await context.bot.send_message(
                        chat_id=vouch_data['user_id'],
                        text=f"✅ Your vouch has been approved and published!\n\nThank you for your support! 🙏",
                        parse_mode=ParseMode.HTML
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to forward vouch: {e}")
                    await query.edit_message_text(
                        f"❌ Failed to forward vouch. Make sure bot is admin in vouch channel.\nError: {e}"
                    )
            
            elif action == 'cancel':
                await query.edit_message_text(
                    f"❌ <b>Vouch Cancelled</b>\n\n"
                    f"From: @{vouch_data['username']}\n"
                    f"Message: {vouch_data['text'][:100]}\n\n"
                    f"Vouch has been rejected.",
                    parse_mode=ParseMode.HTML
                )
                
                # Notify user
                await context.bot.send_message(
                    chat_id=vouch_data['user_id'],
                    text=f"❌ Your vouch has been rejected. Please check the format and try again.\n\nRequired format: <code>Vouch {VOUCH_USERNAME} for MM'd</code>",
                    parse_mode=ParseMode.HTML
                )
            
            # Remove from pending
            del pending_vouches[message_id]

async def send_vouch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /s command - Admin reply with /s to send vouch to channel"""
    if not update.message or not update.message.reply_to_message:
        return
    
    # Check if user is admin
    if not await is_admin(update, context):
        await update.message.delete()
        return
    
    # Check if command is /s
    if update.message.text.strip().lower() == '/s':
        replied_msg = update.message.reply_to_message
        
        # Check if replied message is a vouch
        vouch_pattern = rf'(?i)vouch\s+{re.escape(VOUCH_USERNAME)}\s+(?:for\s+)?(?:mm\'d|mmd|middleman)'
        
        if re.search(vouch_pattern, replied_msg.text or ''):
            try:
                # Parse vouch channel
                vouch_parts = VOUCH_CHANNEL.replace("t.me/", "").split("/")
                channel_username = f"@{vouch_parts[0]}"
                
                # Forward the message to vouch channel
                await context.bot.forward_message(
                    chat_id=channel_username,
                    from_chat_id=update.effective_chat.id,
                    message_id=replied_msg.message_id
                )
                
                await update.message.reply_text(
                    f"✅ Vouch forwarded to {VOUCH_CHANNEL}",
                    parse_mode=ParseMode.HTML
                )
                
            except Exception as e:
                logger.error(f"Failed to forward vouch via /s: {e}")
                await update.message.reply_text(f"❌ Failed to forward: {e}")
        
        await update.message.delete()

async def member_join_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new members joining the chat"""
    if not update.message:
        return
    
    chat_id = update.effective_chat.id
    
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            continue  # Skip bot itself
        
        # Send alert to group mentioning MM
        mention = f"<a href='tg://user?id={member.id}'>{member.first_name}</a>"
        user_info = f"@{member.username}" if member.username else f"ID: {member.id}"
        
        alert_text = (
            f"🔔 <b>New Member Joined!</b>\n\n"
            f"Name: {mention}\n"
            f"Username: {user_info}\n"
            f"User ID: <code>{member.id}</code>\n\n"
            f"Please verify this member before proceeding with deal!\n\n"
            f"<b>@seunko - Please check this user!</b>"
        )
        
        # Send alert to the group
        await context.bot.send_message(
            chat_id=chat_id,
            text=alert_text,
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"New member {member.id} joined chat {chat_id}")

async def com_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .com command - Mark deal as completed"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    
    if not await is_admin(update, context):
        await update.message.delete()
        return
    
    # Change group name to completed
    new_group_name = f"Sen's MM | Completed ⚫"
    try:
        await context.bot.set_chat_title(
            chat_id=chat_id,
            title=new_group_name
        )
    except Exception as e:
        logger.error(f"Failed to change group name: {e}")
    
    # Lock the group
    chat_state['group_locked'] = True
    
    # Completion message
    com_text = """<b>Deal Completed Successfully!</b>

Thank you for using me as your Middleman!

Your deal has been completed safely and securely.

<b>New messages will be auto-deleted.</b>

<b>Want to support?</b>
- Leave a vouch
- Share with friends
- Use again for future deals

Stay safe!"""
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=com_text,
        parse_mode=ParseMode.HTML
    )
    
    # Reset deal state
    chat_state['current_deal_amount'] = None
    chat_state['deal_active'] = False
    
    # Delete the command
    await update.message.delete()

async def lock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .lock command - Lock group without changing name"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    
    if not await is_admin(update, context):
        await update.message.delete()
        return
    
    # Lock ONLY this group - Auto delete new messages
    chat_state['group_locked'] = True
    
    # Lock message
    lock_text = """<b>Group Locked</b>

New messages will be auto-deleted.

Always deal with mm for extra security in deals."""
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=lock_text,
        parse_mode=ParseMode.HTML
    )
    
    # Delete the command
    await update.message.delete()

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .cancel command - Cancel deal"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    
    if not await is_admin(update, context):
        await update.message.delete()
        return
    
    # Lock the group
    chat_state['group_locked'] = True
    
    # Change group name to cancelled
    new_group_name = f"Sen's MM | Cancelled ❌"
    try:
        await context.bot.set_chat_title(
            chat_id=chat_id,
            title=new_group_name
        )
    except Exception as e:
        logger.error(f"Failed to change group name: {e}")
    
    # Cancellation message
    cancel_text = """<b>Deal Cancelled</b>

This deal has been cancelled.

<b>This group will be archived in 20 minutes.</b>

Please ensure all parties are aware of the cancellation."""
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=cancel_text,
        parse_mode=ParseMode.HTML
    )
    
    # Reset deal state
    chat_state['current_deal_amount'] = None
    chat_state['deal_active'] = False
    
    # Delete the command
    await update.message.delete()

async def unlock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .unlock command - Stop auto-deleting messages"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    
    if not await is_admin(update, context):
        await update.message.delete()
        return
    
    # Unlock ONLY this group
    chat_state['group_locked'] = False
    
    await update.message.reply_text("Group has been unlocked. Messages will no longer be auto-deleted.")
    
    # Delete the command
    await update.message.delete()

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages - Auto delete if THIS group is locked"""
    if not update.message:
        return
    
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    
    # Only auto-delete if THIS SPECIFIC group is locked
    if not chat_state['group_locked']:
        return
    
    # If group is locked, delete any new message from non-admin users
    user_id = update.effective_user.id
    
    # Check if sender is admin
    is_sender_admin = False
    if user_id == ADMIN_ID:
        is_sender_admin = True
    else:
        try:
            chat_member = await context.bot.get_chat_member(chat_id, user_id)
            is_sender_admin = chat_member.status in ['creator', 'administrator']
        except:
            is_sender_admin = False
    
    # Delete message if not from admin
    if not is_sender_admin:
        try:
            await update.message.delete()
            logger.info(f"Deleted message from non-admin user {user_id} in locked group {chat_id}")
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stat", stat_command))
    application.add_handler(CommandHandler("qr", qr_command))
    application.add_handler(CommandHandler("name", name_command))
    application.add_handler(CommandHandler("setname", setname_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add chnge command handler (owner only)
    application.add_handler(MessageHandler(
        filters.Regex(r'^[/.]chnge\s+') & filters.ChatType.PRIVATE,
        chnge_command
    ))
    # Also allow in groups (owner only)
    application.add_handler(MessageHandler(
        filters.Regex(r'^[/.]chnge\s+') & filters.ChatType.GROUPS,
        chnge_command
    ))
    
    # Add callback query handler for crypto selection and vouch
    application.add_handler(CallbackQueryHandler(crypto_callback, pattern='^crypto_'))
    application.add_handler(CallbackQueryHandler(vouch_callback, pattern='^vouch_'))
    
    # Handle pay command variations
    application.add_handler(MessageHandler(
        filters.Regex(r'^[/.]pay\s+\d+') & filters.ChatType.GROUPS,
        pay_command
    ))
    
    # Handle crypto command
    application.add_handler(MessageHandler(
        filters.Regex(r'^[/.]crypto\s+\d+') & filters.ChatType.GROUPS,
        crypto_command
    ))
    
    # Handle direct crypto commands (.eth, .btc, .sol, etc.)
    application.add_handler(MessageHandler(
        filters.Regex(r'(?i)^[/.](eth|btc|bnb|sol|ton|usdt|ltc)\s+\d+') & filters.ChatType.GROUPS,
        direct_crypto_command
    ))
    
    # Handle stat command variations
    application.add_handler(MessageHandler(
        filters.Regex(r'^[/.]stat$') & filters.ChatType.GROUPS,
        stat_command
    ))
    
    # Handle qr command variations
    application.add_handler(MessageHandler(
        filters.Regex(r'^[/.]qr$') & filters.ChatType.GROUPS,
        qr_command
    ))
    
    # Handle rcvd command (with or without amount)
    application.add_handler(MessageHandler(
        filters.Regex(r'^[/.]rcvd') & filters.ChatType.GROUPS,
        rcvd_command
    ))
    
    # Handle vouch command
    application.add_handler(MessageHandler(
        filters.Regex(r'^[/.]vouch$') & filters.ChatType.GROUPS,
        vouch_command
    ))
    
    # Handle /s command for forwarding vouch
    application.add_handler(MessageHandler(
        filters.Regex(r'^/s$') & filters.ChatType.GROUPS,
        send_vouch_command
    ))
    
    # Detect vouch messages
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS,
        detect_vouch
    ))
    
    # Handle member join events
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        member_join_handler
    ))
    
    # Handle com command
    application.add_handler(MessageHandler(
        filters.Regex(r'^[/.]com$') & filters.ChatType.GROUPS,
        com_command
    ))
    
    # Handle lock command
    application.add_handler(MessageHandler(
        filters.Regex(r'^[/.]lock$') & filters.ChatType.GROUPS,
        lock_command
    ))
    
    # Handle cancel command
    application.add_handler(MessageHandler(
        filters.Regex(r'^[/.]cancel$') & filters.ChatType.GROUPS,
        cancel_command
    ))
    
    # Handle unlock command
    application.add_handler(MessageHandler(
        filters.Regex(r'^[/.]unlock$') & filters.ChatType.GROUPS,
        unlock_command
    ))
    
    # Handle all messages for auto-delete feature
    application.add_handler(MessageHandler(
        filters.ALL & filters.ChatType.GROUPS,
        message_handler
    ))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Start bot
    print("Bot is running...")
    print("Make sure mm.jpg file exists in the same directory!")
    
    # Run the bot with proper error handling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()