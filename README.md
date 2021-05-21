# get-banned-challenge
Heroku hosted SETI@home style thing to collaboratively brute force a guessing game challenge on a discord I'm in https://discord.gg/cM3rndZ
The webpage is currently live on heroku at https://get-banned-challenge.herokuapp.com/

Update: the word was revealed by accident. It was Epäjärjestelmällistyttämättömyydelläänsäkäänköhan. So this wouldn't have been successfuly anyway since it was a non english word :(

## todo

- [X] fix issues recorded on GitHub
- [X] add code to generate words
- [X] finish filling sql wordlist
- [X] fix wrong ip address being got
- [ ] ~~add additional duplication checking using cookies?~~
- [X] Fix messages being too long
- [X] optimise for more speed (sql queries in generate_message mostly)
- [X] add indicator of progress through wordlist on requests
- [X] fix issue with line 157
- [X] add favicon
- [X] add jinja stuff for more efficient responses and more modern favicon support?
- [X] add contingency for when all the words are used (if you want to be rigorous)
- [X] add functionality to show the user the last words they were given, e.g. for if they refreshed by accident.
- [X] add script to get the most recently served messages, for when the word is found
- [X] refactor to stop duplicating the same connection code in each script
- [X] tell the user the human-readable time when they will next be able to make a successful request
- [X] tell the user the timezone of the next time they can make a request 
- [X] add get-banned-challenge.herokuapp.com/undo for marking the most recently retrieved words as unused
- [X] refactor generate_message for slightly better message length efficiency
- [X] add "copy to clipboard" button
- [X] refactor to only connect to SQL database once for one request?
- [X] finish making all pages (remaining: /undo) into Jinja templates
- [ ] prettify
- [X] add logging for /undo
- [ ] refactor to remove "message" column from last_ips, as that information is included in lastm_tuples.
- [X] add /alphasupporters
- [ ] markdown TODO

- [ ] add testing toggle with a single constant
-------
### migrating sql server
- [X] provision addon
- [X] set up env variables
- [X] install mysql workbench
- [X] migrate wordlist table
- [X] write new sql connect module
- [X] push to production!
-------
- [ ] test test test
- [ ] add docstrings and clean up comments
- [ ] separate app.py into different modules/files for tidier code
- [ ] separate existing functions into smaller functions for tidier code?
- [ ] add inheritance for more efficient templates
-------
- [ ] IDEA: client to automatically request words and send them on discord, with pyautogui?

### rewrite
- [ ] remove geoip and user frontend thing instead (didn't I write this down somewhere already?)
- [ ] finish docstrings
- [ ] use mostly just conn instead of conn, cur pairs
- [ ] read over all code and improve quality

