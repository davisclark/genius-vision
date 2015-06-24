from datetime import datetime
from flask import request, redirect, session, url_for, current_app, flash
from requests_oauthlib import OAuth2Session
from flask.json import jsonify
import json
from . import oauth2
from ..models import User, Referent


client_id = "ym7CVRkna6PLmT2MgCmDimPgbWyAbfGwO2PBevqoHw6tVS_32hy2ZV9jBMGE5Ydq"
client_secret = "-mLg5ebXvx_vlw_68hu9ztw5ouM4793UsyD2Xv1mFHvGpT97LVXYKWh6P4rLFWNTjJH7BnEQMkbq4AeG_WCBDA"
authorization_base_url = "https://api.genius.com/oauth/authorize"
token_url = "https://api.genius.com/oauth/token"
scope = ["me","create_annotation", "manage_annotation", "vote"]


@oauth2.route('/callback', methods=["GET"])
def callback():
    redirect_uri = current_app.config['REDIRECT_URI_BASE'] + 'oauth2/callback'
    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, state=session['oauth_state'])
    token = oauth.fetch_token(token_url, client_secret=client_secret, code=request.args.get('code',''))
    session['oauth_token'] = token
    return redirect(url_for('.account'))


@oauth2.route('/account', methods=["GET"])
def account():
    if 'oauth_token' in session:
        oauth = OAuth2Session(client_id, token=session['oauth_token'])
        r = oauth.get("https://api.genius.com/account").text
        data = json.loads(r)
        if data['meta'] == 200:
            session.pop('oauth_token',None)
            session.pop('oauth_state', None)
            user = User.from_json(request.json)
            db.session.add(user)
            return render_template('index.html')
        elif data['meta'] == 400:
            flash('A failure of code for which Davis is to blame.')
        elif data['meta'] == 401:
            flash('Authentication is invalid.')
        session.pop('oauth_token',None)
        session.pop('oauth_state', None)
        return redirect(url_for('main.index'))
    else:
        redirect_uri = current_app.config['REDIRECT_URI_BASE'] + 'oauth2/callback'
        oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
        authorization_url, state = oauth.authorization_url(authorization_base_url)
        session['oauth_state'] = state
        #session['url'] = url
        return redirect(authorization_url)

@oauth2.route('/collect', methods=["GET"])
def collect_data(url):
    if 'oauth_token' in session:
        oauth = OAuth2Session(client_id, token=session['oauth_token'])
        api_url = "https://api.genius.com/referents?created_by_id="
        data = oauth.get(api_url)
        headers = {"Content-Type":"application/json",
                   "x-li-format":"json"}
        if data.status_code == 200:
            session.pop('oauth_token',None)
            session.pop('oauth_state', None)
            annotation = Referent.from_json(request.json)
            db.session.add(user)
            return redirect(url_for('.songs'))
        elif data.status_code == 400:
            flash('A failure of code for which Davis is to blame.')
        elif data.status_code == 401:
            flash('Authentication is invalid.')
        session.pop('oauth_token',None)
        session.pop('oauth_state', None)
        return redirect(url_for('main.entries'))

@oauth2.route('/songs', methods=["GET"])
def songs(url):
    if 'oauth_token' in session:
        oauth = OAuth2Session(client_id, token=session['oauth_token'])
        entry = Entry.query.filter_by(url=url).first()  
        json_entry = entry.to_json()
        api_url = "https://api.linkedin.com/v1/people/~/shares"
        headers = {"Content-Type":"application/json",
                   "x-li-format":"json"}
        data = oauth.post(api_url, data=json_entry, headers=headers)
        if data.status_code == 201:
            session.pop('oauth_token',None)
            session.pop('oauth_state', None)        
            flash('You successfully shared this entry with your peers -- thanks a lot!')
            return redirect(url_for('main.entry', eyear=entry.published.year, emonth=entry.published.month, url=url))
        elif data.status_code == 400:
            flash('A failure of code for which Davis is to blame.')
        elif data.status_code == 401:
            flash('Authentication is invalid.')
        session.pop('oauth_token',None)
        session.pop('oauth_state', None)
        return redirect(url_for('main.entries'))