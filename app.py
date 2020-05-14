#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
import sys

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

Shows = db.Table('Shows',
  db.Column('artist_id', db.Integer, db.ForeignKey('Artist.id'), primary_key=True),
  db.Column('venue_id', db.Integer, db.ForeignKey('Venue.id'), primary_key=True),
  db.Column('date', db.DateTime, primary_key=True)
)


class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String(120)))
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(500))
    artist_show = db.relationship('Artist', secondary=Shows, backref=db.backref('venues'), lazy=True)

    # TODO: implement any missing fields, as a database migration using Flask-Migrate

class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String(120)))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(500))

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  main_data =db.session.query(Venue.state, Venue.city).group_by(Venue.state, Venue.city).order_by(Venue.state, Venue.city).all()
  data=[]
  venues=[]
  for d in main_data:
    venue_location = Venue.query.filter(Venue.city == d.city, Venue.state == d.state).all()
    for v in venue_location:
      venue_name = {
        'id': v.id, 'name': v.name, 'num_upcoming_shows': db.session.query(Shows).filter(Shows.c.venue_id == v.id, Shows.c.date > datetime.now()).count()
      }
      venues.append(venue_name)
    data.append({'city': d.city, 'state': d.state, 'venues': venues})
    venues=[]
  return render_template('pages/venues.html', areas=data);

@app.route('/venues/search', methods=['POST'])
def search_venues():
    data=[]
    search_data= request.form.get('search_term')
    venue_search = db.session.query(Venue).filter(Venue.name.ilike('%' + search_data + '%')).all()

    for d in venue_search:
      data.append({'id':d.id, 'name':d.name, 'num_upcoming_shows':db.session.query(Shows).filter(Shows.c.venue_id == d.id, Shows.c.date > datetime.now()).count()})

    response={
      "count": len(data),
      "data": data
    }
    return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):

  past_shows=[]
  upcoming_shows=[]

  main_data= Venue.query.get(venue_id)
  sub_query=db.session.query(Shows).filter(Shows.c.venue_id==venue_id).subquery('sub_query')
  main_qurey= db.session.query(Artist,sub_query).join(Artist).all()
  for d in main_qurey:
    if d.date > datetime.now():
      upcoming_shows.append({'artist_id':d.Artist.id, 'artist_name':d.Artist.name, 'artist_image_link':d.Artist.image_link, 'start_time':d.date.strftime('%Y/%m/%d-%H:%M')})
    else:
      past_shows.append({'artist_id':d.Artist.id, 'artist_name':d.Artist.name, 'artist_image_link':d.Artist.image_link, 'start_time':d.date.strftime('%Y/%m/%d-%H:%M')})
  

  data={'id':main_data.id, 'name': main_data.name, 'genres': main_data.genres,
        'address':main_data.address, 'city':main_data.city, 'state':main_data.state, 
        'phone':main_data.phone, 'website':main_data.website, 'facebook_link':main_data.facebook_link, 
        'seeking_talent': main_data.seeking_talent, 'seeking_description':main_data.seeking_description, 
        'image_link':main_data.image_link, 'past_shows': past_shows, 'upcoming_shows':upcoming_shows,
        'past_shows_count':len(past_shows), 'upcoming_shows_count':len(upcoming_shows)
        }
  
  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  error = False
  try:
    name= request.form.get('name')
    city= request.form.get('city')
    state= request.form.get('state')
    address= request.form.get('address')
    phone= request.form.get('phone')
    image_link= request.form.get('image_link')
    genres= request.form.get('genres')
    facebook_link= request.form.get('facebook_link')
    website= request.form.get('website')
    if request.form.get('seeking_talent') == 'YES':
      seeking_talent=True
    else:
      seeking_talent=False
    seeking_description= request.form.get('seeking_description')
    venue = Venue(name=name, city=city, state=state, address=address, 
                  phone=phone, image_link=image_link, genres=genres,
                  facebook_link=facebook_link, website=website,
                  seeking_talent=seeking_talent, seeking_description=seeking_description
                  )
    db.session.add(venue)
    db.session.commit()
    
  except:
    error=True
    db.session.rollback()
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
    print(sys.exc_info())

  finally:
      db.session.close()

  if not error:
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
      
  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # TODO: Complete this endpoint for taking a venue_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.

  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
   # clicking that button delete it from the db then redirect the user to the homepage
  return None

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():

  main_data =Artist.query.order_by(Artist.name).all()
  data=[]
  for d in main_data:
    data.append({'id': d.id, 'name': d.name})
  return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    data=[]
    search_data= request.form.get('search_term')
    artist_search = db.session.query(Artist).filter(Artist.name.ilike('%' + search_data + '%')).all()

    for d in artist_search:
      data.append({'id':d.id, 'name':d.name, 'num_upcoming_shows':db.session.query(Shows).filter(Shows.c.artist_id == d.id, Shows.c.date > datetime.now()).count()})

    response={
      "count": len(data),
      "data": data
    }


    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):

  past_shows=[]
  upcoming_shows=[]

  main_data= Artist.query.get(artist_id)
  sub_query=db.session.query(Shows).filter(Shows.c.artist_id==artist_id).subquery('sub_query')
  main_qurey= db.session.query(Venue,sub_query).join(Venue).all()
  for d in main_qurey:
    if d.date > datetime.now():
      upcoming_shows.append({'venue_id':d.Venue.id, 'venue_name':d.Venue.name, 
                              'venue_image_link':d.Venue.image_link, 
                              'start_time':d.date.strftime('%Y/%m/%d-%H:%M')}
                            )
    else:
      past_shows.append({'venue_id':d.Venue.id, 'venue_name':d.Venue.name, 
                          'venue_image_link':d.Venue.image_link, 
                          'start_time':d.date.strftime('%Y/%m/%d-%H:%M')}
                        )
  

  data={'id':main_data.id, 'name': main_data.name, 'genres': main_data.genres,
        'city':main_data.city, 'state':main_data.state, 
        'phone':main_data.phone, 'website':main_data.website, 'facebook_link':main_data.facebook_link, 
        'seeking_talent': main_data.seeking_talent, 'seeking_description':main_data.seeking_description, 
        'image_link':main_data.image_link, 'past_shows': past_shows, 'upcoming_shows':upcoming_shows,
        'past_shows_count':len(past_shows), 'upcoming_shows_count':len(upcoming_shows)
        }
  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist_det = Artist.query.get(artist_id)
  form.name.data = artist_det.name
  form.genres.data = artist_det.genres
  form.city.data = artist_det.city
  form.state.data = artist_det.state
  form.phone.data = artist_det.phone
  form.website.data = artist_det.website
  form.facebook_link.data = artist_det.facebook_link
  if artist_det.seeking_talent:
    form.seeking_talent.data = 'YES'
  else:
    form.seeking_talent.data = 'NO'
  form.seeking_description.data = artist_det.seeking_description
  form.image_link.data = artist_det.image_link



  return render_template('forms/edit_artist.html', form=form, artist=artist_det)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  error= False
  try:
    artist_det = Artist.query.get(artist_id)
    name= request.form.get('name')
    city= request.form.get('city')
    state= request.form.get('state')
    phone= request.form.get('phone')
    image_link= request.form.get('image_link')
    genres= request.form.get('genres')
    facebook_link= request.form.get('facebook_link')
    website= request.form.get('website')
    if request.form.get('seeking_talent') == 'YES':
      seeking_talent=True
    else:
      seeking_talent=False

    seeking_description= request.form.get('seeking_description')
    
    # artist_det = Artist.query.get(artist_id)
    artist_det.name = name
    artist_det.genres = genres
    artist_det.city = city
    artist_det.state = state
    artist_det.phone = phone
    artist_det.website = website
    artist_det.facebook_link = facebook_link
    artist_det.seeking_talent = seeking_talent
    artist_det.seeking_description = seeking_description
    artist_det.image_link = image_link


    db.session.commit()
  except:
    error=True
    db.session.rollback()
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be updated.')
    print(sys.exc_info())
  finally:
    db.session.close()

  if not error:
    flash('Artist ' + request.form['name'] + ' was successfully updated!')
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  # venue={
  #   "id": 1,
  #   "name": "The Musical Hop",
  #   "genres": ["Jazz", "Reggae", "Swing", "Classical", "Folk"],
  #   "address": "1015 Folsom Street",
  #   "city": "San Francisco",
  #   "state": "CA",
  #   "phone": "123-123-1234",
  #   "website": "https://www.themusicalhop.com",
  #   "facebook_link": "https://www.facebook.com/TheMusicalHop",
  #   "seeking_talent": True,
  #   "seeking_description": "We are on the lookout for a local artist to play every two weeks. Please call us.",
  #   "image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60"
  # }
  venue_det = Venue.query.get(venue_id)
  form.name.data = venue_det.name
  form.genres.data = venue_det.genres
  form.address.data= venue_det.address
  form.city.data = venue_det.city
  form.state.data = venue_det.state
  form.phone.data = venue_det.phone
  form.website.data = venue_det.website
  form.facebook_link.data = venue_det.facebook_link
  if venue_det.seeking_talent:
    form.seeking_talent.data = 'YES'
  else:
    form.seeking_talent.data = 'NO'
  form.seeking_description.data = venue_det.seeking_description
  form.image_link.data = venue_det.image_link

  # TODO: populate form with values from venue with ID <venue_id>
  return render_template('forms/edit_venue.html', form=form, venue=venue_det)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  error= False
  try:
    venue_det = Venue.query.get(venue_id)
    name= request.form.get('name')
    address= request.form.get('address')
    city= request.form.get('city')
    state= request.form.get('state')
    phone= request.form.get('phone')
    image_link= request.form.get('image_link')
    genres= request.form.get('genres')
    facebook_link= request.form.get('facebook_link')
    website= request.form.get('website')
    if request.form.get('seeking_talent') == 'YES':
      seeking_talent=True
    else:
      seeking_talent=False

    seeking_description= request.form.get('seeking_description')
    

    venue_det.name = name
    venue_det.genres = genres
    venue_det.city = city
    venue_det.address = address
    venue_det.state = state
    venue_det.phone = phone
    venue_det.website = website
    venue_det.facebook_link = facebook_link
    venue_det.seeking_talent = seeking_talent
    venue_det.seeking_description = seeking_description
    venue_det.image_link = image_link

    db.session.commit()
  except:
    error=True
    db.session.rollback()
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be updated.')
    print(sys.exc_info())
  finally:
    db.session.close()

  if not error:
    flash('Venue ' + request.form['name'] + ' was successfully updated!')


  # TODO: take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  error= False
  try:
    name= request.form.get('name')
    city= request.form.get('city')
    state= request.form.get('state')
    phone= request.form.get('phone')
    image_link= request.form.get('image_link')
    genres= request.form.get('genres')
    facebook_link= request.form.get('facebook_link')
    website= request.form.get('website')
    if request.form.get('seeking_talent') == 'YES':
      seeking_talent=True
    else:
      seeking_talent=False

    seeking_description= request.form.get('seeking_description')
    atist = Artist(name=name, city=city, state=state, phone=phone, 
                  image_link=image_link, genres=genres,
                  facebook_link=facebook_link, website=website,
                  seeking_talent=seeking_talent, seeking_description=seeking_description
                  )
    db.session.add(atist)
    db.session.commit()
  except:
    error=True
    db.session.rollback()
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
    print(sys.exc_info())
  finally:
    db.session.close()

  if not error:
    flash('Artist ' + request.form['name'] + ' was successfully listed!')

  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():

  main_data =db.session.query(Shows).all()
  data=[]

  for d in main_data:
    show_venue_det=Venue.query.get(d.venue_id)
    show_artist_det=Artist.query.get(d.artist_id)

    data.append({'venue_id': d.venue_id, 'venue_name':show_venue_det.name,
                  'artist_id': d.artist_id, 'artist_name': show_artist_det.name,
                  'artist_image_link': show_artist_det.image_link, 'start_time': d.date.strftime('%Y/%m/%d-%H:%M')}
                )
    
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  error= False
  try:
    artist_id = request.form.get("artist_id")
    venue_id = request.form.get("venue_id")
    start_time = request.form.get("start_time")
    Show = Shows.insert().values(artist_id=artist_id, venue_id=venue_id, date=start_time)
    db.session.execute(Show)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
    flash('An error occurred. Show could not be listed.')
    print(sys.exc_info())
  finally:
    db.session.close()
    
  if not error:
    flash('Show was successfully listed!')

  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
