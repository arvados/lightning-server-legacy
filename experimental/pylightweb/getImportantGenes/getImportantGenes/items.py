# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class GetImportantGenesItem(scrapy.Item):
    # define the fields for your item here like:
    geneName = scrapy.Field()
    url = scrapy.Field()
    
    
