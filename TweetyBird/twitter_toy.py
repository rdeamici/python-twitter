#!/usr/bin/env python3

import twitter
import subprocess as sp
import datetime, re
from datetime import time
from t import ACCESS_TOKEN_KEY, ACCESS_TOKEN_SECRET, CONSUMER_KEY, CONSUMER_SECRET
from t import dow, month
from t import date_ordinals as ordinals
from ekphrasis.classes.segmenter import Segmenter
from bs4 import BeautifulSoup
'''
This class essentially extends the twitter.status object.
It adds a new class variable speakable_text, that is a version of
the full_text variable suited for speaking out loud by a TTS engine.
Goal is to use it in an alarm to read texts to the user.
'''
class Vocalizer():
    # cass variable that gets instantiated during class definition
    # All instances of class variable gets the same segmenter
    # it takes a while (more than 2 seconds) to instantiate a segmenter
    # and all class instances will use the same corpus
    hashtag_seg = Segmenter(corpus = "english")
    api = None

    headers = requests.utils.default_headers()
    headers.update({ 'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'})

    def __init__(self, Status, Api):
        # Vocalizer class contains a Status class with all its functionality
        self.status = Status

        if Status.retweeted_status is not None:
            self.tweet_text = Status.retweeted_status.quo_full_text
        else:
            self.tweet_text = Status.full_text

        if Status.hashtags and len(Status.hashtags) > 0:
            self.hashtags_info = [ get_hashtag_info(h) for h in Status.hashtags]
        else:
            self.hashtags_info = None

        if Status.urls and len(Status.urls) > 0:
            self.urls_info = [self.get_url_info(u) for u in Status.urls]

        if Status.media and len(Status.media) > 0:
            self.media_info = [self.get_media_info(m) for m in Status.media]

        if Status.user_mentions and len(Status.user_mentions) > 0:
            self.mentions_info = [self.get_mentions_info(um) for um in Status.user_mentions]

        self.unspeakables = map_funcs(functions = {'mentions': self.get_mentions_info,
                                                  'media': self.get_media_info,
                                                   'urls': self.get_url_info,
                                                   'hashtags': self.get_hashtag_info
                                                   },
                                      data = {'mentions': self.user_mentions,
                                               'media': self.media,
                                               'urls': self.urls,
                                               'hashtags': self.hashtags})

        self.speak = self.create_spoken_tweet()


    def map_funcs(functions, data):
        unspeakables = {}
        for key in data:
        unspeakables[key] = list(map(functions[key], data[key]))

    def create_spoken_tweet(self):
        self.speak = self.tweet_text.repl

    def get_mentions_info(self,mention):
        return {'name': mention.name,
                'mention': '@{}'.format(mention.screen_name)
                }


    def get_media_info(self, media):
        return "animated gif" if media.type == "animated_gif" else media.type


    def get_url_info(self, Url):
        url = Url.url
        eurl = Url.expanded_url
        req = requests.get(eurl)
        soup = BeautifulSoup(req.content, 'html.parser')
        site_name = soup.find("meta",property = "og:site_name").get('content')
        title = soup.find("meta",property = "og:title").get('content')
        description = soup.find("meta",property = "og:description").get('content')
        if description.endswith('...'):
            description = ""
        return {'unspeakable':url,
                'speakable': {'site_name':site_name,
                              'title':title,
                              'desc':description
                              }
            }


    def get_hashtag_info(self, h):
        return {'unspeakable': "#%s"%h.text, 'speakable': hashtag_seg.segment(text)}





def niceSoundingDate(date):
    date = date.split()
    date = date[0:3]
    date[0] = dow[date[0]]
    date[1] = month[date[1]]
    date[2] = ordinals[int(date[2])-1]
    return ' '.join(date)



def espeak(text, *args):
    print(args)
    args_list = ["espeak-ng"]

    if args:
        args_list.extend([text].extend(args))
    else:
        args_list.append(text)

    sp.run(args_list)



def greeting(date):
    if date.minute == 0:
        minute = ""
    elif date.minute < 10:
        minute = "oh {}".format(date.minute)
    else:
        minute = date.minute

    dow = date.strftime('%A')
    month = date.strftime('%B')
    day = ordinals[date.day - 1]
    am_pm = date.strftime('%p')

    if date.hour < 12:
        greeting = "Good Morning!"
    elif date.hour < 18:
        greeting = "Good Afternoon!"
    else:
        greeting = "Good Evening!"

    hour = date.strftime('%I')

    if hour.startswith('0'): hour = hour[1]
    response = "{0} It is {1} {2} {3} on {4}, {5} {6}."
                .format(greeting, hour, minute, am_pm, dow, month, day)
    response = re.sub("\s\s+", " ", response)
    response += " Here are some recent tweets from your timeline"
    print(response)
    # espeak(response)



def date2int(date):
    return date.year*10000 + date.month*100 + date.day



def check_for_holiday(date):
        #TODO: check for holidays and append to greeting
    pass



def format_response(tweet):
    top_level_tweet_text = audible_text(tweet.full_text)

    if tweet.in_reply_to_status_id:
        original_tweet = api.GetStatus(tweet.in_reply_to_status_id)
        original_auth = original_tweet.user.name
        original_text = remove_http(original_tweet.full_text)
        response = "{} tweeted {}. ".format(original_auth,original_text)
        response += "To which {} replied: {}".format(tweet.user.name,                                                     top_level_tweet_text)
    elif tweet.quoted_status:
        quo_tweet = tweet.quoted_status
        quo_full_text = remove_http(quo_tweet.full_text)
        response = """{} quoted {}'s tweet that says {}.
        And then {} added {}."""
        .format(tweet.user.name, quo_tweet.user.name,
                quo_full_text, top_level_tweet_text)
    elif tweet.retweeted_status:
        retweeted_text = remove_http(tweet.retweeted_status.full_text)
        response = """{} retweeted the following
        tweet by {}. {}"""
        .format(tweet.user.name, tweet.retweeted_status.user.name,
                retweeted_text)
    else:
        response = "{} tweeted {}".format(tweet.user.name, top_level_tweet_text)

    return response



def main(api):
    count = 20
    tweets = []
    Vocalizer.api = api
    while count > 0:
        since_id = tweets[0.id if len(tweets) > 0 else None
        statuses = api.GetHomeTimeline(count=count, since_id=since_id,
                                       exclude_replies=True)
        tweets += [s for s in statuses if s.lang == 'en']
        tweets.sort(key= lambda x: x.id)
        count -= len(tweets)

    spoken_statuses = [Vocalizer(status,api) for status in statuses]
    cur_date = datetime.datetime.now()
    # eventually we should put the greeting in a shell script
    # greeting(cur_date)
    # add one to current date so we ensure
    # it will always get spoken first time thru for-loop
    cur_date = date2int(cur_date) + 1

    # this is all effed up and needs to be fixed eventually
    for tweet in spoken_statuses:
        date = datetime.date.fromtimestamp(tweet.created_at_in_seconds)
        tweet_date = date2int(date)
        if tweet_date < cur_date:
            spk_date = niceSoundingDate(tweet.created_at)
            # espeak(spk_date)
            print(spk_date)
            cur_date = tweet_date

        response = tweet.speak
        print(response)
        input("press any key to continue")
        # espeak(response)

if __name__ == "__main__":
    api = twitter.Api(consumer_key=CONSUMER_KEY,
                      consumer_secret=CONSUMER_SECRET,
                      access_token_key=ACCESS_TOKEN_KEY,
                      access_token_secret=ACCESS_TOKEN_SECRET,
                      tweet_mode='extended')
    main(api)
