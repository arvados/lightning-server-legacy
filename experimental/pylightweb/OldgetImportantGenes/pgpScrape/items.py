# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy

class PersonalDataItem(scrapy.Item):
    name = scrapy.Field()
    birthdate = scrapy.Field()
    sex = scrapy.Field()
    weight = scrapy.Field()
    height = scrapy.Field()
    bloodtype = scrapy.Field()
    ethnicity = scrapy.Field()

class MetaDataItem(scrapy.Item):
    name = scrapy.Field()
    blood = scrapy.Field()
    bloodtime = scrapy.Field()
    saliva = scrapy.Field()
    salivatime = scrapy.Field()
