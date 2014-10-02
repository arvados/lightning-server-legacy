import os
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors import LinkExtractor

from pgpScrape.items import MetaDataItem

begstr = 'https://my.pgp-hms.org/profile/'
urls = []
for f in os.listdir("/home/sguthrie/abv"):
    if ".abv" in f:
        urls.append(begstr + f.split('.')[0])

def getFirstTime(times):
    if len(times) == 0:
        return ''
    else:
        return times[0]

class PGPSpider(CrawlSpider):
    name = 'pgp2'
    allowed_domains = ['pgp-hms.org']
    start_urls = urls
    def parse(self, response):
        data = MetaDataItem()
        data['name'] = response.url.split("/")[-1]
        bloodtext = ''
        salivatext = ''
        for text in response.xpath("//div[@class='profile-data']/table/tbody/tr/th/a/text()").extract():
            if 'saliva' in str(text).lower():
                salivatext += str(text) + "; "
            if 'blood' in str(text).lower():
                bloodtext += str(text) + "; "
        data['blood'] = bloodtext
        times = response.xpath("//div[@class='profile-data']/table/tbody/tr/td/text()").re(r'(?<=[Bb]lood\)[\s]{4}received[\s]{4})[ \w\-:]*')
        times.extend(response.xpath("//div[@class='profile-data']/table/tbody/tr/td/text()").re(r'(?<=[Bb]lood\)[\s]{4}mailed[\s]{4})[ \w\-:]*'))
        data['bloodtime'] = getFirstTime(times)
        data['saliva'] = salivatext
        times = response.xpath("//div[@class='profile-data']/table/tbody/tr/td/text()").re(r'(?<=[Ss]aliva\)[\s]{4}received[\s]{4})[ \w\-:]*')
        times.extend(response.xpath("//div[@class='profile-data']/table/tbody/tr/td/text()").re(r'(?<=[Ss]aliva\)[\s]{4}mailed[\s]{4})[ \w\-:]*'))
        data['salivatime'] = getFirstTime(times)

        #data['genomebuild'] = response.xpath("//div[@class='profile-data']/table/tr/td[@data-summarize-as='none']/text()").re('(?<=\\u2022\\xa0).+')
        return data
