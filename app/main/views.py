from datetime import date
from flask import render_template, redirect, url_for, flash, abort,\
    request, current_app, session
from flask_sqlalchemy import get_debug_queries
from requests_oauthlib import OAuth2Session
from flask.json import jsonify
import json
from . import main
from .. import db
from ..models import User, Song, Artist, Annotation, Referent
from ..decorators import permission_required


client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
authorization_base_url = "https://api.genius.com/oauth/authorize"
token_url = "https://api.genius.com/oauth/token"
scope = ["me","create_annotation", "manage_annotation", "vote"]

def totalMetric(dataset, obj_key):
    sum_total = 0
    for d in dataset:
        sum_total += d[obj_key]
    return sum_total

def avgMetric(dataset, obj_key):
    return round(totalMetric(dataset, obj_key)/len(dataset))

def wordCount(string):
    return len(string.split())

def summarize(dataset):
    summary = {}
    summary['totalVotes'] = totalMetric(dataset, 'votes')
    summary['avgVotes'] = avgMetric(dataset,'votes')
    summary['totalWords'] = totalMetric(dataset, 'words')
    summary['avgWords'] = avgMetric(dataset, 'words')
    return summary

@main.route('/')
def index():
    return render_template('index.html') #will render a page with a button that says authorize


@main.route('/oauth2/callback', methods=["GET"])
def callback():
    redirect_uri = current_app.config['REDIRECT_URI_BASE'] + 'oauth2/callback'
    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, state=session['oauth_state'])
    token = oauth.fetch_token(token_url, client_secret=client_secret, code=request.args.get('code',''))
    session['oauth_token'] = token
    return redirect(url_for('main.account'))


@main.route('/account', methods=["GET"])
def account():
    if 'oauth_token' in session:
        oauth = OAuth2Session(client_id, token=session['oauth_token'])
        r = oauth.get("https://api.genius.com/account").json()
        if r['meta']['status'] == 200:
            session['id'] = r['response']['user']['id']
            session['name'] = r['response']['user']['name']
            session['iq'] = r['response']['user']['iq']
            session.pop('oauth_state', None)
            return render_template('index.html')
        elif r['meta']['status'] == 400:
            flash('A failure of code for which Davis is to blame.')
        elif r['meta']['status'] == 401:
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


@main.route('/analyze', methods=["GET"])
def Analysis():
    if 'oauth_token' in session:
        oauth = OAuth2Session(client_id, token=session['oauth_token'])
        data = oauth.get("https://api.genius.com/referents?created_by_id="+str(session['id'])+"&text_format=plain&per_page=100&page=1").json()
        if data['meta']['status'] == 200:
            artist_data = []
            song_data = []
            web_data = []
            referents = data['response']['referents']
            for ref in referents:
                x = {'type': ref['annotatable']['type'],
                'title': ref['annotatable']['title'], 
                'song_id': ref['song_id'], 
                'id': ref['id'],
                'words': wordCount(ref['annotations'][0]['body']['plain']),
                'votes': ref['annotations'][0]['votes_total'],
                'comments': ref['annotations'][0]['comment_count'],
                'url': ref['url'],
                'share_url': ref['annotations'][0]['share_url']}
                if ref['annotatable']['type'] == "Song":
                    s = oauth.get("https://api.genius.com/songs/"+str(ref['song_id'])+"?text_format=plain").json()
                    if s['meta']['status'] == 200:
                        song = s['response']['song']
                        x['pyongs'] = song['pyongs_count']
                        x['annotations'] = song['annotation_count']
                        if 'pageviews' in song['stats']:
                            x['pageviews'] = song['stats']['pageviews']
                    elif s['meta']['status'] == 404:
                        x['pyongs'] = 'error'
                        x['annotations'] = 'error'
                        x['pageviews'] = 'error'       
                    sdata = oauth.get("https://api.genius.com/referents?song_id="+str(ref['song_id'])+"&text_format=plain&per_page=100&page=1").json()
                    if sdata['meta']['status'] == 200:
                        s_summary = []
                        sreferents = sdata['response']['referents']
                        for sref in sreferents:
                            y = {'id':sref['id'],
                            'words': wordCount(sref['annotations'][0]['body']['plain']),
                            'votes': sref['annotations'][0]['votes_total']}
                            s_summary.append(y)
                        x['compare'] = summarize(s_summary)
                else:
                    x['pyongs'] = 'NA'
                    x['annotations'] = 'NA'
                    x['pageviews'] = 'NA'
                if x['type'] == 'Song':
                    song_data.append(x)
                elif x['type'] == 'Artist':
                    artist_data.append(x)
                elif x['type'] == 'WebPage':
                    web_data.append(x)
            song_summary = summarize(song_data)
            web_summary = summarize(web_data)
            artist_summary = summarize(artist_data)
            return render_template('index.html', song_data=song_data, web_data=web_data, artist_data=artist_data, song_summary=song_summary,
web_summary=web_summary, artist_summary=artist_summary)
        elif a['meta']['status'] == 400:
            flash('A failure of code for which Davis is to blame.')
        elif a['meta']['status'] == 401:
            flash('Authentication is invalid.')
        session.pop('oauth_state', None) 
        return redirect(url_for('main.index'))
    else:
        redirect_uri = current_app.config['REDIRECT_URI_BASE'] + 'oauth2/callback'
        oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
        authorization_url, state = oauth.authorization_url(authorization_base_url)
        session['oauth_state'] = state
        #session['url'] = url
        return redirect(authorization_url)  
##

@main.route('/songs/<song_id>', methods=["GET"])
def SongAnalysis(song_id):
    if 'oauth_token' in session:
        oauth = OAuth2Session(client_id, token=session['oauth_token'])
        data = oauth.get("https://api.genius.com/referents?song_id="+str(song_id)+"&text_format=plain&per_page=100&page=1").json()
        if data['meta']['status'] == 200:
            dataset = []
            referents = data['response']['referents']
            for ref in referents:
                x = {'type':ref['annotatable']['type'],'annotator_id': ref['annotator_id'],
                'id': ref['id'],
                'votes': ref['annotations'][0]['votes_total'],
                'comments': ref['annotations'][0]['comment_count'],
                'url': ref['url'],
                'share_url': ref['annotations'][0]['share_url'],
                'authors': ref['annotations'][0]['authors'],
                'text': ref['annotations'][0]['body']['plain']}
                dataset.append(x)
            if ref['annotatable']['type'] == "Song":
                s = oauth.get("https://api.genius.com/songs/"+str(song_id)+"?text_format=plain").json()
                if s['meta']['status'] == 200:
                    song = s['response']['song']
                    songdata = {'title':song['title'],'pyongs':song['pyongs_count'],'annotations':song['annotation_count']}
                    if 'pageviews' in song['stats']:
                        songdata['pageviews'] = song['stats']['pageviews']
                    else: 
                        songdata['pageviews'] = 'NA'
                elif s['meta']['status'] == 404:
                    songdata = {'pyongs':'error','annotations': 'error','pageviews': 'error'}       
            else:
                songdata = {'pyongs':'error','annotations': 'error','pageviews': 'error'}                       
            return render_template('songmetrics.html', dataset=dataset, songdata=songdata)
        elif a['meta']['status'] == 400:
            flash('A failure of code for which Davis is to blame.')
        elif a['meta']['status'] == 401:
            flash('Authentication is invalid.')
        session.pop('oauth_state', None) 
        return redirect(url_for('main.index'))
    else:
        redirect_uri = current_app.config['REDIRECT_URI_BASE'] + 'oauth2/callback'
        oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
        authorization_url, state = oauth.authorization_url(authorization_base_url)
        session['oauth_state'] = state
        #session['url'] = url
        return redirect(authorization_url)  

@main.route('/logout')
def logout():
    # remove the username from the session if it's there
    session.pop('name', None)
    session.pop('iq', None)
    session.pop('id', None)
    return redirect(url_for('main.index'))

# set the secret key.  keep this really secret:
main.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'