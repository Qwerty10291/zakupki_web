import requests
from lxml.html import document_fromstring
import re
import multiprocessing as mp
import time
import json
import sqlalchemy
from data.models import Data, Winners, Objects
from datetime import datetime


class Parser:
    def __init__(self, tags: dict, processes=2, timeout=0.1):

        # устанавливаем канал связи с главным процессом
        self.pipe = mp.Pipe()



        # задаем константы
        self.processes = processes
        self.parse_link = 'https://zakupki.gov.ru/epz/order/extendedsearch/results.html'
        self.main_link = 'https://zakupki.gov.ru'
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:81.0) Gecko/20100101 Firefox/81.0', }

        # создаем теги для запроса
        self.tags = tags
        self.tags['pageNumber'] = '1'
        self.tags['morphology'] = 'on'
        self.tags['recordsPerPage'] = '_50'
        self.tags['fz44'] = 'on'
        self.tags['pc'] = 'on'

    def init_parser(self):
        self.session.get('https://zakupki.gov.ru/')
        self.pipe[1].send('парсер инициализирован')

    def start_async(self):
        process = mp.Process(target=self.async_parser,)
        process.start()
        self.process = process
        return process

    def async_parser(self):
        conn_str = 'postgresql+psycopg2://zakupki:qwerty1029@127.0.0.1/zakupki'
        engine = sqlalchemy.create_engine(conn_str, echo=False)
        self.session_maker = sqlalchemy.orm.sessionmaker(bind=engine)
        self.init_parser()
        links = self.get_links_to_parse()
        self.parse_all(links)

    def get_links_to_parse(self) -> list:
        tags = self.tags
        data = self.session.get(
            'https://zakupki.gov.ru/epz/order/extendedsearch/results.html', params=tags)
        data.raise_for_status()

        links = []
        # получаем количество страниц
        page_num = int(document_fromstring(data.text).xpath(
            '//ul[@class="pages"]/li[last()]/a/span/text()')[0])
        for i in range(1, 2):
            tags['pageNumber'] = str(i)
            page_data = self.session.get(self.parse_link, params=tags)
            page_data.raise_for_status()
            links += list(map(lambda x: [self.main_link + x.xpath('./@href')[0], self._tender_id_handler(x.xpath('./text()')[0])],
                              document_fromstring(page_data.text).xpath('//div[@class="registry-entry__header-mid__number"]/a')))
            self.pipe[1].send(f'Страница: {i}')
        return links

    def parse_all(self, links):
        for link in links:
            if not self.db_checker(link[1]):
                info = self.parse_ea44(link[0])
                data = self.db_handler(link[1], info)
                self.pipe[1].send(data)
            else:
                self.pipe[1].send(self.db_getter(link[1]))
            time.sleep(self.timeout)
        self.pipe[1].send('end')
    
    def db_checker(self, tender_id):
        session = self.session_maker()
        data = session.query(Data).filter(Data.id == tender_id).count()
        session.close()
        return data
    
    def db_handler(self, id, data):
        session = self.session_maker()
        db_data = Data()
        db_data.id = id
        db_data.tender_price = self._tender_price_handler(data['tender_price'])
        db_data.type = data['type']
        db_data.tender_date = self._tender_date_handler(data['tender_date'])
        db_data.tender_object = data['tender_object']
        db_data.customer = data['customer']
        db_data.tender_adress = data['tender_adress']
        db_data.tender_delivery = data['tender_delivery']
        db_data.tender_terms = data['tender_term']
        db_data.document_links = '\n'.join(data['document_links'])
        db_data.tender_link = data['link']

        winner = Winners()
        winner.data_id = id
        winner.name = data['tender_winner'][0]
        winner.position = data['tender_winner'][1]
        winner.price = data['tender_winner'][2]
        db_data.winner.append(winner)

        for i in data['tender_object_info'][1:]:
            if len(i) == 6:
                data = Objects()
                data.position = i[0]
                data.name = i[1]
                data.unit = i[2]
                data.quantity = i[3]
                data.unit_price = i[4]
                data.price = i[5]
                db_data.objects.append(data)
        
        session.add(db_data)
        session.commit()
        db_data.winner = [winner]
        session.close()
        return db_data

    def db_getter(self, id) -> Data:
        session = self.session_maker()
        data = session.query(Data).get(id)
        winner = data.winner[0]
        data.winner = [winner]
        session.close()
        return data

    def parse_ea44(self, link):
        inform_request = self.session.get(link)
        inform_request.raise_for_status()

        order_document = document_fromstring(inform_request.text)

        # парсим главную информацию о закупке - номер цена заказчик дата
        card_info_container = order_document.cssselect('.cardMainInfo')[0]
        tender_id = card_info_container.cssselect(
            '.cardMainInfo__purchaseLink')

        if not tender_id:
            tender_id = ''
        else:
            tender_id = self._normalizer(tender_id[0].text_content())

        tender_object = card_info_container.xpath(
            './div[1]/div[2]/div[1]/span[2]')
        if not tender_object:
            tender_object = ''
        else:
            tender_object = self._normalizer(tender_object[0].text_content())

        customer = card_info_container.xpath('./div[1]/div[2]/div[2]/span[2]')
        if not customer:
            customer = ''
        else:
            customer = self._normalizer(customer[0].text_content())

        tender_price = card_info_container.cssselect('.cost')
        if not tender_price:
            tender_price = ''
        else:
            tender_price = self._normalizer(tender_price[0].text_content())

        tender_date = card_info_container.xpath(
            './div[2]/div[2]/div[1]/div[1]/span[2]')
        if not tender_date:
            tender_date = ''
        else:
            tender_date = self._normalizer(tender_date[0].text_content())

        # общая информация о закупке - адресс электронной площадки и обьект закупки
        general_information_container = order_document.xpath(
            '//div[@class="wrapper"]/div[2]')
        
        tender_adress = general_information_container[0].xpath(
            './/div[@class="col"]/section[3]/span[2]')
        if not tender_adress:
            tender_adress = ''
        else:
            tender_adress = self._normalizer(tender_adress[0].text_content())

        # условия контракта
        condition_container = self._get_cotract_conditions_container(
            order_document.xpath('//div[@id="custReqNoticeTable"]/div'))
        if condition_container is not None:
            tender_delivery_adress = condition_container.xpath(
                './/div[@class="col"]/section[2]/span[2]')
            if not tender_delivery_adress:
                tender_delivery_adress = ''
            else:
                tender_delivery_adress = self._normalizer(
                    tender_delivery_adress[0].text_content())

            tender_term = condition_container.xpath(
                './/div[@class="row"]/section[3]/span[2]')
            if not tender_term:
                tender_term = ''
            else:
                tender_term = self._normalizer(tender_term[0].text_content())
        else:
            tender_delivery_adress = ''
            tender_term = ''

        # парсинг информации о обьекте закупки
        tender_object_info = self._parse_tender_object_info(order_document)

        # парсинг победителя
        winner = self._parse_tender_winner(link)
        if len(winner) < 3:
            winner = ['', '', '']

        # парсинг ссылок документов
        term_document_link = link.replace('common-info', 'documents')
        term_document_data = self.session.get(term_document_link)
        term_document_data.raise_for_status()
        term_document_links = document_fromstring(term_document_data.text).xpath(
            '//span[@class="section__value"]/a[@title]/@href')

        return {
            'tender_id': tender_id, 'tender_object': tender_object, 'customer': customer,
            'tender_price': tender_price, 'tender_date': tender_date, 'tender_adress': tender_adress,
            'tender_delivery': tender_delivery_adress, 'tender_term': tender_term,
            'tender_object_info': tender_object_info, 'document_links': term_document_links,
            'tender_winner': winner, 'type': 'fz44', 'link': link
        }

    def _parse_tender_object_info(self, document):
        # получаем контейнер таблицы
        table = document.xpath(
            '//div[@id="positionKTRU"]//table')
        if not table:
            return []
        else:
            table = table[0]

        # получаем и обрабатываем заголовки
        headers_raw = table.xpath('./thead/tr[1]/th/text()')
        headers = list(map(self._normalizer, headers_raw))

        # данные таблицы
        data_raw = [row.xpath('./td[contains(@class, "tableBlock__col")]/text()')
                    for row in table.xpath('./tbody/tr')]
        data = [list(map(self._normalizer, i)) for i in data_raw]

        return [headers] + data

    def _get_cotract_conditions_container(self, containers):
        for element in containers:
            name = element.xpath('.//h2')[0].text_content()
            if 'Условия' in self._normalizer(name):
                return element
        return None

    def _parse_tender_winner(self, tender_link):
        winner_link = tender_link.replace('common-info', 'supplier-results')
        data = self.session.get(winner_link)
        data.raise_for_status()

        doc = document_fromstring(data.text)
        table = doc.xpath('//div[contains(@id, "participant")]/table')
        if table:
            winner = table[0].xpath('./tbody/tr[1]/td/text()')
        else:
            return ['', '', '']
        return list(map(self._normalizer, winner))

    def _normalizer(self, text: str) -> str:
        return text.replace('\n', '').replace('\xa0', '').strip()

    def _tender_id_handler(self, tender_id: str) -> int:
        return int(re.findall(r'\d+', tender_id)[0])
    
    def _tender_price_handler(self, tender_price: str) -> float:
        tender_price = tender_price.replace(' ', '').replace(',', '.')
        return float(re.findall(r'[\d\,]+', tender_price)[0])
    
    def _tender_date_handler(self, tender_date: str):
        return datetime.strptime(tender_date, '%d.%m.%Y')
