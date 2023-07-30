import datetime
import html
import textwrap
import random

import bs4
import jikanpy
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update, InputMediaPhoto
from telegram.ext import CallbackContext, CallbackQueryHandler, run_async

from Naomi import DEV_USERS, DRAGONS, OWNER_ID, dispatcher
from Naomi.modules.disable import DisableAbleCommandHandler

info_btn = "More Information"
kaizoku_btn = "Kaizoku ☠️"
kayo_btn = "Kayo 🏴‍☠️"
prequel_btn = "⬅️ Prequel"
sequel_btn = "Sequel ➡️"
close_btn = "Close ❌"
searches = dict()
result_imgs = [
    "https://te.legra.ph//file/69927554852c3f444ef79.jpg",
]


def shorten(description, info="anilist.co"):
    msg = ""
    if len(description) > 700:
        description = description[0:500] + "...."
        msg += f"\n➳ *Description:* _{description}_[Read More]({info})"
    else:
        msg += f"\n➳ *Description:*_{description}_"
    return msg


# time formatter from uniborg
def t(milliseconds: int) -> str:
    """Inputs time in milliseconds, to get beautified time,
    as string"""
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = (
        ((str(days) + " Days, ") if days else "")
        + ((str(hours) + " Hours, ") if hours else "")
        + ((str(minutes) + " Minutes, ") if minutes else "")
        + ((str(seconds) + " Seconds, ") if seconds else "")
        + ((str(milliseconds) + " ms, ") if milliseconds else "")
    )
    return tmp[:-2]


airing_query = """
    query ($id: Int,$search: String) { 
      Media (id: $id, type: ANIME,search: $search) { 
        id
        episodes
        title {
          romaji
          english
          native
        }
        nextAiringEpisode {
           airingAt
           timeUntilAiring
           episode
        } 
      }
    }
    """

fav_query = """
query ($id: Int) { 
      Media (id: $id, type: ANIME) { 
        id
        title {
          romaji
          english
          native
        }
     }
}
"""

anime_query = """
   query ($id: Int,$search: String) { 
      Media (id: $id, type: ANIME,search: $search) { 
        id
        title {
          romaji
          english
          native
        }
        description (asHtml: false)
        startDate{
            year
          }
          episodes
          season
          type
          format
          status
          duration
          siteUrl
          studios{
              nodes{
                   name
              }
          }
          trailer{
               id
               site 
               thumbnail
          }
          averageScore
          genres
          bannerImage
      }
    }
"""
character_query = """
    query ($query: String) {
        Character (search: $query) {
               id
               name {
                     first
                     last
                     full
               }
               siteUrl
               image {
                        large
               }
               description
        }
    }
"""

manga_query = """
query ($id: Int,$search: String) { 
    Media (id: $id, type: MANGA,search: $search) { 
        id
        title {
            romaji
            english
            native
        }
        description (asHtml: false)
        startDate{
            year
            month
            day
        }
        endDate{
           year
           month
           day
        }   
        type
        format
        chapters
        volumes
        status
        siteUrl
        averageScore
        genres
        bannerImage
    }
}
"""

anilist_query = """
query ($id: Int, $page: Int, $perPage: Int, $search: String, $type: MediaType) {
    Page (page: $page, perPage: $perPage) {
        pageInfo {
            total
        }
        media (id: $id, search: $search, type: $type) {
            id

            title {
                romaji
                english
                native
            }
            siteUrl
        }
    }
}
"""

url = "https://graphql.anilist.co"

def searchanilist(search, manga=False):
    typea = "MANGA" if manga else "ANIME"
    variables = {"search": search, "type": typea, "page": 1, "perPage": 10}
    response = requests.post(
        url, json={"query": anilist_query, "variables": variables}
    )
    msg = ""
    jsonData = response.json()
    res = list(jsonData.keys())
    if "errors" in res:
        msg += f"**Error** : `{jsonData['errors'][0]['message']}`"
        return msg, False
    return jsonData["data"]["Page"]["media"], True
    
@run_async
def airing(update: Update, context: CallbackContext):
    message = update.effective_message
    search_str = message.text.split(" ", 1)
    if len(search_str) == 1:
        update.effective_message.reply_text(
            "Tell Anime Name :) ( /airing <anime name>)"
        )
        return
    variables = {"search": search_str[1]}
    response = requests.post(
        url, json={"query": airing_query, "variables": variables}
    ).json()["data"]["Media"]
    msg = f"*Name*: *{response['title']['romaji']}*(`{response['title']['native']}`)\n*ID*: `{response['id']}`"
    if response["nextAiringEpisode"]:
        time = response["nextAiringEpisode"]["timeUntilAiring"] * 1000
        time = t(time)
        msg += f"\n*Episode*: `{response['nextAiringEpisode']['episode']}`\n*Airing In*: `{time}`"
    else:
        msg += f"\n*Episode*:{response['episodes']}\n*Status*: `N/A`"
    update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


@run_async
def anime(update: Update, context: CallbackContext):
    message = update.effective_message
    search = message.text.split(" ", 1)
    
    if len(search) == 1:
        update.effective_message.reply_text("Format : /anime <anime name>")
        return
    else:
        search = search[1]

    result, ok = searchanilist(search)
    
    if not ok:
        update.effective_message.reply_text(result)
        return
    if not result:
        update.effective_message.reply_text("Anime not found")
        return
    
    search_id = str(hash(search))
    searches[search_id] = search
    buttons = [
        [
            InlineKeyboardButton(
                anime["title"]["english"] or anime["title"]["romaji"],
                callback_data=f"anime:{search_id}:{message.from_user.id}:{anime['id']}"
            )
        ]
        for anime in result
    ]
    
    update.effective_message.reply_photo(
        photo=random.choice(result_imgs),
        caption=f"Search results for *{search}*:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@run_async
def anime_button(update: Update, context: CallbackContext):
    bot = context.bot
    query = update.callback_query
    message = query.message
    data = query.data.split(":")
    back_hash = data[1]
    button_user = int(data[2])
    anime_id = data[3]

    if button_user != query.from_user.id:
        query.answer("You are not the one who issued the command.")
        return

    query.answer("Processing ...")

    variables = {"id": anime_id}
    json = requests.post(url, json={"query": anime_query, "variables": variables}).json()
    res = list(json.keys())
    
    if "errors" in res:
        query.answer("Anime not found")
        return
    
    if json:
        json = json["data"]["Media"]
        msg = (
            f"➳ *Title : {json['title']['romaji']}* (`{json['title']['native']}`)\n"
            f"➳ *Type:* {json['format']}\n➳ *Status:* {json['status']}\n"
            f"➳ *Episodes:* {json.get('episodes', 'N/A')}\n"
            f"➳ *Duration:* {json.get('duration', 'N/A')} Per Ep.\n"
            f"➳ *Score:* {json['averageScore']}\n➳ *Genres:* `{' '.join(json['genres'])}`\n"
            f"➳ *Studios:* `{' '.join(studio['name'] for studio in json['studios']['nodes'])}`\n"
        )
        
        info = json.get("siteUrl")
        trailer = json.get("trailer", None)
        siteid = json.get('id')
        bannerimg = json.get("bannerImage") or ""
        coverimg = json.get("coverImage") or ""
        title_img = f"https://img.anili.st/media/{siteid}"
        
        if trailer:
            trailer_id = trailer.get("id", None)
            site = trailer.get("site", None)
            if site == "youtube":
                trailer = "https://youtu.be/" + trailer_id
        
        description = (
            json.get("description", "N/A")
            .replace("<i>", "")
            .replace("</i>", "")
            .replace("<br>", "")
        )
        msg += shorten(description, info)
        buttons = [
            [
                InlineKeyboardButton("🔖 More Info 🔖", url=info),
                InlineKeyboardButton("Trailer 🎬", url=trailer),
            ]
        ] if trailer else [[InlineKeyboardButton("🔖 More Info 🔖", url=info)]]
        buttons = []
        buttons.append([InlineKeyboardButton("« Back", callback_data=f"anilist_back:anime:{back_hash}:{button_user}")])

        if title_img:
            try:
                message.edit_media(
                    media=InputMediaPhoto(title_img),
                    caption=msg,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardButton(buttons),
                )
            except:
                raise
                msg += f" [〽️]({title_img})"
                bot.send_message(
                    message.chat.id,
                    msg,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(buttons[:-1]),
                )
                message.delete()
        else:
            bot.send_message(
                message.chat.id,
                msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons),
            )


@run_async
def character(update: Update, context: CallbackContext):
    message = update.effective_message
    search = message.text.split(" ", 1)
    if len(search) == 1:
        update.effective_message.reply_text("Format : /character < character name >")
        return
    search = search[1]
    variables = {"query": search}
    json = requests.post(
        url, json={"query": character_query, "variables": variables}
    ).json()
    if "errors" in json.keys():
        update.effective_message.reply_text("Character not found")
        return
    if json:
        json = json["data"]["Character"]
        msg = f"*{json.get('name').get('full')}*(`{json.get('name').get('native')}`)\n"
        description = f"{json['description']}"
        site_url = json.get("siteUrl")
        msg += shorten(description, site_url)
        image = json.get("image", None)
        if image:
            image = image.get("large")
            update.effective_message.reply_photo(
                photo=image,
                caption=msg.replace("<b>", "</b>"),
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            update.effective_message.reply_text(
                msg.replace("<b>", "</b>"), parse_mode=ParseMode.MARKDOWN
            )


@run_async
def manga(update: Update, context: CallbackContext):
    message = update.effective_message
    search = message.text.split(" ", 1)
    
    if len(search) == 1:
        update.effective_message.reply_text("Format : /manga <manga name>")
        return
    
    search = search[1]

    result, ok = searchanilist(search, manga=True)
    
    if not ok:
        update.effective_message.reply_text(result)
        return
    if not result:
        update.effective_message.reply_text("Manga not found")
        return
    
    search_id = str(hash(search))
    searches[search_id] = search
    buttons = [
        [
            InlineKeyboardButton(
                manga["title"]["english"] or manga["title"]["romaji"],
                callback_data=f"manga:{search_id}:{message.from_user.id}:{manga['id']}"
            )
        ]
        for manga in result
    ]
    
    update.effective_message.reply_photo(
        photo=random.choice(result_imgs),
        caption=f"Search results for *{search}*:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@run_async
def manga_button(update: Update, context: CallbackContext):
    bot = context.bot
    query = update.callback_query
    message = query.message
    data = query.data.split(":")
    back_hash = data[1]
    button_user = int(data[2])
    manga_id = data[3]

    if button_user != query.from_user.id:
        query.answer("You are not the one who issued the command.")
        return

    query.answer("Processing ...")

    variables = {"id": manga_id}
    json = requests.post(url, json={"query": manga_query, "variables": variables}).json()

    res = list(json.keys())
    msg = ""
    if "errors" in res:
        query.answer("Manga not found.")
        return
    
    if json:
        json = json["data"]["Media"]
        title, title_native, title_english = json["title"].get("romaji", False), json["title"].get(
            "native", False
        ), json["title"].get("english", False)
        start_year, start_month, start_day, end_year, end_month, end_day, status, score, chapters, volumes = (
            json["startDate"].get("year", False),
            json["startDate"].get("month", False),
            json["startDate"].get("day", False),
            json["endDate"].get("year", False),
            json["endDate"].get("month", False),
            json["endDate"].get("day", False),
            json.get("status", False),
            json.get("averageScore", False),
            json.get("chapters", False),
            json.get("volumes", False),
        )
        
        if title:
            msg += f"➳ *Title: {title}*"
            if title_english:
                msg += f" | {title_english}"
                
        if start_year:
            msg += f"\n➳ *Start Date:* {start_day}/{start_month}/{start_year}"
            
        if end_year:
            msg += f"\n➳ *End Date:* {end_day}/{end_month}/{end_year}"
        else:
            msg += f"\n➳ *End Date:* NA"
            
        if status:
            msg += f"\n➳ *Status:* {status}"
            
        if score:
            msg += f"\n➳ *Score:* {score}"
            
        if chapters:
            msg += f"\n➳ *Chapter No:* {chapters}"
        else:
            msg += f"\n➳ *Chapters No:* NA"
            
        if volumes:
            msg += f"\n➳ *Volume Count:* {volumes}"
        else:
            msg += f"\n➳ *Volumes Count:* NA"
            
        msg += "\n➳ *Genres:* "
        for x in json.get("genres", []):
            msg += f"{x}, "
        msg = msg[:-2]
        
        info = json["siteUrl"]
        buttons = [
            [
                InlineKeyboardButton("More Info", url=info)
            ]
        ]
        buttons = [
            [
                InlineKeyboardButton("« Back", callback_data=f"anilist_back:manga:{back_hash}:{button_user}")
            ]
        ]
        image = f"https://img.anili.st/media/{json.get('id')}"
        msg += f"\n\n➳ *Description:*_{bs4.BeautifulSoup(json.get('description', None), features='html.parser').text}_"
        
        if image:
            try:
                message.edit_media(
                    media=InputMediaPhoto(image),
                    caption=msg,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardButton(buttons),
                )
            except Exception:
                raise
                msg += f" [〽️]({image})"
                bot.send_message(
                    message.chat.id,
                    msg,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(buttons[:-1]),
                )
                message.delete()
        else:
            bot.send_message(
                message.chat.id,
                msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons),
            )

@run_async
def anilist_back(update: Update, context: CallbackContext):
    query = update.callback_query
    message = query.message
    data = query.data.split(":")
    button_user = int(data[3])
    search_id = data[2]
    typea = data[1]

    if button_user != query.from_user.id:
        query.answer("You are not the one who issued the command.")
        return

    search = searches.get(search_id, None)
    if search is None:
        query.answer("This is an old button. Please redo the command!")
        return
    
    query.answer("Processing ...")
    result, ok = searchanilist(search, manga=typea == "manga")

    if not result:
        query.answer(f"{typea} not found")
        return

    buttons = [
        [
            InlineKeyboardButton(
                item["title"]["english"] or item["title"]["romaji"],
                callback_data=f"{typea}:{search_id}:{button_user}:{item['id']}",
            )
        ]
        for item in result
    ]
    
    message.edit_media(
        media=InputMediaPhoto(random.choice(result_imgs)),
        caption=f"Search results for *{search}*:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )

@run_async
def user(update: Update, context: CallbackContext):
    message = update.effective_message
    args = message.text.strip().split(" ", 1)

    try:
        search_query = args[1]
    except:
        if message.reply_to_message:
            search_query = message.reply_to_message.text
        else:
            update.effective_message.reply_text("Format : /user <username>")
            return

    jikan = jikanpy.jikan.Jikan()

    try:
        user = jikan.user(search_query)
    except jikanpy.APIException:
        update.effective_message.reply_text("Username not found.")
        return

    progress_message = update.effective_message.reply_text("Searching.... ")

    date_format = "%Y-%m-%d"
    if user["image_url"] is None:
        img = "https://cdn.myanimelist.net/images/questionmark_50.gif"
    else:
        img = user["image_url"]

    try:
        user_birthday = datetime.datetime.fromisoformat(user["birthday"])
        user_birthday_formatted = user_birthday.strftime(date_format)
    except:
        user_birthday_formatted = "Unknown"

    user_joined_date = datetime.datetime.fromisoformat(user["joined"])
    user_joined_date_formatted = user_joined_date.strftime(date_format)

    for entity in user:
        if user[entity] is None:
            user[entity] = "Unknown"

    about = user["about"].split(" ", 60)

    try:
        about.pop(60)
    except IndexError:
        pass

    about_string = " ".join(about)
    about_string = about_string.replace("<br>", "").strip().replace("\r\n", "\n")

    caption = ""

    caption += textwrap.dedent(
        f"""
    ➳*Username*: [{user['username']}]({user['url']})
    ➳*Gender*: `{user['gender']}`
    ➳*Birthday*: `{user_birthday_formatted}`
    ➳*Joined*: `{user_joined_date_formatted}`
    ➳*Days wasted watching anime*: `{user['anime_stats']['days_watched']}`
    ➳*Days wasted reading manga*: `{user['manga_stats']['days_read']}`
    """
    )

    caption += f"*About*: {about_string}"

    buttons = [
        [InlineKeyboardButton(info_btn, url=user["url"])],
        [
            InlineKeyboardButton(
                close_btn, callback_data=f"anime_close, {message.from_user.id}"
            )
        ],
    ]

    update.effective_message.reply_photo(
        photo=img,
        caption=caption,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=False,
    )
    progress_message.delete()


@run_async
def upcoming(update: Update, context: CallbackContext):
    jikan = jikanpy.jikan.Jikan()
    upcoming = jikan.top("anime", page=1, subtype="upcoming")

    upcoming_list = [entry["title"] for entry in upcoming["top"]]
    upcoming_message = ""

    for entry_num in range(len(upcoming_list)):
        if entry_num == 10:
            break
        upcoming_message += f"{entry_num + 1}. {upcoming_list[entry_num]}\n"

    update.effective_message.reply_text(upcoming_message)


def button(update: Update, context: CallbackContext):
    bot = context.bot
    query = update.callback_query
    message = query.message
    data = query.data.split(", ")
    query_type = data[0]
    original_user_id = int(data[1])

    user_and_admin_list = [original_user_id, OWNER_ID] + DRAGONS + DEV_USERS

    bot.answer_callback_query(query.id)
    if query_type == "anime_close":
        if query.from_user.id in user_and_admin_list:
            message.delete()
        else:
            query.answer("You are not allowed to use this.")


def site_search(update: Update, context: CallbackContext, site: str):
    message = update.effective_message
    args = message.text.strip().split(" ", 1)
    more_results = True

    try:
        search_query = args[1]
    except IndexError:
        message.reply_text("Give something to search")
        return

    if site == "kaizoku":
        search_url = f"https://animekaizoku.com/?s={search_query}"
        html_text = requests.get(search_url).text
        soup = bs4.BeautifulSoup(html_text, "html.parser")
        search_result = soup.find_all("h2", {"class": "post-title"})

        if search_result:
            result = f"<b>Search results for</b> <code>{html.escape(search_query)}</code> <b>on</b> <code>AnimeKaizoku</code>: \n"
            for entry in search_result:
                post_link = "https://animekaizoku.com/" + entry.a["href"]
                post_name = html.escape(entry.text)
                result += f"• <a href='{post_link}'>{post_name}</a>\n"
        else:
            more_results = False
            result = f"<b>No result found for</b> <code>{html.escape(search_query)}</code> <b>on</b> <code>AnimeKaizoku</code>"

    elif site == "kayo":
        search_url = f"https://animekayo.com/?s={search_query}"
        html_text = requests.get(search_url).text
        soup = bs4.BeautifulSoup(html_text, "html.parser")
        search_result = soup.find_all("h2", {"class": "title"})

        result = f"<b>Search results for</b> <code>{html.escape(search_query)}</code> <b>on</b> <code>AnimeKayo</code>: \n"
        for entry in search_result:

            if entry.text.strip() == "Nothing Found":
                result = f"<b>No result found for</b> <code>{html.escape(search_query)}</code> <b>on</b> <code>AnimeKayo</code>"
                more_results = False
                break

            post_link = entry.a["href"]
            post_name = html.escape(entry.text.strip())
            result += f"• <a href='{post_link}'>{post_name}</a>\n"

    buttons = [[InlineKeyboardButton("See all results", url=search_url)]]

    if more_results:
        message.reply_text(
            result,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True,
        )
    else:
        message.reply_text(
            result, parse_mode=ParseMode.HTML, disable_web_page_preview=True
        )


@run_async
def kaizoku(update: Update, context: CallbackContext):
    site_search(update, context, "kaizoku")


@run_async
def kayo(update: Update, context: CallbackContext):
    site_search(update, context, "kayo")


__help__ = """
*Get information about anime, manga or characters from* [AniList](anilist.co).
*Available commands:*
 ❍ /anime <anime>*:* returns information about the anime.
 ❍ /character <character>*:* returns information about the character.
 ❍ /animequotes *:* Get random Anime qoute.
 ❍ /manga <manga>*:* returns information about the manga.
 ❍ /user <user>*:* returns information about a MyAnimeList user.
 ❍ /latest *:* to know ongoing anime schedule.
 ❍ /kaizoku <anime>*:* search an anime on animekaizoku.com
 ❍ /kayo <anime>*:* search an anime on animekayo.com
 ❍ /airing <anime>*:* returns anime airing info.
 """

ANIME_HANDLER = DisableAbleCommandHandler("anime", anime)
ANIME_BUTTON_HANDLER = CallbackQueryHandler(anime_button, pattern="anime:.*")
AIRING_HANDLER = DisableAbleCommandHandler("airing", airing)
CHARACTER_HANDLER = DisableAbleCommandHandler("character", character)
MANGA_HANDLER = DisableAbleCommandHandler("manga", manga)
MANGA_BUTTON_HANDLER = CallbackQueryHandler(manga_button, pattern="manga:.*")
ANILIST_BACK_HANDLER = CallbackQueryHandler(anilist_back, pattern="anilist_back:.*")
USER_HANDLER = DisableAbleCommandHandler("user", user)
UPCOMING_HANDLER = DisableAbleCommandHandler("upcoming", upcoming)
KAIZOKU_SEARCH_HANDLER = DisableAbleCommandHandler("kaizoku", kaizoku)
KAYO_SEARCH_HANDLER = DisableAbleCommandHandler("kayo", kayo)
BUTTON_HANDLER = CallbackQueryHandler(button, pattern="anime_.*")


dispatcher.add_handler(BUTTON_HANDLER)
dispatcher.add_handler(ANIME_HANDLER)
dispatcher.add_handler(ANIME_BUTTON_HANDLER)
dispatcher.add_handler(CHARACTER_HANDLER)
dispatcher.add_handler(MANGA_HANDLER)
dispatcher.add_handler(MANGA_BUTTON_HANDLER)
dispatcher.add_handler(ANILIST_BACK_HANDLER)
dispatcher.add_handler(AIRING_HANDLER)
dispatcher.add_handler(USER_HANDLER)
dispatcher.add_handler(KAIZOKU_SEARCH_HANDLER)
dispatcher.add_handler(KAYO_SEARCH_HANDLER)
dispatcher.add_handler(UPCOMING_HANDLER)


__command_list__ = [
    "anime",
    "manga",
    "character",
    "user",
    "upcoming",
    "kaizoku",
    "airing",
    "kayo",
]
__handlers__ = [
    ANIME_HANDLER,
    CHARACTER_HANDLER,
    MANGA_HANDLER,
    USER_HANDLER,
    UPCOMING_HANDLER,
    KAIZOKU_SEARCH_HANDLER,
    KAYO_SEARCH_HANDLER,
    BUTTON_HANDLER,
    AIRING_HANDLER,
]
__mod_name__ = "🇦ɴɪᴍᴇ"
