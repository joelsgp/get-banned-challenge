from jmcb_mysql import mysql_connect, mysql_disconnect

conn, cur = mysql_connect()

message_words_tuples = [(1,), (2,)]
used_sql = "TRUE"

args_list = [sql_response[0] for sql_response in message_words_tuples]
args_list = [True] + args_list
args_list = tuple(args_list)
args_template_str = "%s,"*(len(message_words_tuples)-1) + "%s"
# This doesn't work
##cur.execute("""
##            UPDATE wordlist
##            SET used = %s
##            WHERE id IN ({})
##            """.format(args_template_str),
##            tuple(args_list))
print(args_list)
print(args_template_str)
print("""
      UPDATE wordlist
      SET used = %s
      WHERE id IN ({})
      """.format(args_template_str))
query = """
        UPDATE wordlist
        SET used = %s
        WHERE id IN ({})
        """.format(args_template_str)

# This works!
##cur.execute("""
##            UPDATE wordlist
##            SET used = TRUE
##            WHERE id IN (%s,%s)
##            """, (1,2))

# This doesn't work
##cur.execute("""
##            UPDATE wordlist
##            SET used = %s
##            WHERE id IN (1,2)
##            """, ("TRUE",))

# This doesn't work
cur.execute(query, args_list)

# This works
##cur.execute("""
##            UPDATE wordlist
##            SET used = TRUE
##            WHERE id IN (1,2)
##            """)

print(cur.statement)
print(cur.rowcount)

cur.close()
conn.commit()


conn.close()
