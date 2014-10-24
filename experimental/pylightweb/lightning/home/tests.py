from django.test import TestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.urlresolvers import reverse
from selenium.webdriver.firefox.webdriver import WebDriver

class TestViewBreadcrumbs(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        cls.selenium = WebDriver()
        super(TestViewBreadcrumbs, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(TestViewBreadcrumbs, cls).tearDownClass()

    def test_home_breadcrumbs(self):
        self.selenium.get('%s' % (self.live_server_url))
        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
        self.assertEqual(len(elements), 1)
        for element in elements:
            self.assertEqual(element.is_displayed(), True)
            if element.text == 'Home':
                self.assertEqual('active' in element.get_attribute('class'), True)
                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s#' % (self.selenium.current_url))
                
    def test_help_breadcrumbs(self):
        self.selenium.get('%s%s' % (self.live_server_url, reverse('home:help')))
        elements = self.selenium.find_element_by_class_name("breadcrumb").find_elements_by_tag_name('li')
        self.assertEqual(len(elements), 2)
        for element in elements:
            self.assertEqual(element.is_displayed(), True)
            if element.text == 'Home':
                self.assertEqual('active' in element.get_attribute('class'), False)
                self.assertEqual(element.find_element_by_link_text('Home').get_attribute('href'), '%s/' % (self.live_server_url))
                
            elif element.text == 'Help':
                self.assertEqual('active' in element.get_attribute('class'), True)
                self.assertEqual(element.find_element_by_link_text('Help').get_attribute('href'), '%s#' % (self.selenium.current_url))



class TestViewBase(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        cls.selenium = WebDriver()
        super(TestViewBase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(TestViewBase, cls).tearDownClass()
        
    def test_base_navbar_home(self):
        self.selenium.get('%s' % (self.live_server_url))
        element = self.selenium.find_element_by_class_name("navbar").find_element_by_link_text('Home')
        self.assertEqual(element.is_displayed(), True)
        self.assertEqual(element.get_attribute('href'), '%s' % (self.selenium.current_url))
    def test_base_navbar_population_toggle(self):
        self.selenium.get('%s' % (self.live_server_url))
        element = self.selenium.find_element_by_class_name("navbar").find_element_by_partial_link_text('Population')
        self.assertEqual(element.is_displayed(), True)
        self.assertEqual(element.get_attribute('href'), '%s#' % (self.selenium.current_url))
    def test_base_navbar_map(self):
        self.selenium.get('%s' % (self.live_server_url))
        element = self.selenium.find_element_by_class_name("navbar").find_element_by_partial_link_text('Population')
        element.click()
        element = self.selenium.find_element_by_class_name("navbar").find_element_by_link_text('Genome Map')
        self.assertEqual(element.is_displayed(), True)
        self.assertEqual(element.get_attribute('href'), '%s%s' % (self.live_server_url, reverse('slippy:slippymap')))
    def test_base_navbar_library(self):
        self.selenium.get('%s' % (self.live_server_url))
        element = self.selenium.find_element_by_class_name("navbar").find_element_by_partial_link_text('Population')
        element.click()
        element = self.selenium.find_element_by_class_name("navbar").find_element_by_link_text('Tile Library Statistics')
        self.assertEqual(element.is_displayed(), True)
        self.assertEqual(element.get_attribute('href'), '%s%s' % (self.live_server_url, reverse('tile_library:statistics')))
    def test_base_navbar_humans(self):
        self.selenium.get('%s' % (self.live_server_url))
        element = self.selenium.find_element_by_class_name("navbar").find_element_by_link_text('Individuals')
        self.assertEqual(element.is_displayed(), True)
        self.assertEqual(element.get_attribute('href'), '%s%s' % (self.live_server_url, reverse('humans:individuals')))
    def test_base_navbar_genes(self):
        self.selenium.get('%s' % (self.live_server_url))
        element = self.selenium.find_element_by_class_name("navbar").find_element_by_link_text('Known Genes')
        self.assertEqual(element.is_displayed(), True)
        self.assertEqual(element.get_attribute('href'), '%s%s' % (self.live_server_url, reverse('genes:names')))
    def test_base_navbar_beacon(self):
        self.selenium.get('%s' % (self.live_server_url))
        element = self.selenium.find_element_by_class_name("navbar").find_element_by_link_text('Beacon')
        self.assertEqual(element.is_displayed(), True)
        self.assertEqual(element.get_attribute('href'), 'http://lightning-dev4.curoverse.com/beacon')
    def test_base_navbar_help(self):
        self.selenium.get('%s' % (self.live_server_url))
        element = self.selenium.find_element_by_class_name("navbar").find_element_by_link_text('Help')
        self.assertEqual(element.is_displayed(), True)
        self.assertEqual(element.get_attribute('href'), '%s%s' % (self.live_server_url, reverse('home:help')))
    def test_base_footer(self):
        self.selenium.get('%s' % (self.live_server_url))
        element = self.selenium.find_element_by_class_name("footer")
        self.assertEqual(element.is_displayed(), True)
        self.assertEqual(element.find_element_by_link_text('arvados.org').get_attribute('href'), 'http://www.arvados.org/')
        self.assertEqual(element.find_element_by_link_text('join').get_attribute('href'), 'https://arvados.org/projects/arvados/wiki/IRC_and_Mailing_lists')

        
