import twitter
import datetime, re
import ftfy
from num2words import num2words
from datetime import time
from ekphrasis.classes.segmenter import Segmenter
from ekphrasis.classes.preprocessor import TextPreProcessor
from ekphrasis.classes.tokenizer import Tokenizer
from ekphrasis.dicts.emo_unicode import EMOTICONS, UNICODE_EMO, EMOTICONS_EMO
from ekphrasis.classes.exmanager import ExManager
from ekphrasis.dicts.noslang.slangdict import slangdict as SLANGDICT

from bs4 import BeautifulSoup
import requests
from pprint import pprint

'''
    This class essentially extends the twitter.status object.
    It adds a new class variable speakable_text, that is a version of
    the full_text variable suited for speaking out loud by a TTS engine.
    Goal is to use it in an alarm to read texts to the user.
'''

class Vocalizer:
    # cass variable that gets instantiated during class definition
    # All instances of class variable gets the same segmenter
    # it takes a while (more than 2 seconds) to instantiate a segmenter
    # and all class instances will use the same corpus
    text_processor = TextPreProcessor(
            # omit = []
            normalize=['url', 'email', 'percent', 'money', 'phone', 'user',
                       'time', 'url', 'date', 'number'],
            fix_html=True,  # fix HTML tokens
            fix_text = True,

            # corpus from which the word statistics are going to be used
            # for word segmentation
            segmenter="twitter",

            # corpus from which the word statistics are going to be used
            # for spell correction
            corrector="twitter",

            # select a tokenizer. You can use SocialTokenizer, or pass your own
            # the tokenizer, should take as input a string and return a list of tokens
            # tokenizer=Tokenizer(lowercase=True).tokenize,
            remove_tags = True,
            dicts = [EMOTICONS, UNICODE_EMO, EMOTICONS_EMO, SLANGDICT]
            )
    hashtag_seg = Segmenter(corpus = "twitter")
    headers = requests.utils.default_headers()
    headers.update({ 'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'})

    def __init__(self, Status):
        self._status = Status

        d = vars(Status)
        self.set_class_attrs(d)

        self.text_mod = self._full_text
        self.non_text_info = ""

        # check for Nonetype
        # no need to check for empty list or empty string,
        # that gets done in set_class_attrs
        if self.user_mentions is not None:
            for u in self.user_mentions:
                self.vocalize_mention(u)
        if self.hashtags is not None:
            for h in self.hashtags:
                self.vocalize_hashtag(h)

        # media and urls are handled differently from other entities
        # because they are largely non text based objects
        # thus there is nothing to replace in the full_text.
        # we only need to add a description of the media
        # and delete the URL from the text (if it is in there)
        if self.urls is not None:
            self.vocalize_urls()
        if self.media is not None:
            self.vocalize_medias()

        self.text_mod = self.clean_up_text(self.text_mod)
        self.spoken_tweet = self.format_response()


    # nonStds = re.compile(r'[^a-zA-Z0-9",.;:\'&@!?]')
    # TODO: create spoken replacements for many commonly used characters

    # media input is guaranteed to always be a list of at least one item
    # returns a list of strings corresponding to
    # a pronouncable way to say each media object
    @staticmethod
    def getSingleMediaInfo(m):
        req = requests.get(m.media_url,
                           headers = Vocalizer.headers)
        try:
            soup = BeautifulSoup(req.text, 'html.parser')
        except:
            return [None]
        # the second item in sub-list will be modified
        # based on the results of soup.find()
        tags = [["from", "og:site_name"],
                ["titled", "og:title"],
                ["described as ", "og:description"]]
        i = 0
        # changes value of second item in each sublist
        # of tags to the result from soup.find()
        # if find() returns None, then delete the item from tags
        while i < len(tags):
            tag = tags[i]
            tag[1] = soup.find("meta", property=tag[1])
            if tag[1] is not None:
                tag[1] = tag[1].get('content')
                i += 1
            else:
                del tags[i]
        # example responses
        # "from twitter, titled how I escaped, with this description. I made a boat"
        # "titled how I escaped, with this description. I made a boat"
        # "from twitter"
        # ""
        spoken_part =  ", ".join(" ".join(t) for tag in tags)
        if not spoken_part.startswith("described"):
            spoken_part = spoken_part.replace("described","and is described", 1)

        return [spoken_part if spoken_part else None]

    @staticmethod
    def recurse_thru_media(media):
        # base case
        if media is None or not media:
            return [None]

        res = Vocalizer.getSingleMediaInfo(media[0])
        return res + Vocalizer.recurse_thru_media(media[1:])


    # take all attributes of Status (stored in d) and assign them to
    # this object. Status objects need to Vocalized.
    # Status objects will occur only as a single status object
    # or a list of status objects
    def set_class_attrs(self, d):
        for k,v in d.items():
            # make full_text quasi un-touchable
            # fix_unicode input errors with ftfy
            if k == 'full_text':
                k = '_full_text'
                v = ftfy.fix_text(v)
            # Set all Nones, [], and "" to None
            # so we don't have to check for those types later
            if v is not None and v:
                if isinstance(v,list) and all([isinstance(i,twitter.Status) for i in v]):
                    setattr(self, k, [Vocalizer(i) for i in v])
                else:
                    val = Vocalizer(v) if isinstance(v,twitter.Status) else v
                    setattr(self, k, val)
            else:
                setattr(self, k, None)


    def look_for_punct(self, text):
        text = text.strip()
        match = re.search(r'[.?!]\Z',text)
        if match is None:
            text += ". "
        return text


    def format_response(self):
        self.text_mod = self.text_mod.strip()
        self.text_mod = self.look_for_punct(self.text_mod)
        self.non_text_info = self.look_for_punct(self.non_text_info)

        return self.text_mod+" "+self.non_text_info

    def convert_money(self,text,match=True):
        money = re.compile(r'\$[0-9]{1,3}(\,?[0-9]{3})*(\.[0-9]{0,2})?')
        match = money.search(text)
        while match:
            to_repl = match.group()
            repl_with = to_repl.replace(",","").strip("$")
            repl_with = num2words(repl_with,
                                  to="currency",
                                  currency="USD").replace("-"," ")
            text = text.replace(to_repl,repl_with,1)
            match = money.search(text)

        return text


    def clean_up_text(self, text):
        regexes = Vocalizer.text_processor.regexes

        text = re.sub(r'  +', ' ', text)  # remove repeating spaces
        text = ftfy.fix_text(text)

        sections = text.splitlines()
        sections = [s for s in sections if s]
        result = ""
        for sec in sections:
            sec = regexes["elongated"].sub(
                    lambda w: Vocalizer.text_processor.handle_elongated_match(w),
                    sec)
            sec = regexes["repeat_puncts"].sub(
                    lambda w: Vocalizer.text_processor.handle_repeated_puncts(w),
                    sec)

            sec = regexes["emphasis"].sub(
                    lambda w: Vocalizer.text_processor.handle_emphasis_match(w),
                     sec)

            if "$" in sec:
                sec = convert_money(sec)

            # split(phrase into individual words
            sec = sec.split()
            # convert slang abbreviations to words
            # and emoticons to words
            for d in Vocalizer.text_processor.dicts:
                sec = Vocalizer.text_processor.dict_replace(sec, d)
            sec = " ".join(sec)#.strip()
            sec = re.sub(r"[^a-zA-Z0-9,.?!:;\"\'&]"," ", sec)
            sec = re.sub(r'..+','.',sec)
            sec = re.sub(r'  +',' ',sec).strip()
            match = re.search(r'.?!',sec)
            if match is None: sec += ". "
            result += sec

        return result


    @staticmethod
    def url_name_title(Url):
        url = Url.url
        eurl = Url.expanded_url
        req = requests.get(eurl)
        soup = BeautifulSoup(req.content, 'html.parser')
        site_n = soup.find("meta",property = "og:site_name")
        from_name = "" if site_n is None else ("from "+site_n.get('content'))
        site_t = soup.find("meta",property = "og:title")
        title ="" if site_t is None else ("titled "+site_t.get('content'))
        titled = "unidentified" if not (from_name or title) else title
        return "{} {}. ".format(from_name, titled).strip()

    # turns a url into something more human readable
    def vocalize_urls(self):
        for url in self.urls: # delete all urls from tweet text
            self.text_mod = self.text_mod.replace(url.url,"")

        if len(self.urls) > 1:
            response = "there are {} U R L's in the tweet. ".format(len(self.urls))
            urls_info = [Vocalizer.url_name_title(url) for url in self.urls]
            urls_info = filter(lambda x: x != "unidentified", urls_info)

            if urls_info:
                for i, url_info in enumerate(urls_info):
                    ord = "first" if not i else "next"
                    response += "the {} U R L is {}".format(ord, url_info)
            else:
                response += "there is no information avaiable about any of them. "

        else:
            response = "there is a U R L in the tweet. "
            url_info = Vocalizer.url_name_title(self.urls[0])

            if url_info != "unidentified":
                response += "the U R L is {}".format(url_info)
            else:
                response += "there is no information available about it. "

        # replace last(possibly only) url with response
        self.non_text_info += self.clean_up_text(response)


    def vocalize_mention(self, m):
        looking_for = "@"+m.screen_name.lower()
        # need to use original _full_text string to ensure character position is accurate
        looking_in = self._full_text.lower()
        start = looking_in.find(looking_for)
        if start != -1:
            stop = start + len(looking_for)
            to_replace = self._full_text[start:stop]
            self.text_mod = self.text_mod.replace(to_replace, m.name)
        else:
            print("after lowering all characters, still")
            print("could not find the user_mention {}:\n".format(looking_for))
            print("in:\n" + looking_in)


    # h.text is the text of the hashtag without the # symbol
    def vocalize_hashtag(self, h):
        self.text_mod = self.text_mod.replace("#"+h.text,
                                    "hash tag " +Vocalizer.hashtag_seg.segment(h.text))


    def vocalize_medias(self):
        for m in self.media:
            self.text_mod = self.text_mod.replace(m.url,"")


        # tweets can only contain one type of media
        # set type for all media objects. remove "animated" from "animated_gifs"
        type = self.media[0].type.replace("animated_","")
        media_info = Vocalizer.recurse_thru_media(self.media)
        media_info = [m for m in media_info if m is not None]
        n_missing_info = len(self.media) - len(media_info)

        if len(self.media) > 1:
            response = " There are {} {}s in the tweet. ".format(len(self.media), type)
            artcl = "one"
        else:
            response = " There is a {} in the tweet. ".format(type)
            artcl = "the"

        if media_info:
            response += "{} {} is ".format(artcl, type)
            for i,m in enumerate(media_info):
                ord = "" if not i else ", another {} is ".format(type)
                response += ord + m
            response +=". "
            if n_missing_info:
                response += "I don't have information about the last {}. ".format(n_missing_info)
        else:
            plural = "s" if len(self.media) > 1 else ""
            response += "There is no information about the {}{}. ".format(type,plural)

        self.non_text_info += response
