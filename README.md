# get-banned-challenge
Heroku hosted SETI@home style thing to collaboratively brute force a guessing game challenge on a discord I'm in https://discord.gg/cM3rndZ
The webpage is currently live on heroku at https://get-banned-challenge.herokuapp.com/

Update: the word was revealed by accident. It was Epäjärjestelmällistyttämättömyydelläänsäkäänköhan. So this wouldn't have been successfuly anyway since it was a non english word :(

## todo

- [x] fix issues recorded on GitHub
- [x] add code to generate words
- [x] finish filling sql wordlist
- [x] fix wrong ip address being got
- [ ] ~~add additional duplication checking using cookies?~~
- [x] Fix messages being too long
- [x] optimise for more speed (sql queries in generate_message mostly)
- [x] add indicator of progress through wordlist on requests
- [x] fix issue with line 157
- [x] add favicon
- [x] add jinja stuff for more efficient responses and more modern favicon support?
- [x] add contingency for when all the words are used (if you want to be rigorous)
- [x] add functionality to show the user the last words they were given, e.g. for if they refreshed by accident.
- [x] add script to get the most recently served messages, for when the word is found
- [x] refactor to stop duplicating the same connection code in each script
- [x] tell the user the human-readable time when they will next be able to make a successful request
- [x] tell the user the timezone of the next time they can make a request 
- [x] add get-banned-challenge.herokuapp.com/undo for marking the most recently retrieved words as unused
- [x] refactor generate_message for slightly better message length efficiency
- [x] add "copy to clipboard" button
- [x] refactor to only connect to SQL database once for one request?
- [x] finish making all pages (remaining: /undo) into Jinja templates
- [ ] prettify html/css
- [x] add logging for /undo
- [ ] refactor to remove "message" column from last_ips, as that information is included in lastm_tuples.
- [x] add /alphasupporters
- [x] markdown TODO

- [ ] add testing toggle with a single constant
-------
### migrating sql server
- [x] provision addon
- [x] set up env variables
- [x] install mysql workbench
- [x] migrate wordlist table
- [x] write new sql connect module
- [x] push to production!
-------
- [ ] test test test
- [x] add docstrings and clean up comments
- [ ] separate app.py into different modules/files for tidier code
- [ ] separate existing functions into smaller functions for tidier code?
- [ ] add inheritance for more efficient templates
-------
- [ ] IDEA: client to automatically request words and send them on discord, with pyautogui?

### rewrite
- [x] remove geoip and use frontend thing instead (didn't I write this down somewhere already?)
- [x] finish docstrings
- [ ] use mostly just conn instead of conn, cur pairs
- [x] read over all code and improve quality
- [x] type hinting
- [ ] handle time stuff better, probably with datetime objects
