from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import OAuth2WebServerFlow

import httplib2
import sqlite3

from apiclient.discovery import build
from bottle import app, static_file, route, request, run, template, redirect
# from oauth2client.client import FlowExchangeError
from beaker.middleware import SessionMiddleware

# client ID we obtained from google
CLIENT_ID='494621496088-8klfsohkn7cbq2u53q60kmk0fjohc1e0.apps.googleusercontent.com'
# the client secret
CLIENT_SECRET='PZrmADC1kOrR2fHTwRq_uToE'
# our json filename.
CLIENT_SECRETDIR='client_secret.json'
# for scope.
SCOPES = ['https://www.googleapis.com/auth/plus.me']
# redirect url
REDIRECT_URI = 'http://radialnetwork.mobi:8080/oauth2client'
#flow = flow_from_clientscrets("client_secrets.json", scope=GCE_SCOPE, redirect_uri='localhost:8080/redirect')
#GOOGLE_AUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_REVOKE_URI = 'https://accounts.google.com/o/oauth2/revoke'
#GOOGLE_TOKEN_URI = 'https://accounts.google.com/o/oauth2/token'
# The server expect files to be located in the same folder.
# When run from terminal, make sure the cwd is where this script is.
WEBROOT='./'

session_opts = {
        'session.type':'file',
        'session.cookie_expires':300,
        'session.data_dir': './data',
        'session.auto':True
        }
app = SessionMiddleware(app(), session_opts)

flow = flow_from_clientsecrets(CLIENT_SECRETDIR,
                               scope=SCOPES,
                               redirect_uri=REDIRECT_URI)
#code = request.data
gauthtoken = ''

@route('/test')
def test():
    s = request.environ.get('beaker.session')
    s['test'] = s.get('test',0) + 1
    s.save()
    return 'Test counter: %d' % s['test']


@route('/')
def index():
    f = open('gplus.html','r')
    index_html=f.read()
    f.close()
    return index_html

@route('/<filename:path>')
def send_static(filename):
    return static_file(filename, root=WEBROOT)

@route('/login')
def gplus_login():
    auth_uri = flow.step1_get_authorize_url()
    redirect(auth_uri)

@route('/oauth2client')
def google_login():
    code = request.query.get('code','')
    #print "The code is: "+code
    credentials= flow.step2_exchange(code)
    gauthtoken = credentials.id_token['sub']
    print "The user token is: " + gauthtoken
    http = httplib2.Http()
    http = credentials.authorize(http)
    # Get user email
    users_service = build('oauth2', 'v2', http=http)
    user_document = users_service.userinfo().get().execute()
    # Get user name
    users_service = build('plus', 'v1', http=http)
    profile = users_service.people().get(userId='me').execute()
    user_name = profile['displayName']
    user_image = profile['image']['url']
    # Header file
    f = open('header.html','r')
    searchengine_header = f.read()
    f.close()
    # navbar div
    navbar = "<div id=\"navibar\"><ul id=\"profile\"><li><a href=\"#\"><img src=\""
    navbar += str(user_image)
    navbar += "\" /></a></li><li id=\"profileText\">"
    navbar += str(user_name)
    navbar += "<li id=\"profileText\">CSC326 Group 1</li><li><a href=\"/signout\"><div id=\"profileLink\">Sign Out</div></a></li></ul></div>"
    f = open('index.html','r')
    searchengine_content = f.read()
    f.close()
    # completed front page loading.
    front_page = (searchengine_header + navbar + searchengine_content)
    return front_page

@route('/oauth2client', method='POST')
def query():
    queryString = request.forms.get('query')
    if queryString == None:
        return error404();
    tokens = queryString.split()
    # Use split() to split list into tokens
    querySet = set()
    # Stores unique query word
    queryFirst = tokens[0]
    # Search for the first query only!
    f = open('header.html','r')
    returnPage = f.read()
    f.close()
    # The page to be returned
    returnPage += "<h1>Search \"" + queryFirst + "\"</h1><br />"
    for token in querySet:
        n = 0
        for i in range(len(tokens)):
            if (token == tokens[i]):
                n += 1
        returnPage += ("<tr><td>" +token + "</td><td>" + str(n) + "</td></tr>")
    # returnPage += ("</table><p>You queried " + queryFirst + "</p></body></html>")
    returnPage += "</table><br /><p>Search Results</p><table border = \"1\">"
    returnPage += queryDB(queryFirst)
    returnPage += "</table></body></html>"
    # Closing tags
    return returnPage

def queryDB(query):
    con = sqlite3.connect('dbFile.db')
    cursor = con.cursor()
    # SELECT PageRank.ranking, DocIndex.url, Lexicon.wordID, InvertedIndex.docID
    cursor.execute('''SELECT PageRank.ranking, DocIndex.url FROM Lexicon
    INNER JOIN InvertedIndex
        ON Lexicon.wordID = InvertedIndex.wordID
    INNER JOIN DocIndex
        ON InvertedIndex.docID = DocIndex.doc_ID
    INNER JOIN PageRank
        ON DocIndex.doc_ID = PageRank.docID
    WHERE Lexicon.word = ?
    ORDER BY ranking DESC''', [query]);
    # Rank result from high to low.
    # con.commit() , url ASC
    rows = cursor.fetchall()
    # print rows
    result=''
    for row in rows:
        result += '<tr><td>PageRank: %s</td><td><a href="%s">%s</a></td></tr>' % (str(row[0]), row[1], row[1])
    con.close()
    return result

@route('/signout')
def signout():
    print GOOGLE_REVOKE_URI + gauthtoken
    # redirect('https://accounts.google.com/o/oauth2/revoke?token={token}', token)
    redirect('/')
run(app=app, host='0.0.0.0', port=8080, reloader=True)
