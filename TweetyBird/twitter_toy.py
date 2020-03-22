#!/usr/bin/env python3

import twitter
import requests
import subprocess as sp
import datetime, re
from datetime import time
from t import ACCESS_TOKEN_KEY, ACCESS_TOKEN_SECRET, CONSUMER_KEY, CONSUMER_SECRET
from t import dow, month
from t import date_ordinals as ordinals


# this class takes a single tweet and turns it into something producable by a TTS engine
class Vocalizer(twitter.models.Status):
    # TODO: wrap the Status class with the below functions
    def __init__(self, Tweet):
        self.tweet = Tweet
        self.speakable = audible_text()

    def audible_text():
        original_text = delete_audibles(tweet.full_text)
        # TODO: format text based on other properties of tweet object
        audible_text = ''
        text_flags = [0]*len(original_text)
        urls = tweet.urls
        user_mentions = tweet.user_mentions
        hashtags = tweet.hashtags
        # 1 == characters to delete
        # 2 == user_names to expand from user_name to display names
        # 3 == hashtags to process into a more readable form
        for url in urls:
            i,j = url.indices
            text_flags[i:j] = [1]*(j-i)
        for m in user_mentions:
            i,j = m.indices
            text_flags[i] = [2]
            i += 1
            text_flags[i] = [2, m.name]
            text_flags[i:j] = [2]*(j-i)
        for h in hashtags:
            i,j = h.hashtags
            text_flags[i:j] = [3]*(j-1)

        #final processing step
        for i in range(len(text_flags)):
            if text_flags[i]==0:
                audible_text += text[i]
            elif text_flags[i]==2:
                start = i
                while text_flags[i] == 2:
                    i += 1
                    stop = i
                    audible_text += user_name(original_text,i,j)
                    new_text += ' '
        
        user_mentions = tweet.user_mentions
        for m in user_mentions:
            indices = m.indices



    def user_name(user_name,i,j):
        tweet.user_mentions
            



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
    response = "{0} It is {1} {2} {3} on {4}, {5} {6}.".format(greeting,
                                                               hour, minute,
                                                               am_pm, dow,
                                                               month, day)
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
        response += "To which {} replied: {}".format(tweet.user.name,
                                                     top_level_tweet_text)
    elif tweet.quoted_status:
        quo_tweet = tweet.quoted_status
        quo_full_text = remove_http(quo_tweet.full_text)
        response = """{} quoted {}'s tweet that says {}. 
        And then {} added {}.""".format(tweet.user.name,
                                        quo_tweet.user.name,
                                        quo_full_text,
                                        top_level_tweet_text)
    elif tweet.retweeted_status:
        retweeted_text = remove_http(tweet.retweeted_status.full_text)
        response = """{} retweeted the following 
        tweet by {}. {}""".format(tweet.user.name,
                                  tweet.retweeted_status.user.name,
                                  retweeted_text)
    else:
        response = "{} tweeted {}".format(tweet.user.name, top_level_tweet_text)
    return response



def main(api):
    tweets = api.GetHomeTimeline(count=20, exclude_replies=True)
    speakable_tweets = [Vocalizer(tweet) for tweet in tweets] 
    cur_date = datetime.datetime.now()
    # eventually we should put the greeting in a shell script
    greeting(cur_date)
    # add one to current date so we ensure
    #it will always get spoken first time thru for-loop
    cur_date = date2int(cur_date) + 1
    for speakable_tweet in speakable_tweets:
        tweet_date = date2int(datetime.date.fromtimestamp(tweet.created_at_in_seconds))
        if tweet_date < cur_date:
            spk_date = niceSoundingDate(tweet.created_at)
            # espeak(spk_date)
            print(spk_date)
            cur_date = tweet_date

        response = speakable_tweet.speak 
        print(response)
        input("press any key to continue")
        # espeak(response)

if __name__ == "__main__":
    api = twitter.Api(consumer_key=CONSUMR_KEY,
                      consumer_secret=CONSUMER_SECRET,
                      access_token_key=ACCESS_TOKEN_KEY,
                      access_token_secret=ACCESS_TOKEN_SECRET,
                      tweet_mode='extended')
        
    main(api)
