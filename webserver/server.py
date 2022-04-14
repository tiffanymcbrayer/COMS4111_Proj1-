#!/usr/bin/env python2.7

"""
Columbia W4111 Intro to databases
Example webserver
To run locally
    python server.py
Go to http://localhost:8111 in your browser
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

from datetime import date
import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


DB_USER = "ttm2126"
DB_PASSWORD = "cocoa?"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/proj1part2"


#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)


# Here we create a test table and insert some values in it
engine.execute("""DROP TABLE IF EXISTS test;""")
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")


userID_ = -1
userIDdict = dict(userID = userID_)


@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request
  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


@app.route('/')
def index():
  print(request.args)
  placeInfo = g.conn.execute("""
    select place.placeID, place.name, place.picture, has.address, location.neighborhood, location.closestSubway
    from place, has, location
    where place.placeID = has.placeID and has.address = location.address
    limit 3
  """)


  collective = []
  for result in placeInfo:
    entry = [result[0], result[1], result[2], result[3], result[4], result[5]] 
    # placeID, name, picture, address, neighborhood, closestSubway

    collective.append(entry)
  placeInfo.close()
  coll = dict(data = collective)
  print(coll)


  
  return render_template("welcome.html", **coll)



@app.route('/form')
def addPage():
  print(userID_)
  if userIDdict.get('userID') == -1:
    return redirect('/login')
  else:
    return render_template('form.html', **userIDdict)

    
@app.route('/view/<id>')
def view_name(id = None):
  placeInfo = g.conn.execute("""
    select place.placeID, place.name, place.picture, has.address, location.neighborhood, location.closestSubway
    from place, has, location
    where place.placeID = has.placeID and has.address = location.address
  """)

  for result in placeInfo:
    if int(result[0]) == int(id):
      entry = [result[0], result[1], result[2], result[3], result[4], result[5]] 
  coll = dict(data = entry)

  placeInfo.close()

  return render_template('view.html', **coll)



@app.route('/another')
def another():
  return render_template("welcome.html")


# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
  user = request.form['user']
  today = date.today()
  print("Today's date:", today)
  
  print(user)
  cmd = 'INSERT INTO users VALUES (:user1)'
  g.conn.execute(text(cmd), user1 = user)
  return redirect('/')


@app.route('/login')
def login():
    return render_template('login.html', **userIDdict)

@app.route('/addLogin', methods=['POST'])
def addLogin():

  ## check here if the userID exists, if yes then dont add to the db if no then add the userID to the database
  user = request.form['user']
  userIDdict['userID'] = user
  print(userIDdict) 

  print(user)
  cmd = 'INSERT INTO users VALUES (:user1)'
  g.conn.execute(text(cmd), user1 = user)
  return redirect('/form')


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using
        python server.py
    Show the help text using
        python server.py --help
    """

    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
