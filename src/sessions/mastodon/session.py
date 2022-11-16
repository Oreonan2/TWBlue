# -*- coding: utf-8 -*-
import os
import paths
import time
import logging
import webbrowser
import wx
import mastodon
import config
import config_utils
import output
import application
from mastodon import MastodonError, MastodonNotFoundError, MastodonUnauthorizedError
from pubsub import pub
from mysc.thread_utils import call_threaded
from sessions import base
from sessions.mastodon import utils
from .wxUI import authorisationDialog

log = logging.getLogger("sessions.mastodonSession")

MASTODON_VERSION = "4.0.1"

class Session(base.baseSession):

    def __init__(self, *args, **kwargs):
        super(Session, self).__init__(*args, **kwargs)
        self.config_spec = "mastodon.defaults"
        self.supported_languages = []
        self.type = "mastodon"
        self.db["pagination_info"] = dict()
        self.char_limit = 500

    def login(self, verify_credentials=True):
        if self.settings["mastodon"]["access_token"] != None and self.settings["mastodon"]["instance"] != None:
            try:
                log.debug("Logging in to Mastodon instance {}...".format(self.settings["mastodon"]["instance"]))
                self.api = mastodon.Mastodon(access_token=self.settings["mastodon"]["access_token"], api_base_url=self.settings["mastodon"]["instance"], mastodon_version=MASTODON_VERSION)
                if verify_credentials == True:
                    credentials = self.api.account_verify_credentials()
                    self.db["user_name"] = credentials["username"]
                    self.db["user_id"] = credentials["id"]
                    self.settings["mastodon"]["user_name"] = credentials["username"]
                self.logged = True
                log.debug("Logged.")
                self.counter = 0
            except IOError:
                log.error("The login attempt failed.")
                self.logged = False
        else:
            self.logged = False
            raise Exceptions.RequireCredentialsSessionError

    def authorise(self):
        if self.logged == True:
            raise Exceptions.AlreadyAuthorisedError("The authorisation process is not needed at this time.")
        authorisation_dialog = wx.TextEntryDialog(None, _("Please enter your instance URL."), _("Mastodon instance"))
        answer = authorisation_dialog.ShowModal()
        instance = authorisation_dialog.GetValue()
        authorisation_dialog.Destroy()
        if answer != wx.ID_OK:
            return
        client_id, client_secret = mastodon.Mastodon.create_app("TWBlue", api_base_url=authorisation_dialog.GetValue(), website="https://twblue.es")
        temporary_api = mastodon.Mastodon(client_id=client_id, client_secret=client_secret, api_base_url=instance, mastodon_version=MASTODON_VERSION)
        authorisation_dialog.Destroy()
        auth_url = temporary_api.auth_request_url()
        webbrowser.open_new_tab(auth_url)
        verification_dialog = wx.TextEntryDialog(None, _("Enter the verification code"), _("PIN code authorization"))
        answer = verification_dialog.ShowModal()
        code = verification_dialog.GetValue()
        verification_dialog.Destroy()
        if answer != wx.ID_OK:
            return
        access_token = temporary_api.log_in(code=verification_dialog.GetValue())
        self.settings["mastodon"]["access_token"] = access_token
        self.settings["mastodon"]["instance"] = instance
        self.settings.write()

    def get_user_info(self):
        """ Retrieves some information required by TWBlue for setup."""
        # retrieve the current user's UTC offset so we can calculate dates properly.
        offset = time.timezone if (time.localtime().tm_isdst == 0) else time.altzone
        offset = offset / 60 / 60 * -1
        self.db["utc_offset"] = offset
        if len(self.supported_languages) == 0:
            self.supported_languages = self.api.instance().languages
        self.get_lists()
        self.get_muted_users()
        # determine instance custom characters limit.
        instance = self.api.instance()
        if hasattr(instance, "max_post_chars"):
            self.char_limit = instance.max_post_chars
        self.settings.write()

    def get_lists(self):
        """ Gets the lists that the user is subscribed to and stores them in the database. Returns None."""
        self.db["lists"] = self.api.lists()

    def get_muted_users(self):
        ### ToDo: Use a function to retrieve all muted users.
        self.db["muted_users"] = self.api.mutes()

    def get_user_alias(self, user):
        aliases = self.settings.get("user-aliases")
        if aliases == None:
            log.error("Aliases are not defined for this config spec.")
            return user.name
        user_alias = aliases.get(user.id_str)
        if user_alias != None:
            return user_alias
        return user.name

    def check_streams(self):
        pass

    def order_buffer(self, name, data, ignore_older=False):
        num = 0
        last_id = None
        if self.db.get(name) == None:
            self.db[name] = []
        objects = self.db[name]
        if ignore_older and len(self.db[name]) > 0:
            if self.settings["general"]["reverse_timelines"] == False:
                last_id = self.db[name][0].id
            else:
                last_id = self.db[name][-1].id
        for i in data:
            if ignore_older and last_id != None:
                if i.id < last_id:
                    log.error("Ignoring an older tweet... Last id: {0}, tweet id: {1}".format(last_id, i.id))
                    continue
            if utils.find_item(i, self.db[name]) == None:
                if self.settings["general"]["reverse_timelines"] == False: objects.append(i)
                else: objects.insert(0, i)
                num = num+1
        self.db[name] = objects
        return num

    def api_call(self, call_name, action="", _sound=None, report_success=False, report_failure=True, preexec_message="", *args, **kwargs):
        finished = False
        tries = 0
        if preexec_message:
            output.speak(preexec_message, True)
        while finished==False and tries < 25:
            try:
                val = getattr(self.api, call_name)(*args, **kwargs)
                finished = True
            except MastodonError as e:
                output.speak(str(e))
                val = None
                if type(e) != MastodonNotFoundError  and type(e) != MastodonUnauthorizedError :
                    tries = tries+1
                    time.sleep(5)
                elif report_failure:
                    output.speak(_("%s failed.  Reason: %s") % (action, str(e)))
                finished = True
#   except:
#    tries = tries + 1
#    time.sleep(5)
        if report_success:
            output.speak(_("%s succeeded.") % action)
        if _sound != None: self.sound.play(_sound)
        return val

    def send_post(self, reply_to=None, users=None, visibility=None, posts=[]):
        """ Convenience function to send a thread. """
        in_reply_to_id = reply_to
        for obj in posts:
            text = obj.get("text")
            if len(obj["attachments"]) == 0:
                item = self.api_call(call_name="status_post", status=text, _sound="tweet_send.ogg",  in_reply_to_id=in_reply_to_id, visibility=visibility, sensitive=obj["sensitive"], spoiler_text=obj["spoiler_text"])
                if item != None:
                    in_reply_to_id = item["id"]
            else:
                media_ids = []
                poll = None
                if len(obj["attachments"]) == 1 and obj["attachments"][0]["type"] == "poll":
                    poll = self.api.make_poll(options=obj["attachments"][0]["options"], expires_in=obj["attachments"][0]["expires_in"], multiple=obj["attachments"][0]["multiple"], hide_totals=obj["attachments"][0]["hide_totals"])
                else:
                    for i in obj["attachments"]:
                        img = self.api_call("media_post", media_file=i["file"], description=i["description"])
                        media_ids.append(img.id)
                item = self.api_call(call_name="status_post", status=text, _sound="tweet_send.ogg", in_reply_to_id=in_reply_to_id, media_ids=media_ids, visibility=visibility, poll=poll, sensitive=obj["sensitive"], spoiler_text=obj["spoiler_text"])
                if item != None:
                    in_reply_to_id = item["id"]

    def get_name(self):
        instance = self.settings["mastodon"]["instance"]
        instance = instance.replace("https://", "")
        user = self.settings["mastodon"]["user_name"]
        return "Mastodon: {}@{}".format(user, instance)