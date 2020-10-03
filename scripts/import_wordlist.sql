LOAD DATA LOCAL INFILE 'C:/Users/joelm/Documents/_Programming/_python/wrtv discord/get-banned-challenge/wordlist_sqlready.csv'
INTO TABLE wordlist
FIELDS TERMINATED BY ','
LINES TERMINATED BY '\n'