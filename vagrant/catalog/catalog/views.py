from flask import (render_template, abort, request, session, redirect,
                   url_for, jsonify, flash)
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.exc import IntegrityError
from werkzeug.contrib.atom import AtomFeed

from . import app

from .forms import TagForm, ItemForm, BlankForm, LoginCSRFForm

# Imports for dealing with database / models
from .database import db_session
from .models import Item, Tag, User

# Imports for oauth views - gconnect and gdisconnect
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

# Other auth related imports
from auth_helpers import (login_required, make_url_relative, owner_only,
                          admin_only, activated_user_required)

@app.route('/')
@app.route('/catalog/')
def index():
    """View to provide a main index page for our site"""
    tags = db_session.query(Tag).all()
    items = db_session.query(Item).all()

    # Check if user logged in
    logged_in = 'user_id' in session

    # If logged in, check if activated:
    user = None
    if logged_in:
        user = db_session.query(User).filter_by(id=session['user_id']).one()

    return render_template('catalog.html',
                            tags=tags,
                            items=items,
                            logged_in=logged_in,
                            user=user)

# Views for viewing data in web page form

@app.route('/catalog/tags/view/<tag_name>/')
def viewTag(tag_name):
    """View to allow users to view tag information and associated
    items."""
    try:
        tag = db_session.query(Tag).filter_by(name=tag_name).one()
    except (MultipleResultsFound, NoResultFound):
        # If there's more or less than one tag with that name,
        # throw a 404
        abort(404)
    
    # Check if user logged in
    logged_in = 'user_id' in session

    # Determine if logged in user is owner of tag
    if tag.user_id == session.get('user_id'):
        owner = True
    else:
        owner = False

    # Determine if logged in user is an admin
    user = None
    if session.get('user_id'):
        user = User.getByID(session.get('user_id'), db_session)

    return render_template('viewtag.html',
                            tag=tag,
                            logged_in=logged_in,
                            owner=owner,
                            user=user)

@app.route('/catalog/items/view/<item_name>-<int:item_id>/')
def viewItem(item_name, item_id):
    """View to allow users to view information about individual
    items."""
    try:
        item = db_session.query(Item).filter_by(name=item_name,
                                                id=item_id).one()
    except (MultipleResultsFound, NoResultFound):
        # If there are more or less than one item with that name and id
        # throw a 404
        abort(404)

    # Check if user logged in
    logged_in = 'user_id' in session

    # Determine if logged in user is owner of item
    if item.user_id == session.get('user_id'):
        owner = True
    else:
        owner = False

    # Determine if logged in user is an admin
    user = None
    if session.get('user_id'):
        user = User.getByID(session.get('user_id'), db_session)

    return render_template('viewitem.html',
                            item=item,
                            logged_in=logged_in,
                            owner=owner,
                            user=user)


# Views for creating new data entities

@app.route('/catalog/tags/new/', methods=['GET', 'POST'])
@login_required(session)
@activated_user_required(session, db_session)
def newTag():
    """View to provide a form for creating new tags, and to respond
    POST requests from this form."""

    form = TagForm(request.form, meta={'csrf_context': session})
    
    if request.method == 'POST' and form.validate():
        try:
            new_tag = Tag(name=form.tag_name.data,
                          user_id=session['user_id'])
            db_session.add(new_tag)
            db_session.commit()

            # Log creation of new tag
            app.logger.info(
                "Created {}, user IP address: {}".format(new_tag,
                                                         request.remote_addr))

            return redirect(url_for('index'))
        except IntegrityError:
            # If user tries to create a tag with an existing name,
            # roll back and add a form error
            db_session.rollback()
            form.tag_name.errors.append(
                'A tag already exists with that name.')

    return render_template('tagform.html',
                            form=form,
                            action="newTag",
                            logged_in=True)

@app.route('/catalog/items/new/', methods=['GET', 'POST'])
@login_required(session)
@activated_user_required(session, db_session)
def newItem():
    """View to provide a form for creating new items, and to respond
    POST requests from this form."""

    form = ItemForm(request.form, meta={'csrf_context': session})
    
    # Get all tags from database
    tags = db_session.query(Tag).all()
    # Fill multiselect with these tags
    form.tags.choices = [(unicode(g.id), g.name) for g in tags]
    
    if request.method == 'POST' and form.validate():
        
        # Get list of the ids of the selected tags.
        item_tag_ids = map(int, form.tags.data)
        
        # Use this to get a list of these as Tag objects.
        item_tags = db_session.query(Tag)                           \
                              .filter(Tag.id.in_(item_tag_ids))     \
                              .all()
        
        # Create new item using this information.
        new_item = Item(name = form.name.data,
                        description=form.description.data,
                        tags=item_tags,
                        picture_url=form.picture_url.data,
                        user_id=session['user_id'])
        db_session.add(new_item)
        db_session.commit()

        # Log creation of new item
        app.logger.info(
            "Created {}, user IP address: {}".format(new_item,
                                                     request.remote_addr))

        return redirect(url_for('index'))

    return render_template('itemform.html',
                            form=form,
                            action='newItem',
                            logged_in=True)


# Views for editing existing entities

@app.route('/catalog/tags/edit/<tag_name>/', methods=['GET', 'POST'])
@login_required(session)
@owner_only(session, db_session, Tag)
@activated_user_required(session, db_session)
def editTag(tag_name):
    """View to provide a form for editing existing tags, and to
    respond POST requests from this form."""
    # Get tag for editing
    try:
        tag = db_session.query(Tag).filter_by(name=tag_name).one()
    except (MultipleResultsFound, NoResultFound):
        # If there are more or less than one tags with this name,
        # throw a 404.
        abort(404)

    form = TagForm(request.form, meta={'csrf_context': session})
    
    if request.method == 'POST' and form.validate():
        try:
            tag.name = form.tag_name.data
            db_session.commit()
            
            # Log tag editing
            app.logger.info(
                "Edited {}, user IP address: {}".format(tag,
                                                        request.remote_addr))

            return redirect(url_for('viewTag', tag_name = tag.name))

        except IntegrityError:
            # If user tries to edit a tag to have the name of another existing
            # tag, roll back and add a form error
            db_session.rollback()
            form.tag_name.errors.append(
                'A tag already exists with that name.')

    elif request.method == 'GET':
        # For GET request, pre-fill details of edited tag
        form.tag_name.data = tag.name

    return render_template('tagform.html',
                           form=form,
                           action="editTag",
                           tag=tag,
                           logged_in=True)


@app.route('/catalog/items/edit/<item_name>-<int:item_id>/',
           methods=['GET', 'POST'])
@login_required(session)
@owner_only(session, db_session, Item)
@activated_user_required(session, db_session)
def editItem(item_name, item_id):
    """View to provide a form for editing existing items, and to
    respond POST requests from this form."""
    try:
        item = db_session.query(Item).filter_by(name=item_name,
                                                id=item_id).one()
    except (MultipleResultsFound, NoResultFound):
        # If there is more or less than one item with that name and id,
        # throw a 404
        abort(404)

    form = ItemForm(request.form, meta={'csrf_context': session})

    # Get list of all tags, and add to multiselect
    tags = db_session.query(Tag).all()
    form.tags.choices = [(unicode(g.id), g.name) for g in tags]

    if request.method == 'POST' and form.validate():

        # Get list of tags selected in the form.
        new_tag_ids = map(int, form.tags.data)
        new_tags = db_session.query(Tag).filter(Tag.id.in_(new_tag_ids)).all()
        
        # Edit item.
        item.tags = new_tags
        item.name = form.name.data
        item.description = form.description.data
        item.picture_url = form.picture_url.data
        db_session.commit()

        # Log item editing
        app.logger.info(
            "Edited {}, user IP address: {}".format(item,
                                                    request.remote_addr))

        return redirect(url_for('viewItem',
                                item_name = item.name,
                                item_id = item.id))
    
    elif request.method == 'GET':
        # For GET requests, pre-fill details of edited item
        form.name.data = item.name
        form.description.data = item.description
        form.picture_url.data = item.picture_url
        form.tags.data = [unicode(g.id) for g in tags if g in item.tags]
    
    return render_template('itemform.html',
                            form=form,
                            action='editItem',
                            item=item,
                            logged_in=True)

# Views for deleting existing entities

@app.route('/catalog/tags/delete/<tag_name>/', methods=['GET', 'POST'])
@login_required(session)
@owner_only(session, db_session, Tag)
@activated_user_required(session, db_session)
def deleteTag(tag_name):
    """View to provide a form for deleting existing tags, and to
    respond POST requests from this form."""
    
    try:
        tag = db_session.query(Tag).filter_by(name=tag_name).one()
    except (MultipleResultsFound, NoResultFound):
        # If there are more or less than one tags with this name,
        # throw a 404.
        abort(404)

    form = BlankForm(request.form, meta={'csrf_context': session})

    if request.method == 'POST' and form.validate():
        db_session.delete(tag)
        db_session.commit()

        # Log tag deletion
        app.logger.info(
            "Deleted {}, user IP address: {}".format(tag,
                                                     request.remote_addr))

        return redirect(url_for('index'))

    return render_template('deleteform.html',
                            form=form,
                            action='deleteTag',
                            deleted=tag,
                            logged_in=True)

@app.route('/catalog/items/delete/<item_name>-<int:item_id>/',
           methods=['GET', 'POST'])
@login_required(session)
@owner_only(session, db_session, Item)
@activated_user_required(session, db_session)
def deleteItem(item_name, item_id):
    """View to provide a form for deleting existing items, and to
    respond POST requests from this form."""
    try:
        item = db_session.query(Item).filter_by(name=item_name,
                                                id=item_id).one()
    except (MultipleResultsFound, NoResultFound):
        # If there are more or less than one items with this name and id,
        # throw a 404.
        abort(404)

    form = BlankForm(request.form, meta={'csrf_context': session})

    if request.method == 'POST' and form.validate():
        db_session.delete(item)
        db_session.commit()

        # Log item deletion
        app.logger.info(
            "Deleted {}, user IP address: {}".format(item,
                                                    request.remote_addr))

        return redirect(url_for('index'))

    return render_template('deleteform.html',
                            form=form,
                            action='deleteItem',
                            deleted=item,
                            logged_in=True)


# Views for JSON API

@app.route('/catalog.json')
def indexJSON():
    """View main catalog index as JSON"""
    tags = db_session.query(Tag).all()
    items = db_session.query(Item).all()
    return jsonify(Tags=[tag.serialize(include_items=True) for tag in tags],
                   Items=[i.serialize(include_tags=True) for i in items])

@app.route('/catalog/tags.json')
def indexTagsJSON():
    """View main catalog index as JSON, but only the Tags section"""
    tags = db_session.query(Tag).all()
    return jsonify(Tags=[tag.serialize(include_items=True) for tag in tags])

@app.route('/catalog/items.json')
def indexItemsJSON():
    """View main catalog index as JSON, but only the Items section"""
    items = db_session.query(Item).all()
    return jsonify(Items=[i.serialize(include_tags=True) for i in items])

@app.route('/catalog/tags/view/<tag_name>.json')
def viewTagJSON(tag_name):
    """View to allow users to retrieve tag information in JSON format"""

    try:
        tag = db_session.query(Tag).filter_by(name=tag_name).one()
    except (MultipleResultsFound, NoResultFound):
        # If there's more or less than one tag with that name,
        # throw a 404
        abort(404) 

    return jsonify(tag.serialize(include_items=True))

@app.route('/catalog/items/view/<item_name>-<int:item_id>.json')
def viewItemJSON(item_name, item_id):
    """View to allow users to retrieve information about individual
    items in JSON."""

    try:
        item = db_session.query(Item).filter_by(name=item_name,
                                                id=item_id).one()
    except (MultipleResultsFound, NoResultFound):
        # If there are more or less than one item with that name and id
        # throw a 404
        abort(404)

    return jsonify(item.serialize(include_tags=True))


# Views for Atom API

@app.route('/catalog/recent.atom')
def recentAtom():
    feed = AtomFeed(title="Recent Items",
                    feed_url=request.url,
                    url=request.host_url,
                    subtitle="The most recently created catalog items.",)
    for item in db_session.query(Item)                      \
                          .order_by(Item.updated_on.desc()) \
                          .limit(10):
        categories = [{'term': tag.name.lower(),
                       'label': tag.name} for tag in item.tags]
        feed.add(title=item.name,
                 url=url_for('viewItem',
                             item_name=item.name,
                             item_id=item.id),
                 updated=item.updated_on,
                 published=item.created_on,
                 content_type='text',
                 content=unicode(item.description),
                 categories=categories,
                 author={'name':"Random dude",
                         'email':'bob@example.com'})
                         # Replace with user once auth in place
    return feed.get_response()

# Views for login and auth

CLIENT_ID = json.loads(
        open('instance/client_secrets.json', 'r').read()
    )['web']['client_id']

@app.route('/login/')
def showLogin():
    next = request.values.get('next')
    if not next:
        next = request.referrer
    if not next:
        next = url_for('index')
    next = make_url_relative(next)
    form = LoginCSRFForm(request.form, meta={'csrf_context': session})
    return render_template('login.html',
                            form=form,
                            next=next,
                            client_id=CLIENT_ID)

@app.route('/logout/')
@login_required(session)
def showLogout():
    return render_template('logout.html')

@app.route('/gconnect', methods=['POST'])
def gconnect():
    """View to log in using Google's Oauth2 service"""
    form = LoginCSRFForm(request.form, meta={'csrf_context': session})
    form.validate()
    if form.csrf_token.errors:
        print "CSRF error detected"
        response = make_response(json.dumps('Invalid CSRF token'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = form.code.data
    try:
        # Exchange authorisation code for credentials object
        oauth_flow = flow_from_clientsecrets('instance/client_secrets.json',
                                             scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

        # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = session.get('access_token')
    stored_gplus_id = session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    session['access_token'] = credentials.access_token
    session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    session['username'] = data['name']
    session['picture'] = data['picture']
    session['email'] = data['email']

    # See if user exists in database, otherwise add them
    user_id = User.getIDByEmail(session['email'], db_session)
    if not user_id:
        user_id = User.createForID(session, db_session)
    session['user_id'] = user_id

    output = ''
    output += 'Welcome'
    if session['username']:
        output += ', '
        output += session['username']
    output += '.'
    flash("you are now logged in as %s" % session['username'])
    print "done!"
    response = make_response(json.dumps(output))
    response.headers['Content-Type'] = 'application/json'
    return response


@app.route('/gdisconnect')
def gdisconnect():
    access_token = session.get('access_token')
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: ' 
    print session.get('username')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'),
                                 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = ('https://accounts.google.com/o/oauth2/revoke?token=%s'
           % session['access_token'])
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del session['access_token'] 
        del session['gplus_id']
        del session['username']
        del session['email']
        del session['picture']
        del session['user_id']
        response = make_response(json.dumps('Successfully disconnected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
    
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

# Admin section
@app.route('/admin/')
@login_required(session)
@admin_only(session, db_session)
def admin():
    users = db_session.query(User).all()
    return render_template('admin.html', users=users, logged_in=True)

@app.route('/admin/activation/<int:user_id>/', methods=['POST', 'GET'])
@login_required(session)
@admin_only(session, db_session)
def user_activation(user_id):
    try:
        user = db_session.query(User).filter_by(id=user_id).one()
    except (MultipleResultsFound, NoResultFound):
        # If there are more or less than one items with this name and id,
        # throw a 404.
        abort(404)

    # If user is an admin, then you aren't allowed to
    # activate/deactivate them.
    if user.admin:
        abort(403)

    form = BlankForm(request.form, meta={'csrf_context': session})

    # Determine whether form should activate or deactivate user
    if user.activated:
        action = "deactivate"
    else:
        action = "activate"

    if request.method == 'POST' and form.validate():
        # Toggle user activation
        user.activated = not user.activated
        db_session.commit()

        return redirect(url_for('admin'))

    return render_template('activationform.html',
                            form=form,
                            action=action,
                            user=user,
                            logged_in=True)

# Error pages

@app.errorhandler(404)
def page_not_found404(e):
    # Find if logged in, for template info
    logged_in = 'username' in session
    return render_template('404.html', logged_in=logged_in), 404

@app.errorhandler(403)
def page_unauthorised403(e):
    # Find if logged in, for template info
    logged_in = 'username' in session
    return render_template('403.html', logged_in=logged_in), 403