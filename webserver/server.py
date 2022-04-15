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
DB_SERVER = "w4111project1part2db.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/proj1part2"


#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)



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


  
  return render_template("welcome.html", **coll)



@app.route('/form')
def addPage():
  placeList = g.conn.execute("""
    select *
    from place
  """)
  places = []
  for place in placeList:
    entry = [place[0], place[1]] # placeID, place name
    places.append(entry)
  placeDict = dict(data = places)
  
  placeList.close()
  return render_template('form.html', **userIDdict, **placeDict)

    
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

  operatingHours = g.conn.execute("""
    select *
    from operating_open
  """)
  hours = []
  for result in operatingHours:
    if result[0] == int(id):
      entry = [result[1], result[2], result[3]] # day, start. end 
      hours.append(entry)
  hoursDict = dict(hoursList = hours)
  operatingHours.close()

  menuInfo = g.conn.execute("""
    WITH newTable AS(
    select contain.placeID, contain.menuID, item.itemID, item.cost, item.name
    from contain JOIN item 
    on contain.itemID = item.itemID 
    group by placeID, menuID, item.itemID, name, cost
    )
    
    SELECT newTable.placeid, newTable.menuid, newTable.itemid, newTable.cost, newTable.name, has_menu.name as menuName
    FROM newTable JOIN has_menu
    ON newTable.menuID = has_menu.menuID
    group by newTable.placeid, newTable.menuid, newTable.itemid, newTable.cost, newTable.name, has_menu.name
  """)
  menus = []
  countedMenu = []
  for result in menuInfo:
    if result[0] == int(id):
      if result[5] not in countedMenu:
        menus.append([result[5]],[])
        countedMenu.append(result[5])
        index  = countedMenu.index(result[5])
        entry = [result[4], result[3]] # name, cost 
        menus[index][1].append(entry)
      else:
        index  = countedMenu.index(result[5])
        entry = [result[4], result[3]] # name, cost 
        menus[index][1].append(entry)
  print()
      
  menusDict = dict(menuList = menus)
  # [drinks,[item cost, item name, ]]

  # placeid, menuid, itemid, cost, name, menuName




  menuInfo.close()
  return render_template('view.html', **coll, **hoursDict, **menusDict)



@app.route('/another')
def another():
  return render_template("welcome.html")


# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
  user = request.form['user']

  usersList = g.conn.execute("""
    select *
    from users
  """)
  users = []
  for userID in usersList:
    users.append(userID[0])
  if int(user) not in users:
    cmd = 'INSERT INTO users VALUES (:user1)'
    g.conn.execute(text(cmd), user1 = user)
  usersList.close()

  today = date.today()
  print("Today's date:", today)

  placeID = request.form['placeID']
  # should not need to be error checked bc of the drop down 

  waitTime = request.form['waitTime']
  cover = request.form['cover']
  minSpend = request.form['minSpend']
  group = request.form['group']
  
  if not (waitTime.isnumeric() or cover.isnumeric() or minSpend.isnumeric() or group.isnumeric()):
    return redirect('/form')

  capacity = request.form['capacity']

  ageMin = request.form['ageMin'] # this is a string
  ageMax = request.form['ageMax'] # this is a string
  if int(ageMin) > int(ageMax):
    return redirect('/form')
  ageRange = ageMin + "-" + ageMax
  
  

  print(placeID, waitTime, cover, minSpend, capacity, ageRange, group)


  return redirect('/')





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


