from wtforms import (Form, StringField, SelectMultipleField, TextAreaField,
                     validators)
from wtforms.csrf.session import SessionCSRF
from datetime import timedelta
from . import app

class MyBaseForm(Form):
    """Base form, provides configuration necessary for WTForms CSRF prevention
    features"""
    class Meta:
        csrf = True
        csrf_class = SessionCSRF
        csrf_secret = app.config['CSRF_SECRET_KEY']
        csrf_time_limit = timedelta(minutes=20)

class TagForm(MyBaseForm):
    tag_name = StringField('Category Name',
                           [validators.Length(min=3, max=25)])

class ItemForm(MyBaseForm):
    name = StringField('Item Name',
                       [validators.Length(min=3, max=25)])
    description = TextAreaField('Item Description',
                                [validators.Length(max=200)])
    picture_url = StringField('Picture URL', 
                              [validators.Optional(), validators.URL(),])
    tags = SelectMultipleField('Categories')

class BlankForm(MyBaseForm):
    """A form with no fields, used for delete confirmations and others
    forms with only a submit button"""
    pass



class LoginCSRFForm(MyBaseForm):
    code = StringField('Code')