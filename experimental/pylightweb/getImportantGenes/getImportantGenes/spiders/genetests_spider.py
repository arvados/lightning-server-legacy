import os
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors import LinkExtractor
import re

from getImportantGenes.items import GetImportantGenesItem

class genetestsSpider(CrawlSpider):
    name = 'genetests'
    allowed_domains = ['genetests.org']
    start_urls = ['http://www.genetests.org/genes/']
    def parse(self, response):
        geneURLs = response.xpath("//a/@href").re(r'/genes/\?gene=[\w]*')
        genes = response.xpath("//a/@href").re(r'(?<=/genes/\?gene=)[\w]*')
        for gene, partialURL in zip(genes, geneURLs):
            data = GetImportantGenesItem()
            data['geneName'] = gene
            data['url'] = 'http://www.genetests.org' + partialURL
            yield data

