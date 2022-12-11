# -*- coding: utf-8 -*-
import arrow
import languageHandler
from .  import utils, templates

def compose_post(post, db, relative_times, show_screen_names):
    if show_screen_names == False:
        user = post.account.get("display_name")
        if user == "":
            user = post.account.get("username")
    else:
        user = post.account.get("acct")
    original_date = arrow.get(post.created_at)
    if relative_times:
        ts = original_date.humanize(locale=languageHandler.curLang[:2])
    else:
        ts = original_date.shift(hours=db["utc_offset"]).format(_("dddd, MMMM D, YYYY H:m"), locale=languageHandler.curLang[:2])
    if post.reblog != None:
        text = _("Boosted from @{}: {}").format(post.reblog.account.acct, templates.process_text(post.reblog))
    else:
        text = templates.process_text(post)
    source = post.get("application", "")
    # "" means remote user, None for legacy apps so we should cover both sides.
    if source != None and source != "":
        source = source.get("name", "")
    else:
        source = ""
    return [user+", ", text, ts+", ", source]

def compose_user(user, db, relative_times=True, show_screen_names=False):
    original_date = arrow.get(user.created_at)
    if relative_times:
        ts = original_date.humanize(locale=languageHandler.curLang[:2])
    else:
        ts = original_date.shift(hours=db["utc_offset"]).format(_("dddd, MMMM D, YYYY H:m:s"), locale=languageHandler.curLang[:2])
    name = user.display_name
    if name == "":
        name = user.get("username")
    return [_("%s (@%s). %s followers, %s following, %s posts. Joined %s") % (name, user.acct, user.followers_count, user.following_count,  user.statuses_count, ts)]

def compose_conversation(conversation, db, relative_times, show_screen_names):
    users = []
    for account in conversation.accounts:
        if account.display_name != "":
            users.append(account.display_name)
        else:
            users.append(account.username)
    users = ", ".join(users)
    last_post = compose_post(conversation.last_status, db, relative_times, show_screen_names)
    text = _("Last message from {}: {}").format(last_post[0], last_post[1])
    return [users, text, last_post[-2], last_post[-1]]