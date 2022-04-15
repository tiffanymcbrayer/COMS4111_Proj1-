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




@app.route('/event/<id>')
def events(id = None):
  # EVENT INFO 
  cmd2 = """
    WITH temp3 AS(
      WITH temp2 AS (
        WITH temp AS(
          SELECT hold.eventid,	hold.placeid, event.name, event.description, event.numberattendees
          FROM hold join event
          on hold.eventID = event.eventID 
        )

        select temp.eventid,	temp.placeid, temp.name, temp.description, temp.numberattendees, has.address
        from temp join has
        on temp.placeid = has.placeid and temp.placeid = (:id1)
      )

      select temp2.eventid,	temp2.placeid, place.name as placename, temp2.name, temp2.description, temp2.numberattendees, temp2.address
      from temp2 join place
      on temp2.placeid = place.placeid 
    )
    select temp3.eventid,	temp3.placeid, temp3.placename, temp3.name, temp3.description, temp3.numberattendees, temp3.address, occur_when.date, 
    occur_when.recur, occur_when.allday, occur_when.timerange, occur_when.starttime, occur_when.endtime
    from temp3 join occur_when
    on temp3.eventid = occur_when.eventid
  """
  eventInfo = g.conn.execute(text(cmd2), id1 = id)

  for eventid, placeid, placename, name, description, numberattendees, address, date, recur, allday, timerange, starttime, endtime in eventInfo:
    entry = [placename, name, description, numberattendees, address, date, recur, allday, timerange, starttime, endtime, eventid]
  eventDict = dict(event = entry)
  eventInfo.close()

  # eventid	placeid	placename	name	description	numberattendees	address

  return render_template('event.html', **eventDict)
    



@app.route('/view/<id>')
def view_name(id = None):

  # PLACE INFO 
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

  # HOURS INFO 
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

  # MENU INFO
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
        menus.append([result[5], []])
        countedMenu.append(result[5])
        index  = countedMenu.index(result[5])
        entry = [result[4], result[3]] # name, cost 
        menus[index][1].append(entry)
      else:
        index  = countedMenu.index(result[5])
        entry = [result[4], result[3]] # name, cost 
        menus[index][1].append(entry)
      
  menusDict = dict(menuList = menus)
  menuInfo.close()

  # REVIEWS INFO 

  cmd = """ 
    select AVG(form_review.wait) AS waitTime, AVG(form_review.cover) as Cover, AVG(form_review.minSpend) as minSpend, AVG(form_review.capacity) as Capacity, AVG(form_review.groupSize) as groupSize
    from form_review natural join place
    where placeID = (:id1)
  """
  reviewInfo = g.conn.execute(text(cmd), id1 = id)
  for waittime, cover, minspend, capacity, groupSize in reviewInfo:
    entry = [int(waittime), int(cover), int(minspend), int(capacity), int(groupSize)]
  reviewDict = dict(review = entry)
  reviewInfo.close()

  # EVENT INFO 
  cmd2 = """
    WITH temp AS(
      SELECT hold.eventid,	hold.placeid, event.name, event.description, event.numberattendees
      FROM hold join event
      on hold.eventID = event.eventID
    )

    select temp.eventid,	temp.placeid, temp.name, temp.description, temp.numberattendees, has.address
    from temp join has
    on temp.placeid = has.placeid and temp.placeID = (:id1)
  """
  eventInfo = g.conn.execute(text(cmd2), id1 = id)
  eventList = []
  for result in eventInfo:
    eventList.append([result[0],result[2]]) # just appending the name, will create the hyperlink after
  eventDict = dict(events = eventList)
  eventInfo.close()
  return render_template('view.html', **coll, **hoursDict, **menusDict, **reviewDict, **eventDict)



@app.route('/another')
def another():
  return render_template("welcome.html")

@app.route('/addAttend', methods=['POST'])
def addAttend():
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

  eventID = request.form['eventID']
  attendeesList = g.conn.execute("""
    select *
    from attends
  """)
  attendees = []
  for result in attendeesList:
    attendees.append([result[0], result[1]])
  print(attendees)
  currEntry = [int(user), int(eventID)]
  print(currEntry)
  if currEntry not in attendees:
    cmd2 = 'INSERT INTO attends VALUES ((:user1),(:eventID1))'
    g.conn.execute(text(cmd2),  user1 = user, eventID1 = eventID)
  
  cmd3 = """
    select numberattendees
    from event
    where eventid = (:eventID1)
  """
  numberAttendees = g.conn.execute(text(cmd3),  eventID1 = eventID)
  print("number")
  for result in numberAttendees:
    currAttendees = result[0]
  numberAttendees.close()
  print(currAttendees)
  currAttendees += 1

  cmd4 = '''
    UPDATE event 
    SET numberattendees = (:currAttendees1)
    WHERE eventid = (:eventID1)
  '''
  g.conn.execute(text(cmd4), currAttendees1 = currAttendees, eventID1 = eventID)


  return redirect('/')


# Adding info from form.html
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

  day = date.today()
  print("Today's date:", day)

  placeID = request.form['placeID']

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

  formList = g.conn.execute("""
    select userid,	placeid,	day
    from form_review
  """)
  compares = []
  for result in formList:
    print(result)
    compares.append([result[0], result[1], str(result[2])])
  currForm = [int(user), int(placeID), str(day)]
  if currForm not in compares:
    cmd2 = """
    INSERT INTO form_review VALUES 
    ((:user1), (:placeID1), (:day1), (:waitTime1), (:cover1), (:minSpend1), (:capacity1), (:ageRange1), (:group1))
    """
    g.conn.execute(text(cmd2), user1 = int(user), placeID1 = int(placeID), day1 = str(day), waitTime1 = int(waitTime), cover1 = int(cover), minSpend1 = int(minSpend), capacity1 = int(capacity), ageRange1 = ageRange, group1 = int(group))
  else:
    return redirect('/form')
  formList.close()


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


