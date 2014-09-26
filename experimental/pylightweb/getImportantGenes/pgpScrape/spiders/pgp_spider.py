import os
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors import LinkExtractor

from pgpScrape.items import PersonalDataItem

begstr = 'https://my.pgp-hms.org/profile/'
urls = []
for f in os.listdir("/home/sguthrie/abv"):
    if ".abv" in f:
        urls.append(begstr + f.split('.')[0])

class PGPSpider(CrawlSpider):
    name = 'pgp'
    allowed_domains = ['pgp-hms.org']
    start_urls = urls
    def parse(self, response):
        person = PersonalDataItem()
        person['name'] = response.url.split("/")[-1]
        person['birthdate'] = response.xpath("//table[@class='demographics']/tr[th='Date of Birth']/td/text()").extract()
        person['sex'] = response.xpath("//table[@class='demographics']/tr[th='Gender']/td/text()").extract()
        person['weight'] = response.xpath("//table[@class='demographics']/tr[th='Weight']/td/text()").extract()
        person['height'] = response.xpath("//table[@class='demographics']/tr[th='Height']/td/text()").extract()
        person['bloodtype'] = response.xpath("//table[@class='demographics']/tr[th='Blood Type']/td/text()").extract()
        person['ethnicity'] = response.xpath("//table[@class='demographics']/tr[th='Race']/td/text()").extract()
        return person
