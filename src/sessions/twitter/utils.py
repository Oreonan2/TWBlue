# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals
from builtins import str
from builtins import range
import url_shortener, re
import output
from twython import TwythonError
import config
import logging
import requests
import time
import sound
log = logging.getLogger("twitter.utils")
""" Some utilities for the twitter interface."""

__version__ = 0.1
__doc__ = "Find urls in tweets and #audio hashtag."

url_re = re.compile(r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))")

url_re2 = re.compile("(?:\w+://|www\.)[^ ,.?!#%=+][^ \\n\\t]*")
bad_chars = '\'\\\n.,[](){}:;"'

def find_urls_in_text(text):
 return  url_re2.findall(text)

def find_urls (tweet):
 urls = []
 # Let's add URLS from tweet entities.
 if "message_create" in tweet:
  entities = tweet["message_create"]["message_data"]["entities"]
 else:
  entities = tweet["entities"]
 for i in entities["urls"]:
  if i["expanded_url"] not in urls:
   urls.append(i["expanded_url"])
 if "quoted_status" in tweet:
  for i in tweet["quoted_status"]["entities"]["urls"]:
   if i["expanded_url"] not in urls:
    urls.append(i["expanded_url"])
 if "retweeted_status" in tweet:
  for i in tweet["retweeted_status"]["entities"]["urls"]:
   if i["expanded_url"] not in urls:
    urls.append(i["expanded_url"])
  if "quoted_status" in tweet["retweeted_status"]:
   for i in tweet["retweeted_status"]["quoted_status"]["entities"]["urls"]:
    if i["expanded_url"] not in urls:
     urls.append(i["expanded_url"])
 if "message" in tweet:
  i = "message"
 elif "full_text" in tweet:
  i = "full_text"
 else:
  i = "text"
 if "message_create" in tweet:
  extracted_urls = find_urls_in_text(tweet["message_create"]["message_data"]["text"])
 else:
  extracted_urls = find_urls_in_text(tweet[i])
 # Don't include t.co links (mostly they are photos or shortened versions of already added URLS).
 for i in extracted_urls:
  if i not in urls and "https://t.co" not in i:
   urls.append(i)
 return urls

def find_item(id, listItem):
 for i in range(0, len(listItem)):
  if listItem[i]["id"] == id: return i
 return None

def find_list(name, lists):
 for i in range(0, len(lists)):
  if lists[i]["name"] == name:  return lists[i]["id"]

def find_previous_reply(id, listItem):
 for i in range(0, len(listItem)):
  if listItem[i]["id_str"] == str(id): return i
 return None

def find_next_reply(id, listItem):
 for i in range(0, len(listItem)):
  if listItem[i]["in_reply_to_status_id_str"] == str(id): return i
 return None

def is_audio(tweet):
 try:
  if len(find_urls(tweet)) < 1:
   return False
  if "message_create" in tweet:
   entities = tweet["message_create"]["message_data"]["entities"]
  else:
   entities = tweet["entities"]
  if len(entities["hashtags"]) > 0:
   for i in entities["hashtags"]:
    if i["text"] == "audio":
     return True
 except IndexError:
  print(tweet["entities"]["hashtags"])
  log.exception("Exception while executing is_audio hashtag algorithm")

def is_geocoded(tweet):
 if "coordinates" in tweet and tweet["coordinates"] != None:
  return True

def is_media(tweet):
 if "message_create" in tweet:
  entities = tweet["message_create"]["message_data"]["entities"]
 else:
  entities = tweet["entities"]
 if ("media" in entities) == False:
  return False
 for i in entities["media"]:
  if "type" in i and i["type"] == "photo":
   return True
 return False

def get_all_mentioned(tweet, conf, field="screen_name"):
 """ Gets all users that has been mentioned."""
 results = []
 for i in tweet["entities"]["user_mentions"]:
  if i["screen_name"] != conf["user_name"] and i["screen_name"] != tweet["user"]["screen_name"]:
   if i[field] not in results:
    results.append(i[field])
 return results

def get_all_users(tweet, conf):
 string = []
 if "retweeted_status" in tweet:
  string.append(tweet["user"]["screen_name"])
  tweet = tweet["retweeted_status"]
 if "sender" in tweet:
  string.append(tweet["sender"]["screen_name"])
 else:
  if tweet["user"]["screen_name"] != conf["user_name"]:
   string.append(tweet["user"]["screen_name"])
  for i in tweet["entities"]["user_mentions"]:
   if i["screen_name"] != conf["user_name"] and i["screen_name"] != tweet["user"]["screen_name"]:
    if i["screen_name"] not in string:
     string.append(i["screen_name"])
 if len(string) == 0:
  string.append(tweet["user"]["screen_name"])
 return string

def if_user_exists(twitter, user):
 try:
  data = twitter.show_user(screen_name=user)
  return data
 except TwythonError as err:
  if err.error_code == 404:
   return None
  else:
   return user

def api_call(parent=None, call_name=None, preexec_message="", success="", success_snd="", *args, **kwargs):
 if preexec_message:
  output.speak(preexec_message, True)
 try:
  val = getattr(parent.twitter.twitter, call_name)(*args, **kwargs)
  output.speak(success)
  parent.parent.sound.play(success_snd)
 except TwythonError as e:
  output.speak("Error %s: %s" % (e.error_code, e.msg), True)
  parent.parent.sound.play("error.ogg")
 return val

def is_allowed(tweet, settings, buffer_name):
 clients = settings["twitter"]["ignored_clients"]
 if "sender" in tweet: return True
 allowed = True
 tweet_data = {}
 if "retweeted_status" in tweet:
  tweet_data["retweet"] = True
 if tweet["in_reply_to_status_id_str"] != None:
  tweet_data["reply"] = True
 if "quoted_status" in tweet:
  tweet_data["quote"] = True
 if "retweeted_status" in tweet: tweet = tweet["retweeted_status"]
 source = re.sub(r"(?s)<.*?>", "", tweet["source"])
 for i in clients:
  if i.lower() == source.lower():
   return False
 return filter_tweet(tweet, tweet_data, settings, buffer_name)

def filter_tweet(tweet, tweet_data, settings, buffer_name):
 if "full_text" in tweet:
  value = "full_text"
 else:
  value = "text"
 for i in settings["filters"]:
  if settings["filters"][i]["in_buffer"] == buffer_name:
   regexp = settings["filters"][i]["regexp"]
   word = settings["filters"][i]["word"]
   # Added if/else for compatibility reasons.
   if "allow_rts" in settings["filters"][i]:
    allow_rts = settings["filters"][i]["allow_rts"]
   else:
    allow_rts = "True"
   if "allow_quotes" in settings["filters"][i]:
    allow_quotes = settings["filters"][i]["allow_quotes"]
   else:
    allow_quotes = "True"
   if "allow_replies" in settings["filters"][i]:
    allow_replies = settings["filters"][i]["allow_replies"]
   else:
    allow_replies = "True"
   if allow_rts == "False" and "retweet" in tweet_data:
    return False
   if allow_quotes == "False" and "quote" in tweet_data:
    return False
   if allow_replies == "False" and "reply" in tweet_data:
    return False
   if word != "" and settings["filters"][i]["if_word_exists"]:
    if word in tweet[value]:
     return False
   elif word != "" and settings["filters"][i]["if_word_exists"] == False:
    if word not in tweet[value]:
     return False
   if settings["filters"][i]["in_lang"] == "True":
    if tweet["lang"] not in settings["filters"][i]["languages"]:
     return False
   elif settings["filters"][i]["in_lang"] == "False":
    if tweet["lang"] in settings["filters"][i]["languages"]:
     return False
 return True

def twitter_error(error):
 if error.error_code == 403:
  msg = _(u"Sorry, you are not authorised to see this status.")
 elif error.error_code == 404:
  msg = _(u"No status found with that ID")
 else:
  msg = _(u"Error code {0}").format(error.error_code,)
 output.speak(msg)