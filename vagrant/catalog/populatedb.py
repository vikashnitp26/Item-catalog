from catalog.database import db_session, init_db, dbfilename

from catalog.models import Item, Tag

import os

# Remove database if it exists

print "Checking for existing sqlite database."
if dbfilename:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    db_file_path = os.path.join(script_dir, dbfilename)

    if os.path.isfile(db_file_path):
        print "Old database found. Deleting."
        os.remove(db_file_path)
    else:
        print "No old database found."

# Create the database

print "Creating and initialising database."
init_db()

#Create tags

print "Creating tags."

books = Tag(name='Books', user_id=1)
db_session.add(books)

novels = Tag(name='Novels', user_id=1)
db_session.add(novels)

nonfiction = Tag(name='Non-fiction', user_id=1)
db_session.add(nonfiction)

furniture = Tag(name='Furniture', user_id=1)
db_session.add(furniture)

cars = Tag(name='Cars', user_id=1)
db_session.add(cars)

vehicles = Tag(name='Vehicles', user_id=1)
db_session.add(vehicles)

boats = Tag(name='Boats', user_id=1)
db_session.add(boats)

db_session.commit()


# Create items

print "Creating items."

i1 = Item(name='Dictionary',
		  description='The latest Oxford dictionary',
		  tags=[books, nonfiction],
		  user_id=1,
		  picture_url = "http://ecx.images-amazon.com/images/I/51RmpdfuGRL._SX379_BO1,204,203,200_.jpg")
db_session.add(i1)

i2 = Item(name='Chair',
		  description='An old antique chair',
		  tags=[furniture],
		  user_id=1,
		  picture_url="https://upload.wikimedia.org/wikipedia/commons/5/52/Karin_larsson_schommelstoel.jpg")
db_session.add(i2)

i3 = Item(name='Coffee table',
	      description='A perfectly ordinary coffee table',
	      tags=[furniture],
	      user_id=1,
	      picture_url="https://upload.wikimedia.org/wikipedia/en/thumb/7/7b/Domestic_coffee_table_in_residential_setting.jpg/500px-Domestic_coffee_table_in_residential_setting.jpg")
db_session.add(i3)

i4 = Item(name='Landrover',
		  description='Chelsea tractor',
		  tags=[cars, vehicles],
		  user_id=1,
		  picture_url="https://upload.wikimedia.org/wikipedia/en/thumb/5/5e/Landrover2a.jpg/440px-Landrover2a.jpg")
db_session.add(i4)

i5 = Item(name='Sailing Boat',
		  description='A beautiful sailing boat',
		  tags=[vehicles, boats],
		  user_id=1,
		  picture_url="https://upload.wikimedia.org/wikipedia/commons/thumb/8/85/Nonsuch30.jpg/200px-Nonsuch30.jpg")
db_session.add(i5)

i6 = Item(name='Pride and Prejudice',
		  description='Classic novel by Jane Austen',
		  tags=[books, novels],
		  user_id=1,
		  picture_url="https://upload.wikimedia.org/wikipedia/commons/thumb/1/17/PrideAndPrejudiceTitlePage.jpg/440px-PrideAndPrejudiceTitlePage.jpg")
db_session.add(i6)

i7 = Item(name='Wolf Hall',
	      description='Historical novel by Hilary Mantel',
	      tags=[books, novels],
	      user_id=1,
	      picture_url="https://upload.wikimedia.org/wikipedia/en/e/ed/Wolf_Hall_cover.jpg")
db_session.add(i7)

db_session.commit()

print "Done."