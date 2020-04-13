#!/usr/bin/env python3

import twitter
import subprocess as sp
import datetime, re
from datetime import time
from t import ACCESS_TOKEN_KEY, ACCESS_TOKEN_SECRET, CONSUMER_KEY, CONSUMER_SECRET
from t import dow, month
from t import date_ordinals as ordinals
from bs4 import BeautifulSoup
import requests
from Vocalizer import Vocalizer

def niceSoundingDate(date):
    date = date.split()
    date = date[0:3]
    date[0] = dow[date[0]]
    date[1] = month[date[1]]
    date[2] = ordinals[int(date[2])-1]
    return ' '.join(date)



def espeak(text, *args):
    print(args)
    args_list = ["espeak-ng", text]

    if args: args_list += list(args)

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
                                                        hour,minute, am_pm,
                                                        dow, month, day)
    response = re.sub("\s\s+", " ", response)
    response += " Here are some recent tweets from your timeline"
    print(response)
    # espeak(response)


# converts the date of a tweet into a number based only on year/month/day
def date2int(date):
    return date.year*10000 + date.month*100 + date.day



def check_for_holiday(date):
        #TODO: check for holidays and append to greeting
    pass



def format_response(tweet):
    if tweet.quoted_status is not None:
        quoter = tweet.user.name
        quoter_sp = tweet.spoken_tweet
        quoted = tweet.quoted_status.user.name
        quoted_sp = tweet.quoted_status.spoken_tweet
        resp = "%s quoted %s's tweet." %(quoter, quoted)
        resp += " the quoted tweet says %s." %(quoted_sp)
        resp += " % added this. %s" %(quoter,quoter_sp)

    elif tweet.retweeted_status is not None:
        retwtr = tweet.user.name
        retwtd = tweet.retweeted_status.user.name
        retwtd_sp = tweet.retweeted_status.spoken_tweet
        resp = "%s retweeted the following tweet by %s. " %(retwtr,retwtd)
        resp += retwtd_sp

    else:
        tweeter = tweet.user.name
        speak = tweet.spoken_tweet
        resp = "This is a tweet from %s. %s" %(tweeter, speak)

    return resp


def main(api):
    count = 80
    max_id = None
    tweets = []
    while len(tweets) < 20:
        # print("max_id = ", max_id)
        temp = api.GetHomeTimeline(count=count, max_id=max_id, exclude_replies=True)
        numTemps = len(temp)
        print("number of tweets returned from api = ",numTemps)
        temp.sort(key = lambda x: x.id, reverse = True)
        # print("oldest tweet returned from api is ",temp[numTemps-1].id)
        max_id = temp[numTemps-1].id
        # print("newest tweet returned from api is ",temp[0].id)
        numAdded = 0
        for t in temp:
            if t.lang == 'en':
                unmentionables = [t.current_user_retweet,
                                  t.in_reply_to_screen_name,
                                  t.in_reply_to_status_id,
                                  t.in_reply_to_user_id,
                                  t.quoted_status,t.retweeted_status]
                if not any(unmentionables):
                    numAdded+=1
                    tweets.append(t)
        # print("number of tweets added to tweets list = ",numAdded)
        print("number of tweets saved is ",len(tweets))
        # to delete duplicates:
        # 1: sort tweets based on id
        # 2: loop through tweets list, deleting duplicates
        tweets.sort(key = lambda x: x.id, reverse = True)
        i,j = 0,1
        numDel = 0
        while j < len(tweets):
            if tweets[i] == tweets[j]:
                del tweets[j]
                numDel += 1
            else:
                i, j = i+1, j+1
        # if there are more than 20 tweets, reduce it to 20
        # print("number of dup tweets deleted is ", numDel)
        # for t in tweets:
        #     print(t.id)
        # print("")

        if len(tweets) > 20:
            print("reducing tweets from ",len(tweets))
            tweets = tweets[:20]
            print("to ",len(tweets))
        input("press enter to continue")

    spoken_tweets = [Vocalizer(tweet) for tweet in tweets]
    cur_date = date2int(datetime.datetime.now()) + 1
    # eventually we should put the greeting in a shell script
    # greeting(cur_date)
    # add one to current date so we ensure
    # it will always get spoken first time thru for-loop

    greeting(datetime.datetime.now())

    for tweet in spoken_tweets:
        date = datetime.date.fromtimestamp(tweet._status.created_at_in_seconds)
        tweet_date = date2int(date)
        if tweet_date < cur_date:
            spk_date = niceSoundingDate(tweet.created_at)
            # espeak(spk_date)
            print(spk_date)
            cur_date = tweet_date

        response = format_response(tweet)
        print("result of formatting the tweet:\n\n" + response)
        input("press any key to continue")
        print("============================================")
        print("============================================")
        # espeak(response)

if __name__ == "__main__":
    api = twitter.Api(consumer_key=CONSUMER_KEY,
                      consumer_secret=CONSUMER_SECRET,
                      access_token_key=ACCESS_TOKEN_KEY,
                      access_token_secret=ACCESS_TOKEN_SECRET,
                      tweet_mode='extended')
    main(api)
