import webapp2

import sys
import string
from httplib import HTTPSConnection
import urllib
from urllib import urlencode
from datetime import datetime
import exceptions
import json

# TODO put your real API key here
api_key = '1234567890abcdef1234567890abcdef'
# put a real perma_token here, or rewrite the session with oauth to get a real
# token for a day or month at a time, authenticate/authorize the app to Trello, etc.
perma_token = '1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'


class ResourceUnavailable(Exception):
    """Exception representing a failed request to a resource"""

    def __init__(self, msg, http_response):
        Exception.__init__(self)
        self._msg = msg
        self._status = http_response.status

    def __str__(self):
        return "Resource unavailable: %s (HTTP status: %s)" % (self._msg, self._status)


class Unauthorized(ResourceUnavailable):
    pass


class TrelloClient(object):
    """ Base class for Trello API access """

    def list_boards(self):
        """
        Returns all boards for your Trello session
        Trello doesn't natively support this, so I do a horrible, horrible thing and loop
        through a massive group of searches.

        :return: a list of Python objects representing the Trello boards. Each board has the
        following noteworthy attributes:
            - id: the board's identifier
            - name: Name of the board
        """
        boards = []
        letters = string.ascii_lowercase + string.digits
        for letter in list(letters):
            json_obj = fetch_json('/search/', query_params={'modelTypes': 'boards', 'query': letter, 'partial': 'true'})
            if 'boards' in json_obj and len(json_obj['boards']):
                for board_obj in json_obj['boards']:
                    tmp_board = json.dumps({
                        'id': board_obj['id'],
                        # force lowercase and strip spaces and dashes
                        'name': board_obj['name'].lower().replace(' ', '').replace('-', '')
                        })
                    if tmp_board not in boards:
                        boards.append(tmp_board)
        return boards

    def get_board(self, board_id):
        """ fetch a board object based on id """
        obj = fetch_json('/boards/' + board_id)
        return Board(board_id=board_id, name=obj['name'])
        # return obj  # self._board_from_json(obj)

    def get_list(self, list_id):
        """ fetch a list object based on id """
        obj = fetch_json('/lists/' + list_id)
        my_list = List(self.get_board(obj['idBoard']), obj['id'], name=obj['name'].encode('utf-8'))
        my_list.closed = obj['closed']
        return my_list

    def get_member(self, member_id):
        """ get a user/member object based on id """
        return Member(self, member_id).fetch()

    # def _board_from_json(self, incoming_json):
    #     """ fetch a Board object based on a json-returned id """
    #     board =
    #     print '<hr>board from json: '
    #     print board
    #     print '<hr>'
    #     return board


class Board(object):
    """Class representing a Trello board. Board attributes are stored as normal Python attributes;
    access to all sub-objects, however, is always an API call (Lists, Cards).
    """

    def __init__(self, board_id, name=''):
        """Constructor.

        :client: Reference to a Trello object
        :board_id: ID for the board
        :name: refers to a filter, if you want to do a search
        """
        self.id = board_id
        self.name = name
        self.description = None
        self.closed = None
        self.url = None

    def __repr__(self):
        return '<Board %s %s>' % (self.name, self.id)

    def fetch(self):
        """Fetch all attributes for this board"""
        json_obj = fetch_json('/boards/' + self.id)
        self.name = json_obj['name'].encode('utf-8')
        self.description = json_obj.get('desc', '').encode('utf-8')
        self.closed = json_obj['closed']
        self.url = json_obj['url']

    def save(self):
        """ may not need this """
        pass

    def all_lists(self):
        """Returns all lists on this board"""
        return self.get_lists('all')

    def open_lists(self):
        """Returns all open lists on this board"""
        return self.get_lists('open')

    def closed_lists(self):
        """Returns all closed lists on this board"""
        return self.get_lists('closed')

    def get_lists(self, list_filter):
        """ get a list of List objects from the board """
        # error checking
        json_lists = fetch_json(
            '/boards/' + self.id + '/lists',
            query_params={'cards': 'none', 'filter': list_filter})

        lists = []
        for obj in json_lists:
            tmp_list = List(self, obj['id'], name=obj['name'].encode('utf-8'))
            tmp_list.closed = obj['closed']
            lists.append(tmp_list)
        return lists

    def add_list(self, name):
        """Add a card to this list

        :name: name for the card
        :return: the card
        """
        obj = fetch_json(
            '/lists',
            http_method='POST',
            post_args={'name': name, 'idBoard': self.id},)
        my_list = List(self, obj['id'], name=obj['name'].encode('utf-8'))
        my_list.closed = obj['closed']
        return my_list

    def all_cards(self):
        """Returns all cards on this board"""
        return self.get_cards('all')

    def open_cards(self):
        """Returns all open cards on this board"""
        return self.get_cards('open')

    def closed_cards(self):
        """Returns all closed cards on this board"""
        return self.get_cards('closed')

    def get_cards(self, card_filter):
        """ get a list of cards for this Board (Card objects will include their list_id) """
        # error checking
        json_obj = fetch_json(
            '/boards/' + self.id + '/cards',
            query_params={'filter': card_filter})
        cards = list()
        for obj in json_obj:
            card = Card(self, obj['id'], name=obj['name'].encode('utf-8'))
            card.closed = obj['closed']
            card.member_ids = obj['idMembers']
            cards.append(card)

        return cards


class List(object):
    """Class representing a Trello list. List attributes are stored on the object, but access to
    sub-objects (Cards) require an API call"""

    def __init__(self, board, list_id, name=''):
        """Constructor

        :board: reference to the parent board
        :list_id: ID for this list
        """
        self.board = board
        self.id = list_id
        self.name = name
        self.closed = None

    def __repr__(self):
        return '<List %s>' % self.name

    def fetch(self):
        """Fetch all attributes for this list"""
        json_obj = fetch_json('/lists/' + self.id)
        self.name = json_obj['name'].encode('utf-8')
        self.closed = json_obj['closed']

    def list_cards(self):
        """ fetch a list of Card objects for all cards in this list """
        json_obj = fetch_json('/lists/' + self.id + '/cards')
        cards = list()
        for tmp_card in json_obj:
            card = Card(self, tmp_card['id'], name=tmp_card['name'].encode('utf-8'))
            card.description = tmp_card.get('desc', '').encode('utf-8')
            card.closed = tmp_card['closed']
            card.url = tmp_card['url']
            card.member_ids = tmp_card['idMembers']
            cards.append(card)
        return cards

    def add_card(self, name, desc=None):
        """Add a card to this list

        :name: name for the card
        :return: the card
        """
        json_obj = fetch_json(
            '/lists/' + self.id + '/cards',
            http_method='POST',
            post_args={'name': name, 'idList': self.id, 'desc': desc},)
        card = Card(self, json_obj['id'])
        card.name = json_obj['name']
        card.description = json_obj.get('desc', '')
        card.closed = json_obj['closed']
        card.url = json_obj['url']
        card.member_ids = json_obj['idMembers']
        return card


class Card(object):
    """
    Class representing a Trello card. Card attributes are stored on
    the object
    """

    def __init__(self, trello_list, card_id, name=''):
        """Constructor

        :trello_list: reference to the parent list
        :card_id: ID for this card
        """
        self.trello_list = trello_list
        self.id = card_id
        self.name = name
        self.url = None
        self.member_ids = []
        self.short_id = None
        self.list_id = None
        self.board_id = None
        self.labels = []
        self.badges = []
        self.actions = None
        self.description = None
        self.closed = None

    def __repr__(self):
        return '<Card %s>' % self.name

    def fetch(self):
        """Fetch all attributes for this card"""
        json_obj = fetch_json(
            '/cards/' + self.id,
            query_params={'badges': False})
        self.name = json_obj['name'].encode('utf-8')
        self.description = json_obj.get('desc', '')
        self.closed = json_obj['closed']
        self.url = json_obj['url']
        self.member_ids = json_obj['idMembers']
        self.short_id = json_obj['idShort']
        self.list_id = json_obj['idList']
        self.board_id = json_obj['idBoard']
        self.labels = json_obj['labels']
        self.badges = json_obj['badges']

    def fetch_actions(self, action_filter='createCard'):
        """
        Fetch actions for this card can give more argv to action_filter,
        split for ',' json_obj is list
        """
        json_obj = fetch_json(
            '/cards/' + self.id + '/actions',
            query_params={'filter': action_filter})
        self.actions = json_obj

    @property
    def create_date(self):
        """ create a date for your card attributes """
        self.fetch_actions()
        date_str = self.actions[0]['date'][:-5]
        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')

    def set_description(self, description):
        """ set description of the Card """
        self._set_remote_attribute('desc', description)
        self.description = description

    def set_closed(self, closed):
        """ set this card as closed """
        self._set_remote_attribute('closed', closed)
        self.closed = closed

    def delete(self):
        """ Delete this card permanently """
        fetch_json(
            '/cards/' + self.id,
            http_method='DELETE',)

    def assign(self, member_id):
        """ assign this card to one Member """
        # TODO: modify to send a list of Members
        fetch_json(
            '/cards/' + self.id + '/members',
            http_method='POST',
            post_args={'value': member_id, })

    def _set_remote_attribute(self, attribute, value):
        """ touch this Card at Trello to update some attribute """
        fetch_json(
            '/cards/' + self.id + '/' + attribute,
            http_method='PUT',
            post_args={'value': value, },)


class Member(object):
    """
    Class representing a Trello member.
    """

    def __init__(self, client, member_id):
        """ build a new Member object """
        self.id = member_id
        self.status = None
        self.bio = None
        self.url = None
        self.username = None
        self.full_name = None
        self.initials = None

    def __repr__(self):
        return '<Member %s>' % self.id

    def fetch(self):
        """Fetch all attributes for this card"""
        json_obj = fetch_json(
            '/members/' + self.id,
            query_params={'badges': False})
        self.status = json_obj['status'].encode('utf-8')
        self.bio = json_obj.get('bio', '')
        self.url = json_obj.get('url', '')
        self.username = json_obj['username'].encode('utf-8')
        self.full_name = json_obj['fullName'].encode('utf-8')
        self.initials = json_obj['initials'].encode('utf-8')
        return self


class MainPage(webapp2.RequestHandler):
    """ foo """

    # def get(self):
    #     """ answer a GET request with a simple form """
    #     # TODO: add a basic_auth or something so the spammers don't find you
    #     self.response.out.write("""
    #       <html>
    #         <body>
    #           <form action="/postit" method="post">
    #             <div><input type="test" name="to" value="default-icebox@address.com"></div>
    #             <div><input type="test" name="from" value="ian.douglas@iandouglas.com"></div>
    #             <div><input type="test" name="subject" value="my subject"></div>
    #             <div><textarea name="text" rows="3" cols="60">here's my big idea</textarea></div>
    #             <div><input type="submit" value="write data to Trello"></div>
    #           </form>
    #         </body>
    #       </html>""")

    def post(self):
        """ handle a post of data """

        # write an 'OK' status so SendGrid gets a 200 status
        # ideally, you'd just return a 200 status regardless
        self.response.out.write('OK')
        trello = TrelloClient()

        # use From address to denote who send this Card
        card_from = self.request.get('from').split(' ')[-1].split('@')[0].replace('<', '').replace('>', '')

        # get username of email recipient to fetch our target board
        email_recipient = self.request.get('to').split(' ')[-1].split('@')[0].replace('<', '').replace('>', '')
        target_board_name, target_list_name = email_recipient.split('-')
        if not target_board_name or not target_list_name:
            print "cannot continue"
            sys.exit()

        target_board_name = target_board_name.replace(' ', '').replace('-', '').lower()
        target_list_name = target_list_name.replace(' ', '').replace('-', '').lower()

        boards = trello.list_boards()

        found_board = None
        for one_board in boards:
            my_board = json.loads(one_board)
            if 'name' in my_board:
                if my_board['name'].lower() == target_board_name:
                    found_board = my_board

        if found_board:
            board = trello.get_board(found_board['id'])

            # loop through the lists on this board to find the one you want
            lists = board.all_lists()
            found_list = None
            for my_list in lists:
                lower_list_name = my_list.name.lower()
                if lower_list_name == target_list_name:
                    found_list = my_list

            if found_list:
                found_list.add_card(
                    name="New card from " + card_from,
                    # trello descriptions can take Markdown, so format this however you
                    desc=self.request.get('subject') + "\n\n" + self.request.get('text')
                    )


def build_url(path, query={}):
    """
    Builds a Trello URL.

    :path: URL path
    :params: dict of key-value pairs for the query string
    """
    domain = 'api.trello.com'
    url = '/1'

    if path[0:1] != '/':
        url += '/'
    url += path

    urlparams = '?'
    urlparams += "key=" + api_key
    urlparams += "&token=" + perma_token

    if len(query) > 0:
        urlparams += '&' + urlencode(query)

    return domain, url, urlparams


def fetch_json(uri_path, http_method='GET', headers={}, query_params={}, post_args={}):
    """ Fetch some JSON from Trello """

    if http_method in ("POST", "PUT", "DELETE"):
        headers['Content-type'] = 'application/json'

    headers['Accept'] = 'application/json'
    domain, url, urlparams = build_url(uri_path, query_params)
    http_client = HTTPSConnection(domain)
    url = url + urlparams
    url = url.replace(' ', '')
    if http_method == "GET":
        http_client.request(http_method, url)
    elif http_method == "POST":
        http_client.request(
            http_method,
            url,
            json.dumps(post_args),
            headers
            )

    response = http_client.getresponse()
    content = response.read()
    http_client.close()

    # error checking
    if response.status == 401:
        raise Unauthorized(url, response)
    if response.status != 200:
        raise ResourceUnavailable(url, response)
    return json.loads(content)


# this is where App Engine actually listens to a URL endpoint (foo.appspot.com/postit)
# to run all this code
app = webapp2.WSGIApplication([('/postit', MainPage)],
                              debug=True)
