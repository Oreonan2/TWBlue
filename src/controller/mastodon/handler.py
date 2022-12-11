# -*- coding: utf-8 -*-
import wx
import logging
from pubsub import pub
from mysc import restart
from wxUI.dialogs.mastodon import dialogs
from wxUI.dialogs.mastodon import search as search_dialogs
from wxUI.dialogs.mastodon import dialogs
from wxUI import commonMessageDialogs
from sessions.twitter import utils
from . import userActions, settings

log = logging.getLogger("controller.mastodon.handler")

class Handler(object):

    def __init__(self):
        super(Handler, self).__init__()

    def create_buffers(self, session, createAccounts=True, controller=None):
        session.get_user_info()
        name = session.get_name()
        if createAccounts == True:
            pub.sendMessage("core.create_account", name=name, session_id=session.session_id, logged=True)
        root_position =controller.view.search(name, name)
        for i in session.settings['general']['buffer_order']:
            if i == 'home':
                pub.sendMessage("createBuffer", buffer_type="BaseBuffer", session_type=session.type, buffer_title=_("Home"), parent_tab=root_position, start=False, kwargs=dict(parent=controller.view.nb, function="timeline_home", name="home_timeline", sessionObject=session, account=name, sound="tweet_received.ogg"))
            elif i == 'local':
                pub.sendMessage("createBuffer", buffer_type="BaseBuffer", session_type=session.type, buffer_title=_("Local"), parent_tab=root_position, start=False, kwargs=dict(parent=controller.view.nb, function="timeline_local", name="local_timeline", sessionObject=session, account=name, sound="tweet_received.ogg"))
            elif i == 'federated':
                pub.sendMessage("createBuffer", buffer_type="BaseBuffer", session_type=session.type, buffer_title=_("Federated"), parent_tab=root_position, start=False, kwargs=dict(parent=controller.view.nb, function="timeline_public", name="federated_timeline", sessionObject=session, account=name, sound="tweet_received.ogg"))
            elif i == 'mentions':
                pub.sendMessage("createBuffer", buffer_type="MentionsBuffer", session_type=session.type, buffer_title=_("Mentions"), parent_tab=root_position, start=False, kwargs=dict(parent=controller.view.nb, function="notifications", name="mentions", sessionObject=session, account=name, sound="mention_received.ogg"))
            elif i == 'direct_messages':
                pub.sendMessage("createBuffer", buffer_type="ConversationListBuffer", session_type=session.type, buffer_title=_("Direct messages"), parent_tab=root_position, start=False, kwargs=dict(compose_func="compose_conversation", parent=controller.view.nb, function="conversations", name="direct_messages", sessionObject=session, account=name, sound="dm_received.ogg"))
            elif i == 'sent':
                pub.sendMessage("createBuffer", buffer_type="BaseBuffer", session_type=session.type, buffer_title=_("Sent"), parent_tab=root_position, start=False, kwargs=dict(parent=controller.view.nb, function="account_statuses", name="sent", sessionObject=session, account=name, sound="tweet_received.ogg", id=session.db["user_id"]))
            elif i == 'favorites':
                pub.sendMessage("createBuffer", buffer_type="BaseBuffer", session_type=session.type, buffer_title=_("Favorites"), parent_tab=root_position, start=False, kwargs=dict(parent=controller.view.nb, function="favourites", name="favorites", sessionObject=session, account=name, sound="favourite.ogg"))
            elif i == 'bookmarks':
                pub.sendMessage("createBuffer", buffer_type="BaseBuffer", session_type=session.type, buffer_title=_("Bookmarks"), parent_tab=root_position, start=False, kwargs=dict(parent=controller.view.nb, function="bookmarks", name="bookmarks", sessionObject=session, account=name, sound="favourite.ogg"))
            elif i == 'followers':
                pub.sendMessage("createBuffer", buffer_type="UserBuffer", session_type=session.type, buffer_title=_("Followers"), parent_tab=root_position, start=False, kwargs=dict(parent=controller.view.nb, compose_func="compose_user", function="account_followers", name="followers", sessionObject=session, account=name, sound="update_followers.ogg", id=session.db["user_id"]))
            elif i == 'following':
                pub.sendMessage("createBuffer", buffer_type="UserBuffer", session_type=session.type, buffer_title=_("Following"), parent_tab=root_position, start=False, kwargs=dict(parent=controller.view.nb, compose_func="compose_user", function="account_following", name="following", sessionObject=session, account=name, sound="update_followers.ogg", id=session.db["user_id"]))
            elif i == 'muted':
                pub.sendMessage("createBuffer", buffer_type="UserBuffer", session_type=session.type, buffer_title=_("Muted users"), parent_tab=root_position, start=False, kwargs=dict(parent=controller.view.nb, compose_func="compose_user", function="mutes", name="muted", sessionObject=session, account=name))
            elif i == 'blocked':
                pub.sendMessage("createBuffer", buffer_type="UserBuffer", session_type=session.type, buffer_title=_("Blocked users"), parent_tab=root_position, start=False, kwargs=dict(parent=controller.view.nb, compose_func="compose_user", function="blocks", name="blocked", sessionObject=session, account=name))
        pub.sendMessage("createBuffer", buffer_type="EmptyBuffer", session_type="base", buffer_title=_("Timelines"), parent_tab=root_position, start=False, kwargs=dict(parent=controller.view.nb, name="timelines", account=name))
        timelines_position =controller.view.search("timelines", name)
        for i in session.settings["other_buffers"]["timelines"]:
                pub.sendMessage("createBuffer", buffer_type="BaseBuffer", session_type=session.type, buffer_title=i, parent_tab=timelines_position, start=False, kwargs=dict(parent=controller.view.nb, function="account_statuses", name="%s-timeline".format(i), sessionObject=session, account=name, sound="tweet_timeline.ogg", id=i))
        for i in session.settings["other_buffers"]["followers_timelines"]:
            pub.sendMessage("createBuffer", buffer_type="UserBuffer", session_type=session.type, buffer_title=_("Followers for {}").format(i), parent_tab=timelines_position, start=False, kwargs=dict(parent=controller.view.nb, compose_func="compose_user", function="account_followers", name="%s-followers" % (i,), sessionObject=session, account=name, sound="new_event.ogg", id=i))
        for i in session.settings["other_buffers"]["following_timelines"]:
            pub.sendMessage("createBuffer", buffer_type="UserBuffer", session_type=session.type, buffer_title=_("Following for {}").format(i), parent_tab=timelines_position, start=False, kwargs=dict(parent=controller.view.nb, compose_func="compose_user", function="account_following", name="%s-following" % (i,), sessionObject=session, account=name, sound="new_event.ogg", id=i))
#        pub.sendMessage("createBuffer", buffer_type="EmptyBuffer", session_type="base", buffer_title=_("Lists"), parent_tab=root_position, start=False, kwargs=dict(parent=controller.view.nb, name="lists", name))
#        lists_position =controller.view.search("lists", session.db["user_name"])
#        for i in session.settings["other_buffers"]["lists"]:
#            pub.sendMessage("createBuffer", buffer_type="ListBuffer", session_type=session.type, buffer_title=_(u"List for {}").format(i), parent_tab=lists_position, start=False, kwargs=dict(parent=controller.view.nb, function="list_timeline", name="%s-list" % (i,), sessionObject=session, name, bufferType=None, sound="list_tweet.ogg", list_id=utils.find_list(i, session.db["lists"]), include_ext_alt_text=True, tweet_mode="extended"))
        pub.sendMessage("createBuffer", buffer_type="EmptyBuffer", session_type="base", buffer_title=_("Searches"), parent_tab=root_position, start=False, kwargs=dict(parent=controller.view.nb, name="searches", account=name))
#        searches_position =controller.view.search("searches", session.db["user_name"])
#        for i in session.settings["other_buffers"]["tweet_searches"]:
#            pub.sendMessage("createBuffer", buffer_type="SearchBuffer", session_type=session.type, buffer_title=_(u"Search for {}").format(i), parent_tab=searches_position, start=False, kwargs=dict(parent=controller.view.nb, function="search_tweets", name="%s-searchterm" % (i,), sessionObject=session, name, bufferType="searchPanel", sound="search_updated.ogg", q=i, include_ext_alt_text=True, tweet_mode="extended"))
#        for i in session.settings["other_buffers"]["trending_topic_buffers"]:
#            pub.sendMessage("createBuffer", buffer_type="TrendsBuffer", session_type=session.type, buffer_title=_("Trending topics for %s") % (i), parent_tab=root_position, start=False, kwargs=dict(parent=controller.view.nb, name="%s_tt" % (i,), sessionObject=session, name, trendsFor=i, sound="trends_updated.ogg"))

    def start_buffer(self, controller, buffer):
        if hasattr(buffer, "finished_timeline") and buffer.finished_timeline == False:
            change_title = True
        else:
            change_title = False
        try:
            buffer.start_stream(play_sound=False)
        except Exception as err:
            log.exception("Error %s starting buffer %s on account %s, with args %r and kwargs %r." % (str(err), buffer.name, buffer.account, buffer.args, buffer.kwargs))
        if change_title:
            pub.sendMessage("buffer-title-changed", buffer=buffer)

    def open_conversation(self, controller, buffer):
        post = buffer.get_item()
        if post.reblog != None:
            post = post.reblog
        conversations_position =controller.view.search("direct_messages", buffer.session.get_name())
        pub.sendMessage("createBuffer", buffer_type="ConversationBuffer", session_type=buffer.session.type, buffer_title=_("Conversation with {0}").format(post.account.acct), parent_tab=conversations_position, start=True, kwargs=dict(parent=controller.view.nb, function="status_context", name="%s-conversation" % (post.id,), sessionObject=buffer.session, account=buffer.session.get_name(), sound="search_updated.ogg", post=post, id=post.id))

    def follow(self, buffer):
        if not hasattr(buffer, "get_item"):
            return
        item = buffer.get_item()
        if buffer.type == "user":
            users = [item.acct]
        elif buffer.type == "baseBuffer":
            if item.reblog != None:
                users = [user.acct for user in item.reblog.mentions if user.id != buffer.session.db["user_id"]]
                if item.reblog.account.acct not in users and item.account.id != buffer.session.db["user_id"]:
                    users.insert(0, item.reblog.account.acct)
            else:
                users = [user.acct for user in item.mentions if user.id != buffer.session.db["user_id"]]
            if item.account.acct not in users:
                users.insert(0, item.account.acct)
        u = userActions.userActions(buffer.session, users)

    def search(self, controller, session, value):
        log.debug("Creating a new search...")
        dlg = search_dialogs.searchDialog(value)
        if dlg.ShowModal() == wx.ID_OK and dlg.term.GetValue() != "":
            term = dlg.term.GetValue()
            searches_position =controller.view.search("searches", session.get_name())
            if dlg.posts.GetValue() == True:
                if term not in session.settings["other_buffers"]["post_searches"]:
                    session.settings["other_buffers"]["post_searches"].append(term)
                    session.settings.write()
#                    pub.sendMessage("createBuffer", buffer_type="SearchBuffer", session_type=session.type, buffer_title=_("Search for {}").format(term), parent_tab=searches_position, start=True, kwargs=dict(parent=controller.view.nb, function="search_tweets", name="%s-searchterm" % (term,), sessionObject=session, account=session.get_name(), bufferType="searchPanel", sound="search_updated.ogg", q=term, include_ext_alt_text=True, tweet_mode="extended"))
                else:
                    log.error("A buffer for the %s search term is already created. You can't create a duplicate buffer." % (term,))
                    return
            elif dlg.users.GetValue() == True:
                pub.sendMessage("createBuffer", buffer_type="UserBuffer", session_type=session.type, buffer_title=_("Search for {}").format(term), parent_tab=searches_position, start=True, kwargs=dict(parent=controller.view.nb, compose_func="compose_user", function="account_search", name="%s-searchUser" % (term,), sessionObject=session, account=session.get_name(), sound="search_updated.ogg", q=term))
        dlg.Destroy()

    # ToDo: explore how to play sound & save config differently.
    # currently, TWBlue will play the sound and save the config for the timeline even if the buffer did not load or something else.
    def open_timeline(self, controller, buffer):
        if not hasattr(buffer, "get_item"):
            return
        item = buffer.get_item()
        if buffer.type == "user":
            users = [item.acct]
        elif buffer.type == "baseBuffer":
            if item.reblog != None:
                users = [user.acct for user in item.reblog.mentions if user.id != buffer.session.db["user_id"]]
                if item.reblog.account.acct not in users and item.account.id != buffer.session.db["user_id"]:
                    users.insert(0, item.reblog.account.acct)
            else:
                users = [user.acct for user in item.mentions if user.id != buffer.session.db["user_id"]]
            if item.account.acct not in users and item.account.id != buffer.session.db["user_id"]:
                users.insert(0, item.account.acct)
                u = userActions.UserTimeline(buffer.session, users)
                if u.dialog.ShowModal() == wx.ID_OK:
                    action = u.process_action()
                    if action == None:
                        return
                    user = u.user
                    if action == "posts":
                        if user.statuses_count == 0:
                            dialogs.no_posts()
                            return
                        if user.id in buffer.session.settings["other_buffers"]["timelines"]:
                            commonMessageDialogs.timeline_exist()
                            return
                        timelines_position =controller.view.search("timelines", buffer.session.get_name())
                        pub.sendMessage("createBuffer", buffer_type="BaseBuffer", session_type=buffer.session.type, buffer_title=_("Timeline for {}").format(user.username,), parent_tab=timelines_position, start=True, kwargs=dict(parent=controller.view.nb, function="account_statuses", name="%s-timeline" % (user.id,), sessionObject=buffer.session, account=buffer.session.get_name(), sound="tweet_timeline.ogg", id=user.id))
                        buffer.session.settings["other_buffers"]["timelines"].append(user.id)
                        buffer.session.sound.play("create_timeline.ogg")
                    elif action == "followers":
                        if user.followers_count == 0:
                            dialogs.no_followers()
                            return
                        if user.id in buffer.session.settings["other_buffers"]["followers_timelines"]:
                            commonMessageDialogs.timeline_exist()
                            return
                        timelines_position =controller.view.search("timelines", buffer.session.get_name())
                        pub.sendMessage("createBuffer", buffer_type="UserBuffer", session_type=buffer.session.type, buffer_title=_("Followers for {}").format(user.username,), parent_tab=timelines_position, start=True, kwargs=dict(parent=controller.view.nb, compose_func="compose_user", function="account_followers", name="%s-followers" % (user.id,), sessionObject=buffer.session, account=buffer.session.get_name(), sound="new_event.ogg", id=user.id))
                        buffer.session.settings["other_buffers"]["followers_timelines"].append(user.id)
                        buffer.session.sound.play("create_timeline.ogg")
                    elif action == "following":
                        if user.following_count == 0:
                            dialogs.no_following()
                            return
                        if user.id in buffer.session.settings["other_buffers"]["following_timelines"]:
                            commonMessageDialogs.timeline_exist()
                            return
                        timelines_position =controller.view.search("timelines", buffer.session.get_name())
                        pub.sendMessage("createBuffer", buffer_type="UserBuffer", session_type=buffer.session.type, buffer_title=_("Following for {}").format(user.username,), parent_tab=timelines_position, start=True, kwargs=dict(parent=controller.view.nb, compose_func="compose_user", function="account_following", name="%s-followers" % (user.id,), sessionObject=buffer.session, account=buffer.session.get_name(), sound="new_event.ogg", id=user.id))
                        buffer.session.settings["other_buffers"]["following_timelines"].append(user.id)
                        buffer.session.sound.play("create_timeline.ogg")
        buffer.session.settings.write()

    def account_settings(self, buffer, controller):
        d = settings.accountSettingsController(buffer, controller)
        if d.response == wx.ID_OK:
            d.save_configuration()
            if d.needs_restart == True:
                commonMessageDialogs.needs_restart()
                buffer.session.settings.write()
                buffer.session.save_persistent_data()
                restart.restart_program()