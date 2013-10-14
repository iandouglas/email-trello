Utilize SendGrid and App Engine to Email yourself TODO cards on Trello

This code released under Creative Commons Attribution-Sharealike 3.0:
http://creativecommons.org/licenses/by-sa/3.0/

See the LICENSE file for additional license information including a copyright
from another author.


This project was a proof-of-concept project I built during PyCon Canada in
November of 2012. Some buddies (hitsend.ca) were using Trello but during PyCon
they were constantly sending "To-Do" Emails to one another, and add them as R&D
spikes on Trello for an upcoming sprint of work. I imagined that with a few API
calls, that we could rig up a way to let them send an Email through SendGrid's
"Inbound Parse" mechanism to POST data to a URL somewhere, and write a new
Trello card for themselves.

After a brief search, not only did I not find any existing open source that
handled this, I found a service that would charge you $10/month for this very
service. Knowing that the quotas that App Engine provides (before maxing out
the 200 Emails per day of a free SendGrid developer account) would be free for
hosting, I set out to write a handler.

I found py-trello on GitHub (https://github.com/sarumont/py-trello) and due
props belong to them for the initial work they did to set up a basic
communication setup with Trello for fetching and writing data. The only problem
was that the code wouldn't work natively with Google App Engine (for one, they
don't support httplib2 which py-trello used for their http communications).

Long story short, I rewrote a significant chunk of their code. removed some
bits, and here we are.

Original code I used:
https://github.com/sarumont/py-trello/blob/b6d9ffa6e2f009a038326da3b549dfbe51c4fc60/trello/__init__.py


There are some key requirements here before you can get started:

- A Domain Name
- Access tp modify DNS records for that domain name


---------------
1. Sign up for Google App Engine (free)

1a. Sign up for a Google App Engine account.
Read more about it here: https://appengine.google.com/ You can set up a free
account with them.

1b. Set up a new application.
Follow Google's instructions for adding a new application.

---------------
2. Sign up for Trello (free)

2a. Sign up for a free Trello account
(if you don't already have one)

2b. Get your API key, and get a "permanent read/write token"
curl "https://trello.com/1/authorize?key=YOURAPIKEYGOESHERE&name=My+Application&expiration=never&response_type=token"

---------------
3. Modify my code (free)

3a. Modify app.yaml
Set your Google App Engine application name at the top of the app.yaml file.
Feel free to change the version number, but everything else can stay the same.

3b. Modify the email-trello.py
Put your API key and permanent token at the top of the script.

---------------
4. Sign up for SendGrid (free)

4a. Get a free account
You can get a free "developer" account via http://hack.sendgrid.com/ to send up
to 200 messages per day. Once you reach your 200 message limit per day, it will
block you from sending any additional messages until they reset your credits for
the next day.

4b. Once your SendGrid account is provisioned, follow the instructions to set
up the "Inbound Parse" feature:
    http://sendgrid.com/docs/API%20Reference/Webhooks/parse.html

This will require that you add a subdomain on your current domain. You might
want to call call it "trello.yourdomain.com" or "todo.yourdomain.com". Per the
SendGrid instructions, you will need to add an MX record for that subdomain to
point to mx.sendgrid.net

4c. Set up your Parse API url for POST operations
Visit http://sendgrid.com/developer/reply (once you're logged into SendGrid) and
add your subdomain and App Engine application URL
(ie http://yourprojectname.appspot.com/postit). This step will require that the
DNS settings for your subdomain and its associated MX record have propagated
around the world enough that SendGrid can detect it.

---------------

At this point, your App Engine application should be running, SendGrid is all
set up and provisioned, Trello is ready and waiting. Now all you need to do is
try to send a sample Email in this format:

trello_board_name-board_list_name@subdomain.yourdomain.com

Let's break this down and explain a few things:

"trello_board_name"
Trello allows you to have multiple "boards" where you can post lists of "cards".
This first portion of the Email recipient address will be the name of this
board, without spaces or dashes. For example, "To-Do" would simply become
"todo". "Brilliant Ideas" would become "brilliantideas" and so on.

"board_list_name"
Since each board can have multiple lists, this portion of the address will
indicate which list will get the card data. Like the board name, dashes and
spaces will be removed, so "To-Do" would become "todo", "Current Sprint" would
become "currentsprint" and so on.

To clarify, your Trello boards and lists can have spaces and dashes, but the
address you send a message to cannot have these spaces or dashes. The board
name and list name are separated with a dash, like "board-list" (your App Engine
application will parse it this way).

If you have a board called "To Do" and a list called "Grocery shopping", the
recipient Email address you would use would start out with
todo-groceryshopping@


@subdomain.yourdomain.com
This is the subdomain you set up at SendGrid. SendGrid won't care about the
username of the recipient Email address, but any messages it receives at
subdomain.yourdomain.com will trigger a POST of data to your App Engine
application.

The App Engine application will then parse the POST data that SendGrid sends,
find the "From" address, and strip it down to just the username of the Email
address (ie, joe.smith@address.com would become just "joe.smith"). It should
handle full "named" sender addresses as well, so a header that looks like this:
From: Ian Douglas <ian.douglas@iandouglas.com>
... should parse down to just "ian.douglas"

The application will perform a similar strip-down of the recipient address to
break down the target board/list names.

Since Trello's API does not include a way to retrieve a list of all boards your
API key will have access to (as of November 2012), I had to do an alpha/numeric
search. And since their search could do partial searches, the code will actually
iterate through string.lowercase() + string.digits(), fetch data for each Board
name it finds, makes sure it gets added to a unique list, then checks if any of
those board names (lowercased, stripped of spaces and dashes) match the first
fragment of the recipient Email address.

If it finds a match for the board name, it then fetches all lists (open and
closed) for that Board from Trello to find a matching list name (also lowercased
and stripped of spaces and dashes). If a match is found there as well, then the
subject line and body of the message are written into a new card within that
Board/List.

Either way, unless there's a script error at App Engine, SendGrid will receive
a "200" status code and consider the transaction finished.


---------------
Things you may want to do with this:

If you find this useful, please fork the project and contribute code back to it.
This was literally an evening hack, and there are likely better/cleaner ways
to do things. Also, since I had to hack the py-trello code,
there may be enhancements and changes there (plus newer versions of the
Trello API) that may need updating.

Since App Engine can handle OAuth, you may or may not want to look at setting up
a proper OAuth system between App Engine and Trello to work for multiple users.
Hey, you could even start up a service to charge people $10/month for it...


---------------
It goes without saying that while this code works perfectly for me (my wife
uses it to send messages to my "Honey Do" list on a "Family" board),
your mileage may vary and this may not work for you. I also haven't modified
it or tweaked it other than some simple PEP8 conventions and a lot more
documentation.

I hold no liability or responsibility for your use of this code. I'm happy to
support you as best I can, but you're mostly on your own.

My employer, SendGrid Inc, is not liable in any way for your use of this code.