#%%
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import time
from datetime import datetime
#%%

def select_initial_options(year, make_model, part, zip_code):
    """ After initial load, select year, make & model, part, zip code
    """
    # select options
    select = Select(driver.find_element_by_name('userDate'))
    select.select_by_visible_text(year)
    select = Select(driver.find_element_by_name('userModel'))
    select.select_by_visible_text(make_model)
    select = Select(driver.find_element_by_name('userPart'))
    select.select_by_visible_text(part)
    driver.find_element_by_name('userZip').send_keys(zip_code)

    # click Search
    driver.find_element_by_name('Search Car Part Inventory').click()


def select_trim(trim):
    """ After first Search button, select a trim
    """

    # find radio buttons and their labels
    radio_buttons = driver.find_elements_by_name('dummyVar')
    radio_labels = driver.find_elements_by_tag_name('label')

    # find radio button matching trim
    count = 0
    for label in radio_labels:
        if label.text == trim:
            break
        count += 1
    
    # click radio button, click Search button
    radio_buttons[count].click()
    driver.find_element_by_name('Search Car Part Inventory').click()


def parse_html():
    """ Parse current page html using BeautifulSoup
    """
    page_html = driver.page_source
    html_source = BeautifulSoup(page_html, "html.parser")
    return html_source


def write_html(html_source, d):
    """ Write parsed html to text file in script directory
    """
    import io
    with io.open(str(d) + '\\html.txt', 'w', encoding='utf-8') as txtfile:
        txtfile.write(str(html_source))


def find_pages(html_source):
    """ Find number of pages to scrape
    """
    results = html_source.findAll('tbody')
    
    # table of pages contained in 6th table tag
    tag_num = len(results) - 3
    tbl = results[tag_num]
    
    # get all child td tags which contain page text
    page_tags = tbl.findAll('td')
    last_page = len(page_tags)

    # generate list of urls
    page_urls = []
    for p in page_tags:
        try:
            url = p.find('a')['href']
            page_urls.append(url)
        except:
            pass
    page_urls = ['https://www.car-part.com' + url for url in page_urls]

    return last_page, page_urls


def results_html():
    """ Isolate html to tr tags containing individual listing info
    """
    # get html of current page
    html_source = parse_html()

    # table of pages contained in 5th table tag
    results = html_source.findAll('tbody')
    results = results[4]
    html_result = results.findAll('tr')

    # first and last tr tag in html_result are not individual listings
    last = len(html_result)
    html_result = html_result[1:last-1]

    return html_result


def scrape_results(html_result):
    """ Scrape a page of results and store in list of dicts
    """
    rows_list = []
    last = len(html_result)
    
    # iterate through each result in html
    for i in np.arange(0,last):
        html_ind = html_result[i]
        tags = html_ind.findAll('td')
        
        #  year, part, make/model
        pmm_list = []
        for br in tags[0].findAll('br'):
            next_s = br.nextSibling
            text = str(next_s).strip()
            pmm_list.append(text)
        try:
            year = tags[0].text[:4]
        except:
            year = ''
        try:
            part = pmm_list[0]
        except:
            part = ''
        try:
            mm = pmm_list[1]
        except:
            mm = ''

        # image url, description
        img_tag = tags[1].findChild('img')
        try:
            img_url = img_tag['src']
        except:
            img_url = ''
        try:
            desc = tags[1].text
        except:
            desc = ''

        # part grade, stock no, price
        try:
            p_grade = tags[2].text
        except:
            p_grade = ''
        try:
            stock_no = tags[3].text
        except:
            stock_no = ''
        try:
            price = tags[4].text
        except:
            price = ''

        # dealer
        a_tags = tags[5].findAll('a')
        try:
            dealer_url = a_tags[0]['href']
        except:
            dealer_url = ''
        try:
            dealer_name = a_tags[0].text
        except:
            dealer_name = ''
        
        # location
        all_text = tags[5].text
        pos1 = len(dealer_name)
        pos2 = all_text[pos1+1:].find(' ')
        pos2 = pos1 + pos2
        loc = all_text[pos1+1:pos2]

        # phone, request quote, request ins quote, email
        try:
            if 'Request_Quote' and 'Request_Insurance_Quote' in all_text:
                req_quote_url = a_tags[1]['href']
                req_ins_quote_url = a_tags[2]['href']
                pos1 = all_text.find('Request_Quote')
                pos2 = all_text.find('Request_Insurance_Quote')
                phone = all_text[pos1+14:pos2-1].strip()
                email = ''
            elif 'Request_Quote' in all_text and 'Request_Insurance_Qyote' not in all_text:
                req_quote_url = a_tags[1]['href']
                req_ins_quote_url = ''
                pos1 = all_text.find('Request_Quote')
                phone = all_text[pos1+14:].strip()
                email = ''
            elif 'E-mail' in all_text:
                email = a_tags[1]['href']
                req_quote_url = ''
                req_ins_quote_url = ''
                phone = ''
        except:
            req_quote_url = ''
            req_ins_quote_url = ''
            phone = ''
            email = ''
        
        # distance
        try:
            dist = tags[6].text
        except:
            dist = ''

        # create dict from data and add to rows_list
        dict_row = {
            'year':year, 'part':part, 'make_model': mm, 'img_url':img_url,
            'description':desc, 'part_grade':p_grade, 'stock_no':stock_no,
            'price':price, 'dealer_name':dealer_name, 'dealer_url':dealer_url,
            'location':loc, 'req_quote_url': req_quote_url,
            'req_ins_quote_url':req_ins_quote_url, 'phone':phone, 'email':email
        }

        rows_list.append(dict_row)
    
    return rows_list

def df_to_excel(rows_list, year, make_model):
    df = pd.DataFrame(rows_list)
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    f = f'{timestamp} {year} {make_model}.xlsx'
    df.to_excel(f, index=False)


# car make, model, year, part, location
year = '2015'
make_model = 'Honda Accord'
part = 'A/C Heater Control (see also Radio or TV Screen)'
zip_code = '90005'
trim = 'automatic temperature control, heated mirrors, EX'

# open url
url = 'https://www.car-part.com/'
d = Path(__file__).resolve().parent
driver_path = d / 'chromedriver.exe'
driver = webdriver.Chrome(executable_path=str(driver_path))
driver.get(url)

# navigate to first results page
time.sleep(1)
select_initial_options(year, make_model, part, zip_code)
time.sleep(1)
select_trim(trim)

# find number of pages
time.sleep(1)
html_source = parse_html()
last_page, page_urls = find_pages(html_source)

# iterate through pages and scrape
rows_list = []
pg_count = 0
for p in np.arange(1, last_page):
    if p > 1:
        url = page_urls[pg_count]
        driver.get(url)
        pg_count += 1
    # get html, scrape, save results to rows_list
    time.sleep(2)
    html_result = results_html()
    time.sleep(1)
    rows_list.extend(scrape_results(html_result))

# make df and export to excel
df_to_excel(rows_list, year, make_model)
